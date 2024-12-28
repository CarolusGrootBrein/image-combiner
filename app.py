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
        image_urls = data.get('images', [])  # List of image URLs

        if not image_urls:
            return jsonify({'error': 'No images provided in the request'}), 400

        # Fetch the first image to determine the canvas size
        base_image = None
        for url in image_urls:
            if not url.strip():  # Skip empty or blank URLs
                continue
            print(f"Fetching base image from: {url}")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    break  # Exit loop once a valid base image is found
                else:
                    print(f"Failed to fetch image: {url}, Status Code: {response.status_code}")
            except Exception as e:
                print(f"Error fetching base image from {url}: {e}")

        if not base_image:
            return jsonify({'error': 'No valid base image found'}), 400

        # Create a white background canvas with the same size as the base image
        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        # Overlay each subsequent image
        for url in image_urls[1:]:
            if not url.strip():  # Skip empty or blank URLs
                continue
            print(f"Fetching overlay image from: {url}")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    canvas = Image.alpha_composite(canvas, overlay_image)
                else:
                    print(f"Failed to fetch overlay image from: {url}, Status Code: {response.status_code}")
            except Exception as e:
                print(f"Error fetching overlay image from {url}: {e}")

        # Save the final image
        output_format = data.get('format', 'png').lower()  # Default to PNG
        output_path = f"output.{output_format}"

        if output_format == 'jpeg':
            # Convert to RGB to save as JPEG (JPEG does not support transparency)
            canvas = canvas.convert("RGB")
            canvas.save(output_path, 'JPEG')
        elif output_format == 'pdf':
            # Save as a single-page PDF
            canvas.convert("RGB").save(output_path, 'PDF')
        else:
            # Default to PNG
            canvas.save(output_path, 'PNG')

        print(f"Final image saved as {output_path}")
        mime_type = 'application/pdf' if output_format == 'pdf' else f'image/{output_format}'
        return send_file(output_path, mimetype=mime_type)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


# Run the server on 0.0.0.0 to ensure external access
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
