from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

app = Flask(__name__)

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        data = request.json
        image_urls = data.get('images', [])
        font_url = data.get('font_url', "")
        text = data.get('text', "")
        font_size = data.get('font_size', 180)
        output_format = data.get('format', 'png').lower()

        if not image_urls:
            return jsonify({'error': 'No images provided in the request'}), 400

        # Fetch base image
        base_image = None
        for url in image_urls:
            if not url.strip():
                continue
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    break
            except Exception as e:
                return jsonify({'error': f'Error fetching base image: {e}'}), 400

        if not base_image:
            return jsonify({'error': 'No valid base image found'}), 400

        canvas = Image.new("RGBA", base_image.size, color="white")
        canvas = Image.alpha_composite(canvas, base_image)

        # Add text layer if text is provided
        if text.lower() != "no" and text:
            font = ImageFont.truetype("path/to/font.ttf", font_size)
            draw = ImageDraw.Draw(canvas)

            # Calculate the text width and height
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]

            # Set padding and position based on canvas size
            padding = 50
            x_position = (canvas.width - text_width) // 2
            y_position = canvas.height - text_height - padding

            draw.text((x_position, y_position), text, font=font, fill="black")

        # Overlay the other images
        for url in image_urls[1:]:
            if not url.strip():
                continue
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    canvas = Image.alpha_composite(canvas, overlay_image)
            except Exception as e:
                return jsonify({'error': f'Error fetching overlay image: {e}'}), 400

        # Save output
        output_path = f"output.{output_format}"
        if output_format == 'jpeg':
            canvas = canvas.convert("RGB")
            canvas.save(output_path, 'JPEG')
        elif output_format == 'pdf':
            canvas.convert("RGB").save(output_path, 'PDF')
        else:
            canvas.save(output_path, 'PNG')

        return send_file(output_path, mimetype=f'image/{output_format}')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

