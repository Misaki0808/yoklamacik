import base64
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
import requests
import face_recognition
import numpy as np
from PIL import Image
import io


# Datetime İşlemleri
def datetime_converter(date_str):
    timestamp_ms = int(date_str.strip("/Date()/"))
    timestamp_s = timestamp_ms / 1000
    utc_datetime = datetime.fromtimestamp(timestamp_s, timezone.utc)
    utc_plus_3 = utc_datetime + timedelta(hours=3)
    if utc_plus_3.second > 0 or utc_plus_3.microsecond > 0:
        utc_plus_3 = (utc_plus_3 + timedelta(minutes=1)).replace(second=0, microsecond=0)
    formatted = utc_plus_3.strftime("%Y-%m-%d %H:%M")
    return formatted


# JSON Veri Okuma ve Zaman Aralığı Kontrolü
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


# Aksis Giriş ve Doğrulama Fonksiyonları
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


# OBS ve Dinamik URL İşlemleri
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
def access_obs_home(session):
    """
    OBS ana sayfasına erişerek oturum çerezlerini doğrular.
    """
    OBS_HOME_URL = "https://obs.istanbul.edu.tr"
    response = session.get(OBS_HOME_URL)
    if response.status_code == 200:
        print("OBS ana sayfasına erişim sağlandı.")
        return True
    else:
        raise Exception(f"OBS ana sayfasına erişim sağlanamadı: {response.status_code}")


# Profil Fotoğrafı ve Yüz Tanıma İşlemleri
def get_profile_image(session):
    """
    Fetches the student's profile image in base64 format.
    """
    PROFILE_URL = "https://obs.istanbul.edu.tr/Profil/Ozluk"

    # Önce OBS ana sayfasına erişin
    access_obs_home(session)

    # Profil sayfasına erişin
    response = session.get(PROFILE_URL)
    if response.status_code != 200:
        raise Exception("Profil sayfasına erişim başarısız: " + str(response.status_code))

    soup = BeautifulSoup(response.text, "html.parser")
    image_tag = soup.find("img", {"class": "profileImage"})  # Sınıf adını kontrol edin

    if not image_tag or 'src' not in image_tag.attrs:
        raise Exception("Profil fotoğrafı bulunamadı veya yüklenmemiş.")

    image_url = image_tag['src']
    if not image_url.startswith("http"):
        base_url = PROFILE_URL.split("/Profil")[0]
        image_url = base_url + image_url

    # Resmi indir
    image_response = session.get(image_url)
    if image_response.status_code != 200:
        raise Exception("Profil fotoğrafı indirilemedi: " + str(image_response.status_code))

    # Base64'e dönüştür
    return f"data:image/jpeg;base64,{base64.b64encode(image_response.content).decode('utf-8')}"




def decode_base64_to_image(base64_string):
    image_data = base64.b64decode(base64_string.split(",")[1])
    pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
    return np.array(pil_image)


def compare_faces(obs_image_path, webcam_image_path):
    """
    Compares two images to determine if the faces match.
    """
    try:
        obs_image = face_recognition.load_image_file(obs_image_path)
        webcam_image = face_recognition.load_image_file(webcam_image_path)

        obs_face_locations = face_recognition.face_locations(obs_image)
        webcam_face_locations = face_recognition.face_locations(webcam_image)

        if not obs_face_locations:
            raise ValueError("No face detected in the OBS profile image.")
        if not webcam_face_locations:
            raise ValueError("No face detected in the webcam image.")

        obs_encoding = face_recognition.face_encodings(obs_image, obs_face_locations)[0]
        webcam_encoding = face_recognition.face_encodings(webcam_image, webcam_face_locations)[0]

        # Compute Euclidean distance
        distance = np.linalg.norm(obs_encoding - webcam_encoding)
        threshold = 0.65  # Adjust this threshold if necessary
        is_match = distance < threshold

        print(f"Distance: {distance}, Threshold: {threshold}, Match: {is_match}")
        return is_match
    except IndexError as e:
        print(f"Face not detected in one of the images. Error: {e}")
        return False
