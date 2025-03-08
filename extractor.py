import os
import io
from pdf2image import convert_from_path
from google.cloud import vision

def convert_pdf_to_images(pdf_path, output_folder="static/temp_images"):
    os.makedirs(output_folder, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=300, fmt='png')
    image_paths = []
    for i, image in enumerate(images):
        image_path = os.path.join(output_folder, f"page_{i + 1}.png")
        image.save(image_path, "PNG")
        image_paths.append(image_path)
        print(f"✅ Page {i+1} converted to image: {image_path}")
    return image_paths

def get_ocr_data(image_path, output_text_folder="static/ocr_text"):
    os.makedirs(output_text_folder, exist_ok=True)
    client = vision.ImageAnnotatorClient()
    with io.open(image_path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if not texts:
        print(f"❌ No text found in image: {image_path}")
        return "❌ No text found in image.", []
    combined_lines = []
    detections = []
    for text in texts[1:]:
        line_text = text.description.strip()
        vertices = [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
        combined_lines.append(
            f"{line_text} " +
            "{" +
            ", ".join(f"({x},{y})" for x, y in vertices) +
            "}"
        )
        detections.append({"text": line_text, "vertices": vertices})
    combined_text = "\n".join(combined_lines)
    print(f"Detailed OCR data extracted from {image_path}")
    base_name = os.path.splitext(os.path.basename(image_path))[0]  # e.g. 'page_1'
    text_file_path = os.path.join(output_text_folder, f"{base_name}.txt")
    with open(text_file_path, "w", encoding="utf-8") as f:
        f.write(combined_text)
    print(f"✅ Wrote OCR text to {text_file_path}")

    return combined_text, detections
