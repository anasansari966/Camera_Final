from flask import Flask, request, jsonify
import os
import cv2
import numpy as np
from skimage.metrics import mean_squared_error
from flask_cors import CORS
import json

app = Flask(__name__)
cors = CORS(app, resource={

    r"/*": {

        "origins": "*"

    }

})
# Define the directory to save the images
UPLOAD_FOLDER = 'data/images'
ORIGINAL_FOLDER = 'data/original'

# Create data folders if they don't exist
for folder in [UPLOAD_FOLDER, ORIGINAL_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ORIGINAL_FOLDER'] = ORIGINAL_FOLDER

# Counter for naming captured images
capture_counter = 0
score_response = 0

# Variables to store the paths of the original and captured images
original_img_path = None
captured_img_path = None


@app.route('/vc-webhook/ping')
def ping_pong():
    return "PONG"




@app.route('/vc-webhook/capture', methods=['POST'])
def capture():
    global capture_counter
    global original_img_path
    global captured_img_path

    # Check if the original image has been uploaded
    if original_img_path is None:
        return jsonify({"error": "Please upload the original image first."})

    # Save the captured image
    image_data = request.files.get("image_data")
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_{}.png'.format(capture_counter))
    image_data.save(image_path)
    capture_counter += 1
    captured_img_path = image_path

    # Calculate the score
    global score_response
    score_response = calculate_score()
    if score_response.get("error"):
        return jsonify(score_response)

    return jsonify({"message": "Captured Successfully.", "score": score_response["percentage_similarity"]})


@app.route('/vc-webhook/original_upload', methods=['POST'])
def original_upload():
    global original_img_path

    uploaded_image = request.files.get("image_data")
    filename = 'original.png'
    # Save the uploaded image in the original folder
    uploaded_image.save(os.path.join(app.config['ORIGINAL_FOLDER'], filename))
    original_img_path = os.path.join(app.config['ORIGINAL_FOLDER'], filename)
    return jsonify({"message": "Original Image Uploaded Successfully."})


def calculate_score():
    global original_img_path
    global captured_img_path

    if original_img_path is None or captured_img_path is None:
        return {"error": "One or both images are missing."}

    # Load images
    original_img = cv2.imread(original_img_path)
    captured_img = cv2.imread(captured_img_path)

    # Check if images are loaded successfully
    if original_img is None or captured_img is None:
        return {"error": "One or both images could not be loaded."}

    # Resize captured image to match the dimensions of the original image
    captured_img_resized = cv2.resize(captured_img, (original_img.shape[1], original_img.shape[0]))

    # Convert images to grayscale
    original_gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    captured_gray = cv2.cvtColor(captured_img_resized, cv2.COLOR_BGR2GRAY)

    # Calculate mean squared error
    mse = mean_squared_error(original_gray, captured_gray)

    # Calculate maximum possible error (assuming pixel values range from 0 to 255)
    max_possible_error = 255 ** 2

    # Calculate percentage similarity
    percent_similarity = (1 - mse / max_possible_error) * 100

    return {"percentage_similarity": percent_similarity}

@app.route("/vc-webhook/webhook", methods=["POST"])
def webhook():
    intent = request.form.get('intent')
    data = json.loads(intent)
    print(data)
    action = data['fulfillment']['action']

    if action == "image-captured-score":
        score = score_response
        buttons = []
        buttons_item = {
            "id": 18,
            "message": f"score: {score}<br> total uploads:{capture_counter}",
            "metadata": {
                "payload": [
                    {
                        "label": "Capture",
                        "value": "Capture",
                        "trigger": 17
                    },
                    {
                        "label": "Status",
                        "value": "Status",
                        "trigger": 4
                    }
                ],
                "templateId": 6
            },
            "userInput": False
        }

        buttons.append(buttons_item)

        # Construct JSON response with buttons

        updated_json = json.dumps(buttons_item)
        return updated_json


if __name__ == '__main__':
    app.run()