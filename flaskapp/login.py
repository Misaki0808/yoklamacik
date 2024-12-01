from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, urlparse
import json
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Güvenli bir gizli anahtar oluşturun

# Function to parse, convert to UTC+3, and round up to the nearest minute
def datetime_converter(date_str):
    timestamp_ms = int(date_str.strip("/Date()/"))
    timestamp_s = timestamp_ms / 1000
    utc_datetime = datetime.fromtimestamp(timestamp_s, timezone.utc)
    utc_plus_3 = utc_datetime + timedelta(hours=3)
    if utc_plus_3.second > 0 or utc_plus_3.microsecond > 0:
        utc_plus_3 = (utc_plus_3 + timedelta(minutes=1)).replace(second=0, microsecond=0)
    formatted = utc_plus_3.strftime("%Y-%m-%d %H:%M")
    return formatted

def read_data_array(data):
    for lesson in data:
        yield lesson

def is_time_in_range(start, end, check_time):
    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M")
    check_time_dt = datetime.strptime(check_time, "%Y-%m-%d %H:%M")
    return start_dt <= check_time_dt <= end_dt

def find_lesson(data, date_time):
    for lesson in read_data_array(data):
        start = datetime_converter(lesson["Start"])
        end = datetime_converter(lesson["End"])
        if is_time_in_range(start, end, date_time):
            return lesson["Title"]
    return "there is no lesson for you now"

def get_verification_token(requests_session, url):
    response = requests_session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        print(f"Giriş sayfasına erişim başarısız: {response.status_code}")
        return None

def login_to_aksis(requests_session, username, password, login_url, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    response = requests_session.post(login_url, data=login_data)
    if response.status_code == 200 and "Oturum açma başarısız" not in response.text:
        print("Aksis'e başarılı giriş")
        return True
    else:
        print("Aksis giriş başarısız")
        return False

def check_aksis_api(requests_session, api_url):
    response = requests_session.post(api_url)
    if response.status_code == 200:
        try:
            json_response = response.json()
            print("Aksis API Yanıtı: ", json_response)
            return json_response.get('IsSuccess') == True
        except ValueError:
            print("Aksis API yanıtı JSON formatında değil")
            return False
    else:
        print(f"Aksis API isteğinde hata: {response.status_code}")
        return False

def extract_dynamic_url(soup):
    script_tags = soup.find_all("script")
    for script in script_tags:
        if "Plans_Read" in script.text:
            start_idx = script.text.find("/OgrenimBilgileri/DersProgramiYeni/Plans_Read")
            if start_idx != -1:
                end_idx = script.text.find('"', start_idx)
                dynamic_url = script.text[start_idx:end_idx]
                return dynamic_url
    return None

def extract_ids_from_url(dynamic_url):
    fixed_url = dynamic_url.replace(r"\u0026", "&")
    query_params = parse_qs(urlparse(fixed_url).query)
    ogrenci_id = query_params.get("OgrenciId", [None])[0]
    birim_id = query_params.get("BirimId", [None])[0]
    return ogrenci_id, birim_id

def post_dynamic_api_data(requests_session, base_url, dynamic_url, ogrenci_id, birim_id, yil, donem):
    full_url = f"{base_url}{dynamic_url}"
    payload = {
        "OgrenciId": ogrenci_id,
        "BirimId": birim_id,
        "Yil": yil,
        "Donem": donem
    }
    response = requests_session.post(full_url, data=payload)
    if response.status_code == 200:
        try:
            data = response.json()
            return data
        except ValueError:
            print("API yanıtı JSON formatında değil.")
            return None
    else:
        print(f"API isteği başarısız: {response.status_code}")
        return None

def post_to_obs_results(requests_session, url, base_url):
    payload = {
        "yil": '2024',
        "donem": '1'
    }
    response = requests_session.post(url, data=payload)
    if response.status_code == 200:
        print("POST isteği başarılı.")
        soup = BeautifulSoup(response.text, "html.parser")
        dynamic_url = extract_dynamic_url(soup)
        if dynamic_url:
            print(f"Dinamik URL bulundu: {dynamic_url}")
            ogrenci_id, birim_id = extract_ids_from_url(dynamic_url)
            if ogrenci_id and birim_id:
                print(f"Öğrenci ID: {ogrenci_id}, Birim ID: {birim_id}")
                data = post_dynamic_api_data(requests_session, base_url, dynamic_url, ogrenci_id, birim_id, "2024", "1")
                return data
            else:
                print("Dinamik URL'den ID'ler çıkarılamadı.")
        else:
            print("Dinamik URL bulunamadı.")
    else:
        print(f"POST isteğinde hata: {response.status_code}")
    return None

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
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
                    if lessons is None:
                        return jsonify({"error": "OBS sonuçları alınamadı"}), 500
                    
                    # Veriyi oturumda saklayın
                    session['lessons'] = lessons
                    return jsonify({"success": True}), 200
                else:
                    print(f"İlk OBS sayfasına erişim sağlanamadı: {response_first.status_code}")
                    return jsonify({"error": f"İlk OBS sayfasına erişim sağlanamadı: {response_first.status_code}"}), 500
            else:
                print("Aksis API erişimi sağlanamadı")
                return jsonify({"error": "Aksis API erişimi sağlanamadı"}), 500
        else:
            print("Aksis giriş başarısız")
            return jsonify({"error": "Aksis giriş başarısız"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/results')
def results():
    lessons = session.get('lessons')  # JSON verisini oturumdan alın
    if not lessons:
        lessons = []

    # Şu anki zamanı alın
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Şu anki zamana göre dersi bulun
    current_lesson = find_lesson(lessons, current_time)

    if current_lesson != "there is no lesson for you now":
        return render_template('auth.html')

    return render_template('results.html', lessons=lessons, current_lesson=current_lesson)

if __name__ == '__main__':
    app.run(debug=True)