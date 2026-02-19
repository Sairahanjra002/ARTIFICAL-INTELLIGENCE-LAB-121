import os
import json
import time
import re
import threading
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from flask import Flask, request, render_template, jsonify, send_file

# ------------------ App Config ------------------
app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
PROGRESS_FILE = "progress.json"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

# ------------------ Progress Utils ------------------
def save_progress(status="", results=None, done=False):
    data = {
        "status": status,
        "results": results or [],
        "done": done
    }
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"status": "", "results": [], "done": False}

# ------------------ Scraper Logic ------------------
def extract_emails(text):
    return set(re.findall(EMAIL_REGEX, text))

def get_internal_links(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    links = set()

    for tag in soup.find_all("a", href=True):
        url = urljoin(base_url, tag["href"])
        parsed = urlparse(url)
        if parsed.netloc == base_domain:
            links.add(parsed.scheme + "://" + parsed.netloc + parsed.path)

    return links

def crawl_site(start_url, max_pages=10):
    visited = set()
    queue = [start_url]
    emails_found = set()

    headers = {"User-Agent": "Mozilla/5.0"}

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue

        save_progress(status=f"Scraping: {url}")

        try:
            r = requests.get(url, timeout=10, headers=headers)
            if r.status_code != 200:
                visited.add(url)
                continue

            html = r.text
            emails_found.update(extract_emails(html))
            queue.extend(get_internal_links(start_url, html) - visited)

        except Exception:
            pass

        visited.add(url)
        time.sleep(0.8)

    return sorted(emails_found)

def process_excel(file_path):
    df = pd.read_excel(file_path)
    results = []

    for _, row in df.iterrows():
        raw_url = str(row.get("URL", "")).strip()
        if not raw_url:
            continue

        if not raw_url.startswith("http"):
            raw_url = "http://" + raw_url

        emails = crawl_site(raw_url)
        results.append({
            "URL": raw_url,
            "Emails": ", ".join(emails)
        })

    output_path = os.path.join(DOWNLOAD_FOLDER, "company_emails.xlsx")
    pd.DataFrame(results).to_excel(output_path, index=False)

    save_progress(status="Completed!", results=results, done=True)

# ------------------ Routes ------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "File not provided"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    save_progress(status="Starting scraping...")

    thread = threading.Thread(target=process_excel, args=(filepath,), daemon=True)
    thread.start()

    return jsonify({"success": True})

@app.route("/progress")
def progress():
    return jsonify(load_progress())

@app.route("/download")
def download():
    return send_file(
        os.path.join(DOWNLOAD_FOLDER, "company_emails.xlsx"),
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
