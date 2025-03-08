import time
import json
import os
import google.generativeai as genai
genai.configure(api_key="")
NEET_SYLLABUS = {
    "Physics": [
        "Physics and Measurement", "Kinematics", "Laws of Motion", "Work, Energy and Power",
        "Rotational Motion", "Gravitation", "Properties of Solids and Liquids", "Thermodynamics",
        "Kinetic Theory of Gases", "Oscillations and Waves", "Electrostatics", "Current Electricity",
        "Magnetic Effects of Current and Magnetism", "Electromagnetic Induction and Alternating Currents",
        "Electromagnetic Waves", "Optics", "Dual Nature of Matter and Radiation", "Atoms and Nuclei",
        "Electronic Devices", "Experimental Skills"
    ],
    "Chemistry": [
        "Some Basic Concepts in Chemistry", "Atomic Structure", "Chemical Bonding and Molecular Structure",
        "Chemical Thermodynamics", "Solutions", "Equilibrium", "Redox Reactions and Electrochemistry",
        "Chemical Kinetics", "Classification of Elements and Periodicity in Properties",
        "p-Block Elements", "d- and f-Block Elements", "Coordination Compounds",
        "Purification and Characterization of Organic Compounds", "Hydrocarbons",
        "Organic Compounds Containing Halogens", "Organic Compounds Containing Oxygen",
        "Organic Compounds Containing Nitrogen", "Biomolecules", "Principles of Practical Chemistry"
    ],
    "Biology": [
        "Diversity in Living World", "Structural Organisation in Animals and Plants",
        "Cell Structure and Function", "Plant Physiology", "Human Physiology",
        "Reproduction", "Genetics and Evolution", "Biology and Human Welfare",
        "Biotechnology and Its Applications", "Ecology and Environment"
    ]
}

# Folder for storing responses
RESPONSE_FOLDER = "responses"
os.makedirs(RESPONSE_FOLDER, exist_ok=True)

def call_gemini_api_page_by_page(diagram_info_json, pdf_images=None, interval=30, max_retries=5):
    try:
        with open(diagram_info_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return f"Error loading {diagram_info_json}: {e}"
    page_results = {}
    for page_id, info in data.items():
        output_file = os.path.join(RESPONSE_FOLDER, f"page_{page_id}.json")
        if os.path.exists(output_file):
            print(f"✅ Page {page_id} already processed. Skipping...")
            continue
        extracted_text = info.get("page_text", "")
        diagram_links = {page_id: info.get("diagrams", [])}
        prompt_header = (
            "You are an expert NEET exam assistant. Your task is to process OCR text from a single page "
            "of a NEET exam and provide structured question data.\n\n"
            "The data format should be a JSON array, with each question containing:\n"
            '  - "subject": (Pick the correct subject from the NEET syllabus below),\n'
            '  - "chapter": (Pick the closest matching chapter from the syllabus below),\n'
            '  - "question": (Exact text from OCR or minimal paraphrase),\n'
            '  - "options": (List of choices, if found),\n'
            '  - "correct_option": (Correct option from List of choices),\n'
            '  - "diagram_url": (The matching diagram URL if relevant, else ""),\n'
            '  - "solution": (Brief solution with the correct answer).\n\n'
        )
        prompt_syllabus = "Recognized NEET Chapters:\n"
        for subject, chapters in NEET_SYLLABUS.items():
            prompt_syllabus += f"\n{subject}:\n" + "\n".join(f"- {ch}" for ch in chapters) + "\n"
        prompt_body = f"\nOCR Text for Page {page_id}:\n{extracted_text}\n\n"
        if pdf_images:
            prompt_body += "PDF Page Images (for reference only, do NOT include in final answer):\n"
            for p_id, url in pdf_images.items():
                if p_id == page_id:
                    prompt_body += f"- Page {p_id}: {url}\n"
            prompt_body += "\n(Use these only to understand context.)\n\n"
        if diagram_links:
            prompt_diagrams = f"Detected Diagrams for Page {page_id}:\n"
            for entry in diagram_links.get(page_id, []):
                diagram_url = entry.get("diagram_url", "")
                bbox = entry.get("bbox", "")
                class_label = entry.get("class", "")
                prompt_diagrams += f" - {class_label} at {bbox}, URL: {diagram_url}\n"
            prompt_body += prompt_diagrams + "\n\n"
        prompt_instructions = (
            "Final Output Format:\n"
            "Return a valid JSON array (no extra text). Each element must include:\n"
            '  "subject", "chapter", "question", "options","correct_option", "diagram_url", "solution"\n\n'
            "Example:\n"
            '[\n'
            '  {\n'
            '    "subject": "Physics",\n'
            '    "chapter": "Kinematics",\n'
            '    "question": "Exact question text...",\n'
            '    "options": ["A) ...", "B) ..."],\n'
            '    "correct_option": [1,0,0,0](example of A as correct answer)'
            '    "diagram_url": "http://cloudinary.com/...",\n'
            '    "solution": "Correct option is X. Explanation: ..."\n'
            '  }\n'
            ']\n\n'
            "Ensure the final output is strictly valid JSON. No extra commentary.\n"
            "Chapter names MUST be picked from the syllabus list above.\n"
        )

        final_prompt = prompt_header + prompt_syllabus + prompt_body + prompt_instructions
        retry_count = 0
        success = False
        while retry_count < max_retries and not success:
            try:
                model = genai.GenerativeModel("gemini-1.5-pro")
                response = model.generate_content(final_prompt)
                if not response or not response.text:
                    raise ValueError("No output text returned from Gemini.")

                # Save response locally
                raw_content = response.text.strip()
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(raw_content)

                print(f"✅ Page {page_id} processed successfully. Saved to {output_file}")
                success = True
                page_results[page_id] = raw_content

            except Exception as e:
                print(f"⚠️ Error processing Page {page_id}: {e}. Retrying in {interval} seconds...")
                retry_count += 1
                time.sleep(interval)

        if not success:
            print(f"❌ Max retries reached. Could not process Page {page_id}. Skipping...")

    return page_results
