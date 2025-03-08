import os
import json
import cv2
import tempfile
from ultralytics import YOLO
import cloudinary
import cloudinary.uploader

CLOUDINARY_CONFIG = {
    'cloud_name': "dpdqxdlz5",
    'api_key': "956864746811318",
    'api_secret': "U8vyHhuTQ52KH2-xUsQQJWZdH0I"
}
cloudinary.config(**CLOUDINARY_CONFIG)

def run_yolo_and_save_with_boxes(image_paths, model_path="best.pt", output_dir="static/output_with_boxes"):
    os.makedirs(output_dir, exist_ok=True)
    model = YOLO(model_path)
    predictions = {}

    for image_path in image_paths:
        original_image = cv2.imread(image_path)
        if original_image is None:
            print(f"Failed to load image: {image_path}")
            continue

        page_id = os.path.basename(image_path).split('.')[0]
        predictions[page_id] = []
        results = model(image_path)

        for box in results[0].boxes:
            bbox = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            if class_name.lower() not in ["questions", "options", "solutions", "diagrams"]:
                continue

            x_min, y_min, x_max, y_max = map(int, bbox)
            predictions[page_id].append({
                "class": class_name,
                "path": image_path,
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
                "confidence": confidence
            })
            color = (0, 255, 0)
            cv2.rectangle(original_image, (x_min, y_min), (x_max, y_max), color, 12)
            cv2.putText(
                original_image,
                f"{class_name} {confidence:.2f}",
                (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.5,
                (255, 0, 0),
                10
            )
        output_image_path = os.path.join(output_dir, os.path.basename(image_path))
        cv2.imwrite(output_image_path, original_image)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w")
    json.dump(predictions, temp_file, indent=4)
    temp_file.close()
    print(f"Predictions saved to temporary file: {temp_file.name}")
    return temp_file.name

def crop_images_by_class(predictions_json, output_dir="static/cropped_images"):
    with open(predictions_json, "r") as f:
        predictions = json.load(f)
    questions_folder = os.path.join(output_dir, "Questions")
    options_folder   = os.path.join(output_dir, "Options")
    solutions_folder = os.path.join(output_dir, "Solutions")
    diagrams_folder  = os.path.join(output_dir, "Diagrams")
    for folder in [questions_folder, options_folder, solutions_folder, diagrams_folder]:
        os.makedirs(folder, exist_ok=True)
    cropped_data = {}
    for page_id, boxes in predictions.items():
        cropped_data[page_id] = []
        for box_info in boxes:
            cls = box_info["class"].lower()
            x_min = box_info["x_min"]
            y_min = box_info["y_min"]
            x_max = box_info["x_max"]
            y_max = box_info["y_max"]
            confidence = box_info.get("confidence", 0.0)
            if cls == "questions":
                crop_dir = questions_folder
            elif cls == "options":
                crop_dir = options_folder
            elif cls == "solutions":
                crop_dir = solutions_folder
            elif cls == "diagrams":
                crop_dir = diagrams_folder
            else:
                continue
            # Crop and save
            cropped_path = crop_and_save(
                box_info["path"],
                x_min, y_min, x_max, y_max,
                output_dir=crop_dir
            )
            if not cropped_path:
                continue
            cropped_data[page_id].append({
                "class": cls,
                "cropped_path": cropped_path,
                "confidence": confidence
            })

    return cropped_data

def crop_and_save(image_path, x_min, y_min, x_max, y_max, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(image_path)
    file_name = f"{base_name}_{x_min}_{y_min}.png"
    output_path = os.path.join(output_dir, file_name).replace("\\", "/")
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image for cropping: {image_path}")
        return None
    cropped_region = image[y_min:y_max, x_min:x_max]
    cv2.imwrite(output_path, cropped_region)
    return output_path


def upload_image_to_cloudinary(file_path):
    try:
        result = cloudinary.uploader.upload(file_path)
        secure_url = result.get("secure_url")
        return secure_url
    except Exception as e:
        print(f"Error uploading {file_path} to Cloudinary: {e}")
        return None

def upload_diagrams_in_folder(diagrams_folder="static/cropped_images/Diagrams"):
    diagram_urls = []
    if not os.path.isdir(diagrams_folder):
        print(f"Diagrams folder does not exist: {diagrams_folder}")
        return diagram_urls

    for file_name in os.listdir(diagrams_folder):
        if file_name.lower().endswith((".png", ".jpg", ".jpeg")):
            file_path = os.path.join(diagrams_folder, file_name)
            url = upload_image_to_cloudinary(file_path)
            if url:
                diagram_urls.append(url)
            else:
                print(f"Failed to upload: {file_path}")
    return diagram_urls

def upload_pdf_pages(image_paths):
    page_urls = {}
    for img_path in image_paths:
        try:
            # Use your existing upload_image_to_cloudinary function:
            url = upload_image_to_cloudinary(img_path)
            if url:
                file_name = os.path.basename(img_path)
                page_urls[file_name] = url
            else:
                print(f"Failed to upload PDF page: {img_path}")
        except Exception as e:
            print(f"Error uploading page {img_path} to Cloudinary: {e}")

    return page_urls

def build_final_diagram_json(
    predictions_json,
    ocr_text_folder="static/ocr_text",
    output_json="diagram_info.json",
    diagram_crop_dir="static/cropped_diagrams"
):
    with open(predictions_json, "r") as f:
        predictions = json.load(f)
    final_data = {}
    for page_id, boxes in predictions.items():
        page_text_path = os.path.join(ocr_text_folder, f"{page_id}.txt")
        if os.path.exists(page_text_path):
            with open(page_text_path, "r", encoding="utf-8") as tf:
                page_text = tf.read()
        else:
            page_text = f"No OCR text file found for {page_id}"
        diagram_entries = [b for b in boxes if b["class"].lower() == "diagrams"]
        diagram_list = []
        for entry in diagram_entries:
            x_min = entry["x_min"]
            y_min = entry["y_min"]
            x_max = entry["x_max"]
            y_max = entry["y_max"]
            conf = entry.get("confidence", 0.0)
            cropped_path = crop_and_save(
                entry["path"],
                x_min, y_min, x_max, y_max,
                output_dir=diagram_crop_dir
            )
            if not cropped_path:
                continue

            # Upload the cropped diagram to Cloudinary
            diag_url = upload_image_to_cloudinary(cropped_path)
            if not diag_url:
                diag_url = "Upload failed"
            diagram_item = {
                "diagram_url": diag_url,
                "bbox": f"({x_min},{y_min},{x_max},{y_max})",
                "confidence": conf
            }
            diagram_list.append(diagram_item)
        final_data[page_id] = {
            "page_text": page_text,
            "diagrams": diagram_list
        }
    with open(output_json, "w", encoding="utf-8") as out_f:
        json.dump(final_data, out_f, indent=2)
    print(f"✅ Final diagram JSON saved to {output_json}")

    return final_data