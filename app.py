from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import mysql.connector
from backend.chatbot import get_chatbot_response 
from backend.login import check_login, get_admin_id
from backend.dashboard import get_total_data, get_total_evaluasi
from backend import data
from backend.evaluasi import get_all_evaluasi, delete_evaluasi
from backend.profil import get_admin_profile, update_admin_profile

app = Flask(__name__, template_folder="front-end")  # Menyesuaikan folder HTML
app.secret_key = "poliban_123"
from flask import send_file
import io

# Halaman landing
@app.route("/")
def landing():
    return render_template("landing_page.html")  # Halaman landing page

# Halaman chatbot
@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")  # Halaman chatbot

# Endpoint untuk menerima pesan dan mengirimkan balasan
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.get_json().get("message")  # Mendapatkan pesan pengguna
        if not user_message:
            return jsonify({"response": "❗ Pesan tidak boleh kosong."})

        # Mendapatkan respons chatbot
        bot_response = get_chatbot_response(user_message)

        # Mengirimkan balasan ke frontend
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"response": f"❗ Terjadi kesalahan: {str(e)}"})

# Halaman poliban
@app.route("/poliban")
def poliban():
    return render_template("poliban.html")  # Halaman poliban 

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if check_login(username, password):
            # Simpan admin_id ke session
            admin_id = get_admin_id(username)
            session["admin_id"] = admin_id

            return redirect(url_for("dashboard"))  # atau halaman lain
        else:
            flash("Nama pengguna atau kata sandi salah.", "error")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    total_data = get_total_data()
    total_evaluasi = get_total_evaluasi()
    return render_template("dashboard.html", total_data=total_data, total_evaluasi=total_evaluasi)

# Route untuk halaman data (menampilkan daftar data)
@app.route("/data")
def data_page():
    all_data = data.get_all_data()  # Ambil data dari fungsi data.py
    return render_template("data.html", data=all_data)

# Route untuk download file
@app.route("/download/<int:data_id>")
def download_file(data_id):
    file_record = data.get_file_by_id(data_id)
    if file_record:
        nama_file = file_record['nama'] + ".txt"  # Akses dict pakai key
        file_data = file_record['data']
        return send_file(
            io.BytesIO(file_data),
            mimetype="text/plain",
            as_attachment=True,
            download_name=nama_file
        )
    else:
        flash("File tidak ditemukan.", "error")
        return redirect(url_for("data_page"))


# Route untuk detail data
@app.route("/detail/<int:data_id>")
def detail_data(data_id):
    detail = data.get_file_by_id(data_id)
    if detail:
        return render_template("detail_data.html", detail=detail)
    else:
        flash("Data tidak ditemukan.", "error")
        return redirect(url_for("data_page"))

# Route untuk hapus data
@app.route("/hapus/<int:data_id>")
def hapus_data(data_id):
    data.delete_data(data_id)
    flash("Data berhasil dihapus.", "success")
    return redirect(url_for("data_page"))


# Route untuk halaman tambah data (form untuk menambah data)
@app.route("/tambah_data", methods=["GET", "POST"])
def tambah_data():
    if request.method == "POST":
        nama = request.form["nama"]
        file = request.files["file"]
        
        # Ambil admin_id dari session
        admin_id = session.get("admin_id")
        
        # Pastikan admin_id tersedia
        if not admin_id:
            return redirect(url_for("login"))  # Jika belum login, kembalikan ke login

        # Simpan data menggunakan fungsi dari data.py
        data.save_data(nama, file, admin_id)  # Kirim juga admin_id

        return redirect(url_for("data_page"))  # Setelah simpan, kembali ke halaman data

    return render_template("tambah_data.html")

@app.route("/evaluasi")
def tampilkan_evaluasi():
    evaluasi_list = get_all_evaluasi()
    return render_template("evaluasi.html", evaluasi_list=evaluasi_list)

@app.route("/hapus-evaluasi/<int:evaluasi_id>")
def hapus_evaluasi(evaluasi_id):
    delete_evaluasi(evaluasi_id)
    return redirect(url_for("tampilkan_evaluasi"))


@app.route('/profil')
def profil():
    # Memeriksa apakah admin_id ada di session
    if "admin_id" not in session:
        return redirect(url_for("login"))  # Arahkan ke halaman login jika belum login

    # Ambil profil admin menggunakan admin_id dari session
    admin_profile = get_admin_profile(session["admin_id"])  # Gunakan session["admin_id"] bukan 1
    
    print(admin_profile)  # Menambahkan print untuk debugging
    
    if admin_profile:
        return render_template('profil.html', profile=admin_profile)  # Pastikan menggunakan profil.html
    else:
        return "Admin tidak ditemukan", 404

@app.route("/edit-profil", methods=["GET", "POST"])
def edit_profil():
    # Memeriksa apakah admin_id ada di session
    if "admin_id" not in session:
        return redirect(url_for("login"))  # Arahkan ke halaman login jika belum login

    # Ambil profil admin menggunakan admin_id dari session
    admin_profile = get_admin_profile(session["admin_id"])  # Gunakan session["admin_id"]

    if request.method == "POST":
        # Ambil data dari form
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        nip = request.form.get("nip")
        foto = request.files.get("foto")

        foto_bytes = foto.read() if foto else None


        # Update profil di database
        update_admin_profile(session["admin_id"], fullname, username, nip, foto_bytes)


        flash("Profil berhasil diperbarui.", "success")
        return redirect(url_for("profil"))

    # Jika GET request, tampilkan form edit dengan data profil
    return render_template("edit_profil.html", profile=admin_profile)

# Route untuk logout
@app.route("/logout")
def logout():
    session.pop("admin_id", None)  # Menghapus admin_id dari session
    return redirect(url_for("login"))  # Redirect ke halaman login

if __name__ == "__main__":
    app.run(debug=True)
