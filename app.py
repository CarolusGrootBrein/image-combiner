from flask import Flask, request, jsonify, send_file
from PIL import Image
import requests
from io import BytesIO
import uuid

app = Flask(__name__)

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        # Extract data from the POST request
        data = request.json
        image_urls = data['images']  # List of image URLs

        # Fetch the first image to determine the canvas size
        response = requests.get(image_urls[0])
        if response.status_code != 200:
            return jsonify({'error': f"Failed to fetch image from {image_urls[0]}"}), 400
        
        base_image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Create a white background canvas with the same size as the base image
        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        # Overlay each subsequent image
        for url in image_urls[1:]:
            response = requests.get(url)
            if response.status_code == 200:
                overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                canvas = Image.alpha_composite(canvas, overlay_image)
            else:
                return jsonify({'error': f"Failed to fetch image from {url}"}), 400

        # Generate a unique output file name
        output_format = data.get('format', 'png').lower()  # Default to PNG
        output_filename = f"output_{str(uuid.uuid4())}.{output_format}"

        # Convert to the appropriate format and send the file
        output_image = BytesIO()
        if output_format == 'jpeg':
            canvas = canvas.convert("RGB")  # Convert to RGB for JPEG
            canvas.save(output_image, 'JPEG')
        else:
            canvas.save(output_image, 'PNG')

        output_image.seek(0)  # Reset pointer to the start of the file-like object

        # Return the image as a downloadable file in the response
        return send_file(output_image, mimetype=f'image/{output_format}', as_attachment=True, download_name=output_filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run the server
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
