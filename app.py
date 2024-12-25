from flask import Flask, request, jsonify, send_file
from PIL import Image
import requests
from io import BytesIO

app = Flask(__name__)

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        # Extract data from the POST request
        data = request.json
        image_urls = data['images']  # List of image URLs

        # Fetch the first valid image to determine the canvas size
        base_image = None
        for url in image_urls:
            if not url:  # Skip blank or empty URLs
                print("Skipping blank URL.")
                continue
            print(f"Fetching base image from: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                base_image = Image.open(BytesIO(response.content)).convert("RGBA")
                print(f"Base image loaded successfully from {url}")
                break
            else:
                print(f"Failed to fetch image from: {url}, Status Code: {response.status_code}")

        if not base_image:
            return jsonify({'error': 'No valid base image provided'}), 400

        # Create a white background canvas with the same size as the base image
        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        # Overlay each subsequent image
        for url in image_urls[1:]:
            if not url:  # Skip blank or empty URLs
                print("Skipping blank URL.")
                continue
            print(f"Fetching overlay image from: {url}")
            response = requests.get(url)
            if response.status_code == 200:
                overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                canvas = Image.alpha_composite(canvas, overlay_image)
                print(f"Overlay image from {url} processed successfully.")
            else:
                print(f"Skipping invalid or inaccessible URL: {url}, Status Code: {response.status_code}")

        # Save the final image in the requested format
        output_format = data.get('format', 'png').lower()  # Default to PNG
        output_filename = f"output.{output_format}"

        if output_format == 'jpeg':
            # Convert to RGB to save as JPEG (JPEG does not support transparency)
            canvas = canvas.convert("RGB")
            canvas.save(output_filename, 'JPEG')
        elif output_format == 'pdf':
            # Save as a single-page PDF
            canvas.convert("RGB").save(output_filename, 'PDF')
        else:
            # Default to PNG
            canvas.save(output_filename, 'PNG')

        print(f"Final image saved as {output_filename}")
        return send_file(output_filename, mimetype=f'application/{output_format}' if output_format == 'pdf' else f'image/{output_format}')

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


# Run the server on 0.0.0.0 to ensure external access
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
