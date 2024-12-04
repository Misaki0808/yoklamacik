import base64
from flask import Flask, jsonify, request, send_from_directory
import requests
from bs4 import BeautifulSoup
from deepface import DeepFace
import cv2
import numpy as np
from PIL import Image
import io

app = Flask(__name__, static_folder='.', static_url_path='')

# URLs
LOGIN_URL = "https://aksis.istanbul.edu.tr/Account/LogOn"
OBS_HOME_URL = "https://obs.istanbul.edu.tr"
PROFILE_URL = "https://obs.istanbul.edu.tr/Profil/Ozluk"


def get_verification_token(session, url):
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        raise Exception(f"Doğrulama token'ı alınamadı: {response.status_code}")


def login_to_aksis(session, username, password, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    response = session.post(LOGIN_URL, data=login_data)
    if response.status_code == 200 and "Giriş başarısız" not in response.text:
        return True
    else:
        raise Exception("Giriş başarısız. Kullanıcı adı veya şifre hatalı.")


def access_obs_home(session):
    response = session.get(OBS_HOME_URL)
    if response.status_code == 200:
        return True
    else:
        raise Exception(f"OBS ana sayfasına erişim sağlanamadı: {response.status_code}")


def get_profile_image(session):
    response = session.get(PROFILE_URL)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        image_tag = soup.find("img", {"class": "profileImage"})
        if image_tag and 'src' in image_tag.attrs:
            image_url = image_tag['src']
            if not image_url.startswith("http"):
                base_url = PROFILE_URL.split("/Profil")[0]
                image_url = base_url + image_url

            # Profil fotoğrafını indir
            image_response = session.get(image_url)
            if image_response.status_code == 200:
                image_base64 = base64.b64encode(image_response.content).decode('utf-8')
                return f"data:image/jpeg;base64,{image_base64}"
            else:
                raise Exception(f"Profil fotoğrafı indirilemedi: {image_response.status_code}")
        else:
            raise Exception("Profil fotoğrafı URL'si bulunamadı.")
    else:
        raise Exception(f"Profil sayfasına erişim başarısız: {response.status_code}")


def decode_base64_to_image(base64_string):
    """Base64 string'ini OpenCV formatında bir numpy array'e çevirir."""
    image_data = base64.b64decode(base64_string.split(",")[1])
    pil_image = Image.open(io.BytesIO(image_data)).convert("RGB")
    return np.array(pil_image)


@app.route('/', methods=['GET'])
def index():
    return send_from_directory('.', 'index.html')


@app.route('/get-profile-image', methods=['POST'])
def get_profile_image_endpoint():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Kullanıcı adı ve şifre gereklidir."}), 400

        session = requests.Session()
        token = get_verification_token(session, LOGIN_URL)
        login_to_aksis(session, username, password, token)
        access_obs_home(session)
        profile_image_base64 = get_profile_image(session)
        return jsonify({"profile_image": profile_image_base64}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/compare-faces', methods=['POST'])
def compare_faces():
    try:
        data = request.json
        obs_image_base64 = data['obsImage']
        webcam_image_base64 = data['webcamImage']

        # Görselleri Base64'ten numpy array'e çevir
        obs_image = decode_base64_to_image(obs_image_base64)
        webcam_image = decode_base64_to_image(webcam_image_base64)

        # DeepFace ile karşılaştırma
        result = DeepFace.verify(obs_image, webcam_image, enforce_detection=False)

        # Sonuç döndür
        return jsonify({
            "match": result["verified"],
            "distance": result["distance"],
            "threshold": result["threshold"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
