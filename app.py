from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

app = Flask(__name__)

def wrap_text(draw, text, font, max_width):
    lines = []
    words = text.split(' ')
    current_line = ""
    for word in words:
        test_line = current_line + ' ' + word if current_line else word
        width, _ = draw.textbbox((0, 0), test_line, font=font)[2:4]

        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines

def draw_wrapped_text(draw, text, font, base_image_width, base_image_height, padding=10):
    # Calculate max width (60% of image width)
    max_width = int(base_image_width * 0.6)
    
    # Wrap text
    lines = wrap_text(draw, text, font, max_width)
    
    # Position the text at the bottom
    y_offset = base_image_height - (len(lines) * font.getsize(lines[0])[1] + padding)
    
    for line in lines:
        draw.text((100, y_offset), line, font=font, fill="black")  # Example x_position of 100px
        y_offset += font.getsize(line)[1] + padding  # Increase by line height and padding

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        # Extract data from the POST request
        data = request.json
        image_urls = data.get('images', [])  # List of image URLs
        text = data.get('text', '')  # The text to overlay on the image
        font_url = data.get('font_url', None)  # The font URL (if any)
        font_size = data.get('font_size', 50)  # Font size
        output_format = data.get('format', 'png').lower()  # Default to PNG

        if not image_urls:
            return jsonify({'error': 'No images provided in the request'}), 400

        # Fetch the base image
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
        canvas.paste(base_image, (0, 0), base_image)  # Paste the base image onto the white canvas

        # Overlay each subsequent image
        for url in image_urls[1:]:
            if not url.strip():  # Skip empty or blank URLs
                continue
            print(f"Fetching overlay image from: {url}")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    canvas.paste(overlay_image, (0, 0), overlay_image)  # Composite the image
                else:
                    print(f"Failed to fetch overlay image from: {url}, Status Code: {response.status_code}")
            except Exception as e:
                print(f"Error fetching overlay image from {url}: {e}")

        # Add the text if provided
        if text and font_url:
            print(f"Adding text: {text}")
            # Load font
            font = ImageFont.truetype(font_url, font_size)
            draw = ImageDraw.Draw(canvas)

            # Calculate max width (60% of image width)
            max_width = int(base_image.width * 0.6)

            # Add the wrapped text to the canvas at the bottom
            draw_wrapped_text(draw, text, font, base_image.width, base_image.height)

        # Save the final image
        output_path = f"output.{output_format}"
        if output_format == 'jpeg':
            canvas = canvas.convert("RGB")  # Convert to RGB to save as JPEG (JPEG does not support transparency)
            canvas.save(output_path, 'JPEG')
        elif output_format == 'pdf':
            canvas.convert("RGB").save(output_path, 'PDF')
        else:
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

