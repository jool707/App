import streamlit as st
from PIL import Image
import pytesseract
import sqlite3
from datetime import datetime

DB_PATH = "image_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ocr_text TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_user_id(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if row:
        user_id = row[0]
    else:
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        user_id = c.lastrowid
    conn.close()
    return user_id

def get_user_ocr_texts(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ocr_text FROM images WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

def save_image_text(user_id, ocr_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("INSERT INTO images (user_id, ocr_text, timestamp) VALUES (?, ?, ?)",
              (user_id, ocr_text, now))
    conn.commit()
    conn.close()

def extract_numbers(text):
    import re
    numbers = re.findall(r'\d+', text)
    return set(numbers)

def is_duplicate(new_numbers, existing_ocr_texts):
    for text in existing_ocr_texts:
        existing_numbers = extract_numbers(text)
        if new_numbers == existing_numbers:
            return True
    return False

def main():
    st.title("فحص الصور وحذف الصور المتكررة حسب الأرقام (OCR)")

    username = st.text_input("أدخل اسم المستخدم")
    if not username:
        st.info("يرجى إدخال اسم المستخدم للاستمرار.")
        return

    user_id = get_user_id(username)

    uploaded_files = st.file_uploader("ارفع صورك (PNG, JPG)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

    if uploaded_files:
        existing_ocr_texts = get_user_ocr_texts(user_id)
        new_images_count = 0
        duplicates_count = 0

        for file in uploaded_files:
            try:
                img = Image.open(file)
                gray = img.convert('L')
                text = pytesseract.image_to_string(gray, config='--psm 6').strip()

                numbers_in_image = extract_numbers(text)

                if not numbers_in_image:
                    st.warning(f"الصورة '{file.name}' لا تحتوي على أرقام واضحة.")
                    continue

                if is_duplicate(numbers_in_image, existing_ocr_texts):
                    duplicates_count += 1
                else:
                    save_image_text(user_id, text)
                    existing_ocr_texts.append(text)
                    new_images_count += 1

            except Exception as e:
                st.error(f"خطأ في معالجة الصورة '{file.name}': {e}")

        st.success(f"تم رفع {new_images_count} صورة جديدة.")
        if duplicates_count > 0:
            st.warning(f"تم تجاهل {duplicates_count} صورة مكررة.")

        total_unique = len(get_user_ocr_texts(user_id))
        st.write(f"عدد الصور الفريدة حسب الأرقام: {total_unique}")
        if total_unique > 0:
            st.markdown("● " * total_unique)

if __name__ == "__main__":
    init_db()
    main()
