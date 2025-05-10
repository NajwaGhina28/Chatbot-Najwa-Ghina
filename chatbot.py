from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import mysql.connector
import requests
import string
import re

# === KONFIGURASI GEMINI ===
api = open("api_key.txt").read().strip()
endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api}"
headers = {"Content-type": "application/json"}

# === FUNGSI BANTU ===
def is_greeting_or_thanks(text):
    greetings = ['halo', 'hai', 'hello', 'selamat pagi', 'selamat siang', 'selamat malam', 'terima kasih', 'makasih']
    text = text.lower()
    return any(greet in text for greet in greetings)

def preprocess(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text

def remove_markdown(text):
    markdown_chars = ['**', '__', '*', '_', '`']
    for char in markdown_chars:
        text = text.replace(char, '')
    return text

def is_list_format(text):
    lines = text.strip().splitlines()
    list_pattern = re.compile(r"^(\d+[\.\)]|[-*•])\s+")
    count = sum(1 for line in lines if list_pattern.match(line.strip()))
    return count >= 2

def get_database_texts():
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="tugasakhir"
    )
    cursor = db.cursor()
    cursor.execute("SELECT data FROM data")
    rows = cursor.fetchall()
    db.close()
    return [row[0].decode('utf-8') if row[0] is not None else "" for row in rows]

def get_chatbot_response(user_input):
    if not user_input:
        return "Halo, selamat datang di polibot. Ada yang ingin anda tanyakan mengenai Poliban, seperti jurusan yang ada, pendaftaran, beasiswa, dll?"

    if is_greeting_or_thanks(user_input):
        return ask_gemini(user_input)

    processed_question = preprocess(user_input)
    documents = get_database_texts()

    if not documents:
        return "❗ Maaf, tidak ada informasi yang dapat saya akses."

    if len(processed_question.split()) == 1:
        for doc in documents:
            if processed_question in preprocess(doc):
                prompt = (
                    f"Pertanyaan:\n{user_input}\n\n"
                    f"Berikan jawaban yang jelas, singkat, dan terstruktur.\n"
                    f"Informasi pendukung:\n{doc}"
                )
                return ask_gemini(prompt)

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([processed_question] + documents)
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    print("Skor Kemiripan:", similarity)

    max_sim_index = similarity.argmax()
    max_sim_score = similarity[max_sim_index]

    if max_sim_score > 0.02:
        most_relevant = documents[max_sim_index]
        prompt = (
            f"Pertanyaan:\n{user_input}\n\n"
            f"Berikan jawaban yang jelas, singkat, dan terstruktur.\n"
            f"Gunakan poin-poin atau paragraf pendek bila perlu.\n\n"
            f"Informasi pendukung:\n{most_relevant}"
        )
        return ask_gemini(prompt)
    else:
        default_response = "❗ Maaf, saya belum memiliki informasi tentang itu."
        try:
            db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="tugasakhir"
            )
            cursor = db.cursor()
            query = "INSERT INTO evaluasi (pertanyaan, jawaban) VALUES (%s, %s)"
            cursor.execute(query, (user_input, default_response))
            db.commit()
            db.close()
        except mysql.connector.Error as err:
            print(f"❗ Gagal menyimpan ke database evaluasi: {err}")

        return default_response

def ask_gemini(prompt):
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        r = requests.post(endpoint, headers=headers, json=data, timeout=10)
        r.raise_for_status()
        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        clean = remove_markdown(raw)

        if is_list_format(clean):
            lines = [l.strip() for l in clean.split("\n") if l.strip()]
            html_parts = []
            in_ol = False
            in_ul = False

            for line in lines:
                match_jurusan = re.match(r"^(\d+)\.\s*(.*)", line)
                if match_jurusan:
                    # Tutup list sebelumnya jika ada
                    if in_ul:
                        html_parts.append("</ul></li>")
                        in_ul = False
                    if not in_ol:
                        html_parts.append("<ol class='jurusan'>")
                        in_ol = True
                    jurusan = match_jurusan.group(2)
                    html_parts.append(f"<li><strong>{jurusan}</strong><ul class='prodi'>")
                    in_ul = True
                else:
                    html_parts.append(f"<li>{line}</li>")

            if in_ul:
                html_parts.append("</ul></li>")
            if in_ol:
                html_parts.append("</ol>")

            return "".join(html_parts)

        else:
            return f"<p>{clean}</p>"

    except requests.exceptions.RequestException as e:
        return f"❗ Gagal menghubungi API: {e}"
