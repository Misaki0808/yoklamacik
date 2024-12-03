import base64
from flask import Flask, jsonify, request, send_from_directory
import requests
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='.', static_url_path='')

# URLs
LOGIN_URL = "https://aksis.istanbul.edu.tr/Account/LogOn"
OBS_HOME_URL = "https://obs.istanbul.edu.tr"
PROFILE_URL = "https://obs.istanbul.edu.tr/Profil/Ozluk"


def get_verification_token(session, url):
    """OBS giriş sayfasından doğrulama token'ını alır."""
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        raise Exception(f"Doğrulama token'ı alınamadı: {response.status_code}")


def login_to_aksis(session, username, password, token):
    """Aksis sistemine giriş yapar."""
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
    """OBS ana sayfasına erişim sağlar."""
    response = session.get(OBS_HOME_URL)
    if response.status_code == 200:
        return True
    else:
        raise Exception(f"OBS ana sayfasına erişim sağlanamadı: {response.status_code}")


def get_profile_image(session):
    """Profil fotoğrafını indirir ve base64 formatında döner."""
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
                # Base64 olarak kodla
                image_base64 = base64.b64encode(image_response.content).decode('utf-8')
                return f"data:image/jpeg;base64,{image_base64}"
            else:
                raise Exception(f"Profil fotoğrafı indirilemedi: {image_response.status_code}")
        else:
            raise Exception("Profil fotoğrafı URL'si bulunamadı.")
    else:
        raise Exception(f"Profil sayfasına erişim başarısız: {response.status_code}")


@app.route('/', methods=['GET'])
def index():
    """GET isteği geldiğinde index.html dosyasını döndürür."""
    return send_from_directory('.', 'index.html')


@app.route('/get-profile-image', methods=['POST'])
def get_profile_image_endpoint():
    """
    Kullanıcıdan alınan bilgilerle giriş yapar ve profil fotoğrafını base64 formatında döner.
    """
    try:
        # JSON'dan kullanıcı adı ve şifreyi al
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Kullanıcı adı ve şifre gereklidir."}), 400

        # Oturum başlat
        session = requests.Session()

        # Aksis'e giriş yap
        token = get_verification_token(session, LOGIN_URL)
        login_to_aksis(session, username, password, token)

        # OBS ana sayfasına eriş
        access_obs_home(session)

        # Profil fotoğrafını al ve base64 olarak döndür
        profile_image_base64 = get_profile_image(session)
        return jsonify({"profile_image": profile_image_base64}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
