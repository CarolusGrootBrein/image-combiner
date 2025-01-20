from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

app = Flask(__name__)

def wrap_text(draw, text, font, max_width):
    lines = []
    words = text.split(' ')
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        width, _ = draw.textbbox((0, 0), test_line, font=font)[2:4]

        # Check if the line exceeds the max width
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:  # Add the current line to lines before wrapping
                lines.append(' '.join(current_line))
            current_line = [word]  # Start new line with the current word

    # Add any remaining text
    if current_line:
        lines.append(' '.join(current_line))

    return lines

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

        # Handle text layer if text and font are provided
        if text and font_url:
            # Download the font file
            font_response = requests.get(font_url)
            font = ImageFont.truetype(BytesIO(font_response.content), font_size)

            # Draw the text
            draw = ImageDraw.Draw(canvas)

            # Wrap text to fit within the fixed 360px width
            max_width = 180  # Fixed width for the text box (360px)
            lines = wrap_text(draw, text, font, max_width)

            # Start drawing from the bottom, with each line stacked vertically
            y_position = canvas.height - 20  # Start 20px from the bottom (margin)
            for line in reversed(lines):
                # Calculate text width and height
                width, height = draw.textbbox((0, 0), line, font=font)[2:4]

                # Position text at the bottom and center it
                x_position = (canvas.width - width) // 2
                draw.text((x_position, y_position - height), line, font=font, fill="black")

                # Update y_position for the next line
                y_position -= height + 5  # 5px space between lines

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

