from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_session import Session
import requests
from urllib.parse import parse_qs, urlparse
import json
import secrets
import os
from functions import datetime_converter, read_data_array, is_time_in_range, find_lesson, get_verification_token, login_to_aksis, check_aksis_api, extract_dynamic_url, extract_ids_from_url, post_dynamic_api_data, post_to_obs_results
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Güvenli bir gizli anahtar oluşturun

from datetime import timedelta

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the file system
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = './flask_session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # 30 dakika oturum süresi
Session(app)

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
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        try:
            aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
            aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
            obs_url = "https://obs.istanbul.edu.tr"
            obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/DersProgramiYeni"

            requests_session = requests.Session()
            token = get_verification_token(requests_session, aksis_login_url)

            if token and login_to_aksis(requests_session, username, password, aksis_login_url, token):
                if check_aksis_api(requests_session, aksis_api_url):
                    print("Aksis sayfasına erişim sağlandı")
                    response_first = requests_session.get(obs_url)
                    if response_first.status_code == 200:
                        print("İlk OBS sayfasına erişim sağlandı")
                        lessons = post_to_obs_results(requests_session, obs_post_url, obs_url)
                        session['lessons'] = lessons  # Store lessons in the session
                        return jsonify({"success": True}), 200
                    else:
                        print(f"İlk OBS sayfasına erişim sağlanamadı: {response_first.status_code}")
                        return jsonify({"error": f"İlk OBS sayfasına erişim sağlanamadı: {response_first.status_code}"}), 500
                else:
                    print("Username or password is not valid, try again.")
                    return jsonify({"error": "Username or password is not valid, try again."}), 500
            else:
                print("Aksis giriş başarısız")
                return jsonify({"error": "Aksis giriş başarısız"}), 500
        except Exception as e:
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
        return render_template('auth.html',current_lesson=current_lesson)

    return jsonify({"error": "No lesson found for you now"}), 404

if __name__ == '__main__':
    app.run(debug=True)
