from flask import Flask, render_template, request
import os
import cv2
from ultralytics import YOLO

app = Flask(__name__)

# Folder to save uploads
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


model = YOLO("yolov8n.pt")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        # Check if file exists
        if "file" not in request.files:
            return "No file uploaded"

        file = request.files["file"]

        if file.filename == "":
            return "No selected file"

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)

        # Run YOLO detection
        results = model(filepath)

        # Get first result
        result = results[0]

        animal_count = 0

        # List of animals we care about
        target_animals = ["cow", "sheep", "horse", "elephant", "zebra", "giraffe"]

        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]

            if label in target_animals:
                animal_count += 1

        # Herd condition
        herd_detected = animal_count >= 5

        # Save annotated image
        annotated_frame = result.plot()
        output_path = os.path.join(app.config["UPLOAD_FOLDER"], "output_" + file.filename)
        cv2.imwrite(output_path, annotated_frame)

        return render_template("result.html",
                               image=output_path,
                               count=animal_count,
                               herd=herd_detected)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)