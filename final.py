from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import os
import requests
from rembg import remove
from PIL import Image
from io import BytesIO
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)

# Configure directories
UPLOAD_FOLDER = 'images'
PROCESSED_FOLDER = 'processed_images'
ZIP_FOLDER = 'zipped'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

# Unsplash API credentials
UNSPLASH_ACCESS_KEY = "bUrrCOHEfTukc_WzUSi5GZB9HdtgPrEAK9hArzt25Rg"

# Email credentials
EMAIL = "kathait2309@gmail.com"
PASSWORD = "oqht igot qdvo ffdh"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.form
        keyword = data['keyword']
        num_images = int(data['num_images'])
        email = data['email']

        # Step 1: Download images
        images = download_images(keyword, num_images)

        # Step 2: Remove background
        processed_images = remove_background(images)

        # Step 3: Zip processed images
        zip_name = f"{keyword}_images.zip"
        zip_path = create_zip(processed_images, zip_name)

        # Step 4: Email zip file
        send_email(email, zip_path)

        return jsonify({"message": "Images processed and emailed successfully!"}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Helper functions
def download_images(keyword, num_images):
    images = []
    try:
        url = "https://api.unsplash.com/search/photos"
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
        }
        params = {
            "query": keyword,
            "per_page": num_images
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        photos = response.json().get('results', [])
        for i, photo in enumerate(photos):
            image_url = photo['urls']['regular']
            img_response = requests.get(image_url)
            if img_response.status_code == 200:
                img_path = os.path.join(UPLOAD_FOLDER, f"{keyword}_{i}.jpg")
                with open(img_path, 'wb') as f:
                    f.write(img_response.content)
                images.append(img_path)
    except Exception as e:
        print(f"Error downloading images from Unsplash: {e}")
    return images

def remove_background(images):
    processed_images = []
    for image_path in images:
        try:
            with open(image_path, 'rb') as img_file:
                input_img = img_file.read()
                output = remove(input_img)
            img = Image.open(BytesIO(output)).convert("RGBA")
            processed_path = os.path.join(PROCESSED_FOLDER, os.path.basename(image_path).replace('.jpg', '.png'))
            img.save(processed_path, "PNG")
            processed_images.append(processed_path)
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
    return processed_images

def create_zip(files, zip_name):
    zip_path = os.path.join(ZIP_FOLDER, zip_name)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            zipf.write(file, arcname=os.path.basename(file))
    return zip_path

def send_email(recipient_email, zip_file):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = "Your Processed Images"
        body = "Find the processed images attached."
        msg.attach(MIMEText(body, 'plain'))

        with open(zip_file, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(zip_file)}")
        msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.sendmail(EMAIL, recipient_email, msg.as_string())
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    app.run(debug=False)
