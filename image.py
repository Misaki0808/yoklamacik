import requests
from bs4 import BeautifulSoup

def get_verification_token(session, url):
    """OBS giriş sayfasından doğrulama token'ını alır."""
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        print(f"Giriş sayfasına erişim başarısız: {response.status_code}")
        return None

def login_to_aksis(session, username, password, login_url, token):
    """aksis sistemine giriş yapar."""
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    response = session.post(login_url, data=login_data)
    if response.status_code == 200 and "Giriş başarısız" not in response.text:
        print("Aksis'e başarılı giriş")
        return True
    else:
        print("Aksis'e giriş başarısız")
        return False

def access_obs_home(session, obs_url):
    """OBS ana sayfasına erişim sağlar."""
    response = session.get(obs_url)
    if response.status_code == 200:
        print("OBS ana sayfasına erişim sağlandı.")
        return True
    else:
        print(f"OBS ana sayfasına erişim sağlanamadı: {response.status_code}")
        return False

def get_profile_image_url(session, profile_url):
    """Profil fotoğrafı URL'sini alır."""
    response = session.get(profile_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        image_tag = soup.find("img", {"class": "profileImage"})
        if image_tag and 'src' in image_tag.attrs:
            profile_image_url = image_tag['src']
            # URL tam değilse ana URL ile birleştirin
            if not profile_image_url.startswith("http"):
                base_url = profile_url.split("/Profil")[0]
                profile_image_url = base_url + profile_image_url
            return profile_image_url
        else:
            print("Profil fotoğrafı URL'si bulunamadı.")
            return None
    else:
        print(f"Profil sayfasına erişim başarısız: {response.status_code}")
        return None

def download_profile_image(session, image_url):
    """Profil fotoğrafını indirir."""
    response = session.get(image_url, stream=True)
    if response.status_code == 200:
        with open("profile_image.jpg", "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print("Profil fotoğrafı başarıyla indirildi: profile_image.jpg")
    else:
        print(f"Profil fotoğrafı indirilemedi: {response.status_code}")

def main():
    username = input("Kullanıcı Adı (TC): ")
    password = input("Şifre: ")

    # Giriş ve erişim URL'leri
    login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    obs_url = "https://obs.istanbul.edu.tr"
    profile_url = "https://obs.istanbul.edu.tr/Profil/Ozluk"

    session = requests.Session()

    # Doğrulama token'ını al ve giriş yap
    token = get_verification_token(session, login_url)
    if token and login_to_aksis(session, username, password, login_url, token):
        # OBS ana sayfasına eriş
        if access_obs_home(session, obs_url):
            # Profil sayfasına eriş ve fotoğraf URL'sini al
            profile_image_url = get_profile_image_url(session, profile_url)
            if profile_image_url:
                print(f"Profil fotoğrafı URL'si bulundu: {profile_image_url}")
                # Fotoğrafı indir
                download_profile_image(session, profile_image_url)
            else:
                print("Profil fotoğrafı URL'si bulunamadı.")
        else:
            print("OBS ana sayfasına erişilemedi.")
    else:
        print("OBS giriş başarısız.")

if __name__ == "__main__":
    main()
