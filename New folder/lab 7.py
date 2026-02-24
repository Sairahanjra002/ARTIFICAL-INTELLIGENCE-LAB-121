import requests
from flask import Flask, render_template

app = Flask(__name__)

# New API key
api_key = "VfPmJxmJWkhLRSUmoDRILf2K1PkOgqbYSSRJQGHO"

# NASA APOD endpoint
url = f"https://api.nasa.gov/planetary/apod?api_key={api_key}"

@app.route('/<date>')
def specific_date(date):
    response = requests.get(url + "&date=" + date)

    if response.status_code == 200:
        nasa_data = response.json()
    else:
        nasa_data = {}

    return render_template('index.html', data=nasa_data)

@app.route('/')
def main():
    response = requests.get(url)

    if response.status_code == 200:
        nasa_data = response.json()
    else:
        nasa_data = {}

    return render_template('index.html', data=nasa_data)

if __name__ == "__main__":
    app.run(debug=True)