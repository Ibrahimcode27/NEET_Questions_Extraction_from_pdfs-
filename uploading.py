import os
import shutil
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext
import uuid
import json
from PIL import Image, ImageTk
from extractor import convert_pdf_to_images, get_ocr_data
from diagram_linker import (
    run_yolo_and_save_with_boxes,
    build_final_diagram_json
)
from gemini_integration import call_gemini_api_page_by_page
from Gemini_SQL_generator import generate_sql_from_json

UPLOAD_FOLDER = "uploads"
RESPONSE_FOLDER = "responses"  # Folder storing JSON responses
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESPONSE_FOLDER, exist_ok=True)

OCR_TEXT_FOLDER = "static/ocr_text"
os.makedirs(OCR_TEXT_FOLDER, exist_ok=True)

def create_gui():
    global root, status_label, text_display, generate_sql_button
    root = tk.Tk()
    root.title("PDF to SQL Generator")
    root.geometry("800x700")
    root.resizable(True, True)

    status_label = tk.Label(root, text="Upload a PDF to start processing...", font=("Arial", 14), fg="blue")
    status_label.pack(pady=10)

    upload_button = tk.Button(
        root, text="Upload & Process PDF", command=lambda: select_file(root),
        font=("Arial", 12), bg="#4CAF50", fg="white", padx=20, pady=10
    )
    upload_button.pack()

    text_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=25, width=90, font=("Arial", 10))
    text_display.pack(pady=10)

    # Initially Hide Generate SQL Button
    generate_sql_button = tk.Button(
        root, text="Generate SQL", font=("Arial", 12), bg="#008CBA", fg="white", padx=20, pady=10,
        command=generate_sql, state=tk.DISABLED
    )
    generate_sql_button.pack(pady=10)

    root.mainloop()

def update_gui_status(message):
    """ Updates the GUI text area with progress messages """
    text_display.insert(tk.END, message + "\n")
    text_display.see(tk.END)
    root.update()

def select_file(root):
    file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if not file_path:
        return

    # Copy the PDF to 'uploads/' with a unique name
    unique_filename = f"{uuid.uuid4().hex}.pdf"
    save_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    shutil.copy(file_path, save_path)

    update_gui_status("✅ PDF uploaded successfully.")
    process_pdf(save_path)

def process_pdf(pdf_path):
    update_gui_status("🔄 Converting PDF to images...")
    try:
        image_paths = convert_pdf_to_images(pdf_path)
        if not image_paths:
            raise ValueError("No images generated from the PDF.")
        update_gui_status(f"✅ PDF converted into {len(image_paths)} images.")
    except Exception as e:
        update_gui_status(f"❌ Error during PDF to image conversion: {e}")
        return

    update_gui_status("🔄 Running OCR on images...")
    try:
        for img_path in image_paths:
            page_text, _ = get_ocr_data(img_path)
            base_name = os.path.splitext(os.path.basename(img_path))[0]  # e.g., "page_1"
            text_file_path = os.path.join(OCR_TEXT_FOLDER, f"{base_name}.txt")
            with open(text_file_path, "w", encoding="utf-8") as f:
                f.write(page_text)
        update_gui_status("✅ OCR processing completed.")
    except Exception as e:
        update_gui_status(f"❌ Error during OCR processing: {e}")
        return

    update_gui_status("🔄 Running YOLO for diagram detection...")
    try:
        predictions_json = run_yolo_and_save_with_boxes(
            image_paths, model_path="best.pt", output_dir="static/output_with_boxes"
        )
        update_gui_status("✅ YOLO processing completed.")
    except Exception as e:
        update_gui_status(f"❌ Error during YOLO processing: {e}")
        return

    update_gui_status("🔄 Merging extracted text and detected diagrams...")
    try:
        diagram_info_json = "diagram_info.json"
        build_final_diagram_json(
            predictions_json, ocr_text_folder=OCR_TEXT_FOLDER, output_json=diagram_info_json,
            diagram_crop_dir="static/cropped_diagrams"
        )
        update_gui_status("✅ Text and diagrams merged successfully.")
    except Exception as e:
        update_gui_status(f"❌ Error during merging process: {e}")
        return

    update_gui_status("🔄 Processing each page with Gemini API...")
    try:
        gemini_results = call_gemini_api_page_by_page(diagram_info_json)
        update_gui_status("✅ Gemini API processing completed.\n")

        # Display Gemini responses in GUI
        text_display.insert(tk.END, json.dumps(gemini_results, indent=2) + "\n")
        text_display.see(tk.END)
        root.update()

        # Enable the Generate SQL Button
        generate_sql_button.config(state=tk.NORMAL)

    except Exception as e:
        update_gui_status(f"❌ Error during Gemini processing: {e}")
        return

def generate_sql():
    update_gui_status("🔄 Merging all response JSON files...")
    combined_data = []

    # Merge all JSON response files
    for filename in os.listdir(RESPONSE_FOLDER):
        if filename.endswith(".json"):
            file_path = os.path.join(RESPONSE_FOLDER, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        combined_data.extend(data)
            except Exception as e:
                update_gui_status(f"❌ Error reading {filename}: {e}")

    if not combined_data:
        update_gui_status("❌ No valid JSON data found. SQL generation aborted.")
        return

    # Save merged JSON for reference
    merged_json_path = os.path.join(RESPONSE_FOLDER, "merged_data.json")
    with open(merged_json_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2)

    update_gui_status(f"✅ Merged JSON saved at {merged_json_path}")

    # Generate SQL from merged JSON
    update_gui_status("🔄 Generating SQL from merged JSON data...")
    try:
        generate_sql_from_json(merged_json_path, "exam_2024.pdf")

        # Read and display the generated SQL
        sql_file_path = os.path.join("sql_outputs", "exam_2024.pdf_output.sql")
        with open(sql_file_path, "r", encoding="utf-8") as sql_file:
            sql_output = sql_file.read()

        update_gui_status("✅ SQL generation completed. Here is the output:\n")
        text_display.insert(tk.END, sql_output + "\n")
        text_display.see(tk.END)

    except Exception as e:
        update_gui_status(f"❌ Error during SQL generation: {e}")

if __name__ == "__main__":
    create_gui()
