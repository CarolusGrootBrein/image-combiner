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
        image_urls = data.get('images', [])
        text = data.get('text', '')
        font_url = data.get('font', '')
        font_size = data.get('font_size', 180)
        output_format = data.get('format', 'png').lower()  # Default to PNG

        if font_url.lower() == "no":
            font_url = None

        # Fetch base image
        base_image = None
        for url in image_urls:
            if not url.strip():
                continue
            print(f"Fetching base image from: {url}")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    base_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    break
                else:
                    print(f"Failed to fetch image: {url}, Status Code: {response.status_code}")
            except Exception as e:
                print(f"Error fetching base image from {url}: {e}")

        if not base_image:
            return jsonify({'error': 'No valid base image found'}), 400

        # Create a canvas with a white background (same size as base image)
        canvas = Image.new("RGBA", base_image.size, color=(255, 255, 255, 255))  # White background

        # Place the base image on top of the white canvas
        canvas.paste(base_image, (0, 0), base_image)  # Ensure transparency handling

        # Overlay each subsequent image on top of the base image
        for url in image_urls[1:]:
            if not url.strip():
                continue
            print(f"Fetching overlay image from: {url}")
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    overlay_image = Image.open(BytesIO(response.content)).convert("RGBA")
                    # Paste the overlay image on top of the canvas, ensuring it preserves transparency
                    canvas.paste(overlay_image, (0, 0), overlay_image)  # Use the alpha channel as a mask
                else:
                    print(f"Failed to fetch overlay image: {url}, Status Code: {response.status_code}")
            except Exception as e:
                print(f"Error fetching overlay image from {url}: {e}")
                continue  # Skip to the next image if an error occurs

        # Handle text layer if text and font are provided
        if text and font_url:
            # Download the font file
            font_response = requests.get(font_url)
            font = ImageFont.truetype(BytesIO(font_response.content), font_size)

            # Draw the text
            draw = ImageDraw.Draw(canvas)

            # Calculate the text size and position (centered horizontally)
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:4]

            # Position text at the bottom and center it
            x_position = (canvas.width - text_width) // 2
            y_position = canvas.height - text_height - 180 # 20px padding from the bottom

            # Draw the text
            draw.text((x_position, y_position), text, font=font, fill="black")

        # Save the final image
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
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# Run the server on 0.0.0.0 to ensure external access
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')


