from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

app = Flask(__name__)

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        # Extract data from the POST request
        data = request.json
        image_urls = data.get('images', [])  # List of image URLs
        text = data.get('text', None)  # Text to overlay on the image
        font_url = data.get('font', None)  # Font URL (or "No" to skip)
        font_size = int(data.get('font_size', 180))  # Font size (default 180px)
        text_position = data.get('text_position', (100, 100))  # Default position if no position is provided

        if not image_urls:
            return jsonify({'error': 'No images provided'}), 400

        # Fetch base image (first image in the list)
        base_image = None
        for url in image_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    break
            except Exception as e:
                print(f"Error fetching base image: {e}")
        
        if not base_image:
            return jsonify({'error': 'No valid base image found'}), 400

        # Create a blank canvas to overlay images
        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        # Overlay each subsequent image
        for url in image_urls[1:]:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    canvas = Image.alpha_composite(canvas, overlay_image)
            except Exception as e:
                print(f"Error fetching overlay image: {e}")

        # Add text layer if needed, skip if "No" is passed as font URL
        if text and font_url != "No":
            try:
                # Debugging: Check the font URL
                print(f"Fetching font from URL: {font_url}")

                # Download the font from the URL
                if font_url:
                    font_response = requests.get(font_url, timeout=10)
                    if font_response.status_code == 200:
                        # Debugging: Check the font file size to ensure it's being downloaded
                        print(f"Font file downloaded successfully, size: {len(font_response.content)} bytes")
                        font = ImageFont.truetype(BytesIO(font_response.content), font_size)
                    else:
                        print(f"Failed to load font from {font_url} - Status Code: {font_response.status_code}")
                        return jsonify({'error': f"Failed to load font from {font_url}"}), 400
                else:
                    # Default font (if no font URL is provided, fallback to a basic font)
                    font = ImageFont.load_default()

                # Debugging: Print some information about the font
                print(f"Font loaded successfully: {font}")

                draw = ImageDraw.Draw(canvas)

                # Calculate the size of the text to get the width and height
                text_width, text_height = draw.textsize(text, font=font)

                # Calculate position: align at the bottom, with a 20px margin
                x_position = (canvas.width - text_width) // 2  # Center horizontally
                y_position = canvas.height - text_height - 20  # 20px from bottom

                # Draw the text at the calculated position
                draw.text((x_position, y_position), text, font=font, fill=(255, 255, 255, 255))

                print(f"Text '{text}' drawn at position ({x_position}, {y_position})")
            except Exception as e:
                print(f"Error adding text: {e}")
                return jsonify({'error': f"Error adding text: {e}"}), 500

        # Output the image
        output_format = data.get('format', 'png').lower()  # Default to PNG
        output_path = f"output.{output_format}"

        if output_format == 'jpeg':
            canvas = canvas.convert("RGB")
            canvas.save(output_path, 'JPEG')
        elif output_format == 'pdf':
            canvas.convert("RGB").save(output_path, 'PDF')
        else:
            canvas.save(output_path, 'PNG')

        return send_file(output_path, mimetype=f"image/{output_format}")

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run the server on 0.0.0.0 to ensure external access
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
