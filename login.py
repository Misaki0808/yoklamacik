from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_session import Session
import requests
import base64
from urllib.parse import parse_qs, urlparse
import json
import secrets
import os
from functions import (
    datetime_converter,
    read_data_array,
    is_time_in_range,
    find_lesson,
    get_verification_token,
    login_to_aksis,
    check_aksis_api,
    extract_dynamic_url,
    extract_ids_from_url,
    post_dynamic_api_data,
    post_to_obs_results,
    get_profile_image,
    compare_faces,
    access_obs_home
)
from datetime import datetime, timedelta
import time
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Güvenli bir gizli anahtar oluşturun

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the file system
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = './flask_session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 dakika oturum süresi
Session(app)

def clean_session_files(session_dir, lifetime):
    """
    Eski oturum dosyalarını temizlemek için yardımcı fonksiyon.
    """
    now = time.time()
    for filename in os.listdir(session_dir):
        file_path = os.path.join(session_dir, filename)
        if os.path.isfile(file_path):
            if now - os.path.getmtime(file_path) > lifetime:
                os.remove(file_path)
                print(f"Eski oturum dosyası silindi: {file_path}")

def start_cleaner():
    """
    Oturum dosyalarını temizlemek için zamanlayıcıyı başlatır.
    """
    session_dir = app.config['SESSION_FILE_DIR']
    lifetime = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
    scheduler = BackgroundScheduler()
    scheduler.add_job(clean_session_files, 'interval', minutes=30, args=[session_dir, lifetime])
    scheduler.start()

def initialize():
    """
    İlk istekten önce temizleyici zamanlayıcıyı başlat.
    """
    start_cleaner()

# Uygulama bağlamında initialize fonksiyonunu çalıştır
with app.app_context():
    initialize()


@app.route('/logout')
def logout():
    session.clear()  # Oturumu temizle
    print("Oturum temizlendi.")
    return redirect(url_for('index'))  # Ana sayfaya yönlendirme

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    session.permanent = True
    if request.method == 'GET':
        return render_template('loginogrenci.html')
    elif request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        webcam_image_base64 = data.get('webcamImage')  # Kullanıcıdan gelen webcam görüntüsü

        if not username or not password or not webcam_image_base64:
            return jsonify({"error": "Username, password, and webcam image are required"}), 400

        try:
            aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
            aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
            obs_url = "https://obs.istanbul.edu.tr"
            obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/DersProgramiYeni"

            # Oturum oluştur
            requests_session = requests.Session()
            token = get_verification_token(requests_session, aksis_login_url)

            # Aksis'e giriş
            if token and login_to_aksis(requests_session, username, password, aksis_login_url, token):
                if check_aksis_api(requests_session, aksis_api_url):
                    print("Aksis'e giriş başarılı.")

                    # OBS ana sayfasına erişim
                    access_obs_home(requests_session)

                    # Profil resmi alınıyor
                    profile_image_base64 = get_profile_image(requests_session)
                    if not profile_image_base64:
                        return jsonify({"error": "Failed to retrieve profile image"}), 500

                    # Yüz tanıma işlemi için dosyaları kaydet
                    profile_image_path = "profile_image.jpg"
                    webcam_image_path = "webcam_image.jpg"

                    # Base64 verilerini çöz ve dosyaya kaydet
                    with open(profile_image_path, "wb") as profile_file:
                        profile_file.write(base64.b64decode(profile_image_base64.split(",")[1]))
                    with open(webcam_image_path, "wb") as webcam_file:
                        webcam_file.write(base64.b64decode(webcam_image_base64.split(",")[1]))

                    # Yüz eşleşmesini kontrol et
                    is_match = compare_faces(profile_image_path, webcam_image_path)
                    if not is_match:
                        return jsonify({
                            "success": False,
                            "message": "Face mismatch: Access denied.",
                            "match": False,
                            "distance": 0.533,  # Örnek bir mesafe değeri
                            "threshold": 0.65
                        }), 403

                    # Ders bilgilerini al ve oturuma kaydet
                    lessons = post_to_obs_results(requests_session, obs_post_url, obs_url)
                    if lessons:
                        session['lessons'] = lessons  # Ders bilgilerini oturuma kaydet
                        print("Ders bilgileri başarıyla alındı ve oturuma kaydedildi.")
                    else:
                        print("Ders bilgileri alınamadı.")

                    return jsonify({
                        "success": True,
                        "message": "Login Successful",
                        "match": True
                    }), 200

                else:
                    return jsonify({"error": "Username or password is not valid"}), 401

            else:
                return jsonify({"error": "Aksis giriş başarısız"}), 500

        except Exception as e:
            print(f"Hata: {e}")
            return jsonify({"error": str(e)}), 500




@app.route('/academic_login', methods=['GET', 'POST'])
def academic_login():
    if request.method == 'GET':
        return render_template('loginakademisyen.html')
    # POST işlemleri burada yapılacak

@app.route('/resultsogrenci')
def results():
    lessons = session.get('lessons')  # JSON verisini oturumdan alın

    if not lessons:
        print("Oturumda dersler bulunamadı")
    else:
        lessons = lessons['Data']
        print(type(lessons))

    # Şu anki zamanı alın
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Şu anki zamana göre dersi bulun
    current_lesson = find_lesson(lessons, current_time)

    if current_lesson != "there is no lesson for you now":
        return render_template('auth.html', current_lesson=current_lesson)

    # Eğer ders bulunamazsa, hata mesajını oturuma kaydet
    session['error_message'] = "No lesson found for you now"
    return redirect(url_for('student_login'))  # Ana sayfaya yönlendirme


if __name__ == '__main__':
    app.run(debug=True)
