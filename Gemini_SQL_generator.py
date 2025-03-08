import json
import os
from database_info import get_next_ids

SQL_OUTPUT_FOLDER = "sql_outputs"
os.makedirs(SQL_OUTPUT_FOLDER, exist_ok=True)

def generate_sql_from_json(json_file, pdf_name):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return

    # Get the next available IDs
    next_pdf_id, next_question_id = get_next_ids()
    if next_pdf_id is None or next_question_id is None:
        print("❌ Could not retrieve database IDs. Exiting...")
        return

    chapter_pdf_mapping = {}  # Dictionary to store `pdf_id` for each chapter
    sql_statements = []

    # 1️⃣ **Insert statements for PDFs table (one row per unique chapter)**
    for entry in data:
        subject = entry["subject"]
        chapter = entry["chapter"]

        if chapter not in chapter_pdf_mapping:
            chapter_pdf_mapping[chapter] = next_pdf_id
            sql_statements.append(
                f"INSERT INTO pdfs (id, pdf_name, subject, exam_type, chapter_name, difficulty_level) "
                f"VALUES ({next_pdf_id}, '{pdf_name}', '{subject}', 'NEET', '{chapter}', 'simple');"
            )
            next_pdf_id += 1

    # 2️⃣ **Insert statements for Questions table**
    for entry in data:
        chapter = entry["chapter"]
        question_text = entry["question"]
        pdf_id = chapter_pdf_mapping[chapter]  # Get correct `pdf_id` from mapping

        sql_statements.append(
            f"INSERT INTO questions (id, pdf_id, question_text) "
            f"VALUES ({next_question_id}, {pdf_id}, '{question_text}');"
        )
        question_id = next_question_id  # Store current `question_id`
        next_question_id += 1  # Increment for next question

        # 3️⃣ **Insert statements for Options table**
        correct_answer = entry["solution"].split(" ")[-1].strip(".")  # Extract last word as correct answer
        for option in entry["options"]:
            option_text = option.strip()
            is_correct = 1 if option.startswith(correct_answer) else 0

            sql_statements.append(
                f"INSERT INTO options (question_id, option_text, is_correct) "
                f"VALUES ({question_id}, '{option_text}', {is_correct});"
            )

        # 4️⃣ **Insert statement for Solutions table**
        solution_text = entry["solution"]
        sql_statements.append(
            f"INSERT INTO solutions (question_id, solution_text) "
            f"VALUES ({question_id}, '{solution_text}');"
        )

        # 5️⃣ **Insert statement for Diagrams table (if applicable)**
        diagram_url = entry["diagram_url"]
        if diagram_url:
            sql_statements.append(
                f"INSERT INTO diagrams (question_id, diagram_path) "
                f"VALUES ({question_id}, '{diagram_url}');"
            )

    # Save the generated SQL to a file
    sql_file = os.path.join(SQL_OUTPUT_FOLDER, f"{pdf_name}_output.sql")
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_statements))

    print(f"✅ SQL file generated successfully: {sql_file}")

