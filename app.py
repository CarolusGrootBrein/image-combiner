from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import concurrent.futures

app = Flask(__name__)

# Function to fetch image with retries
def fetch_image(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content)).convert("RGBA")
    except requests.RequestException:
        return None  # Return None if the image can't be fetched

@app.route('/combine-images', methods=['POST'])
def combine_images():
    try:
        data = request.json
        image_urls = data.get('images', [])
        text = data.get('text', '')
        font_url = data.get('font', '')
        font_size = data.get('font_size', 180)
        output_format = data.get('format', 'png').lower()

        if font_url.lower() == "no":
            font_url = None

        # Fetch base image
        base_image = None
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(fetch_image, url) for url in image_urls if url.strip()]
            for future in concurrent.futures.as_completed(futures):
                image = future.result()
                if image:
                    base_image = image
                    break

        if not base_image:
            return jsonify({'error': 'No valid base image found'}), 400

        canvas = Image.new("RGBA", base_image.size, color=(255, 255, 255, 255))  # White background
        canvas.paste(base_image, (0, 0), base_image)  # Place base image

        # Fetch additional layers concurrently
        layers = image_urls[1:]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(fetch_image, url) for url in layers if url.strip()]
            for future in concurrent.futures.as_completed(futures):
                overlay_image = future.result()
                if overlay_image:
                    canvas.paste(overlay_image, (0, 0), overlay_image)

        # Handle text layer if needed
        if text and font_url:
            font_response = requests.get(font_url)
            font = ImageFont.truetype(BytesIO(font_response.content), font_size)
            draw = ImageDraw.Draw(canvas)

            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]
            x_position = (canvas.width - text_width) // 2
            y_position = canvas.height - text_height - 180  # 20px padding from bottom

            draw.text((x_position, y_position), text, font=font, fill="black")

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

