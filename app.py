from flask import Flask, request, jsonify, send_file
from PIL import Image
import requests
from io import BytesIO
import os

app = Flask(__name__)

# Basic test route to check if the app is running
@app.route('/')
def hello_world():
    return "Hello, World!"

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        # Extract data from the POST request
        data = request.json
        image_urls = data['images']  # List of image URLs

        # Fetch the first image to determine the canvas size
        print(f"Fetching base image from: {image_urls[0]}")
        response = requests.get(image_urls[0])
        if response.status_code != 200:
            return jsonify({'error': f"Failed to fetch image from {image_urls[0]}"}), 400
        
        base_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Create a white background canvas with the same size as the base image
        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        # Overlay each subsequent image
        for url in image_urls[1:]:
            print(f"Fetching overlay image from: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                canvas = Image.alpha_composite(canvas, overlay_image)
            else:
                print(f"Failed to fetch image from: {url}")
                return jsonify({'error': f"Failed to fetch image from {url}"}), 400

        # Save the final image
        output_format = data.get('format', 'png').lower()  # Default to PNG
        output_path = f"output.{output_format}"

        if output_format == 'jpeg':
            # Convert to RGB to save as JPEG (JPEG does not support transparency)
            canvas = canvas.convert("RGB")
            canvas.save(output_path, 'JPEG')
        else:
            canvas.save(output_path, 'PNG')

        print(f"Final image saved as {output_path}")
        return send_file(output_path, mimetype=f'image/{output_format}')

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


# Run the server
if __name__ == '__main__':
    print("Starting Flask app...")
    # Make sure Flask listens on the correct port for Render
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
