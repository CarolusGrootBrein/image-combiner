from flask import Flask, request, jsonify, send_file, url_for
from PIL import Image
import requests
from io import BytesIO
import os
import time
from threading import Thread

app = Flask(__name__)

# Ensure the static/temp directory exists
os.makedirs('static/temp', exist_ok=True)

# Cleanup function to remove old files
def cleanup_temp_folder():
    temp_folder = 'static/temp'
    max_age = 3600  # 1 hour in seconds
    while True:
        now = time.time()
        for filename in os.listdir(temp_folder):
            file_path = os.path.join(temp_folder, filename)
            if os.path.isfile(file_path) and now - os.path.getmtime(file_path) > max_age:
                print(f"Deleting old file: {file_path}")
                os.remove(file_path)
        time.sleep(600)  # Check every 10 minutes

# Start the cleanup process in a separate thread
cleanup_thread = Thread(target=cleanup_temp_folder, daemon=True)
cleanup_thread.start()

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        # Extract data from the POST request
        data = request.json
        image_urls = data['images']

        print("Starting image fetch and processing...")

        # Fetch the first image to determine the canvas size
        print(f"Fetching base image from: {image_urls[0]}")
        response = requests.get(image_urls[0])
        if response.status_code != 200:
            return jsonify({'error': f"Failed to fetch image from {image_urls[0]}"}), 400

        # Debug: Check content type
        if 'image' not in response.headers.get('Content-Type', ''):
            return jsonify({'error': f"Invalid content type for base image: {image_urls[0]}"}), 400

        base_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Create a white canvas and combine images
        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        for url in image_urls[1:]:
            print(f"Fetching overlay image from: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                if 'image' not in response.headers.get('Content-Type', ''):
                    return jsonify({'error': f"Invalid content type for URL: {url}"}), 400
                overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                canvas = Image.alpha_composite(canvas, overlay_image)
            else:
                print(f"Failed to fetch image from: {url}, Status Code: {response.status_code}")
                return jsonify({'error': f"Failed to fetch image from {url}, Status Code: {response.status_code}"}), 400

        # Save the final image in the static/temp directory
        output_format = data.get('format', 'png').lower()
        output_filename = f"output.{output_format}"
        output_path = os.path.join('static/temp', output_filename)

        if output_format == 'jpeg':
            canvas = canvas.convert("RGB")
            canvas.save(output_path, 'JPEG')
        else:
            canvas.save(output_path, 'PNG')

        # Generate a URL for the temporary image
        temp_url = url_for('static', filename=f"temp/{output_filename}", _external=True)
        print(f"Image temporarily saved as {output_path}, accessible at {temp_url}")

        return jsonify({'temp_image_url': temp_url})

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
