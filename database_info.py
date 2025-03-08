import mysql.connector
DATABASE_CONFIG = {
    'host': 'auth-db982.hstgr.io',
    'user': 'u273147311_admin',
    'password': 'Code4bharat@123',
    'database': 'u273147311_examportal'
}
# =========================== FUNCTION DEFINITIONS =========================== #
def get_next_ids():
    try:
        conn = mysql.connector.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM pdfs;")
        last_pdf_id = cursor.fetchone()[0]
        next_pdf_id = (last_pdf_id + 1) if last_pdf_id else 1
        cursor.execute("SELECT MAX(id) FROM questions;")
        last_question_id = cursor.fetchone()[0]
        next_question_id = (last_question_id + 1) if last_question_id else 1
        cursor.close()
        conn.close()
        return next_pdf_id, next_question_id
    
    except mysql.connector.Error as e:
        print(f"❌ Database Error: {e}")
        return None, None  # Return None if there's an error
 