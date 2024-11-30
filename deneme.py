import requests
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone, timedelta
import json

# Function to parse, convert to UTC+3, and round up to the nearest minute
def datetime_converter(date_str):
    # Extract the timestamp (remove "/Date(" and ")/" and convert to int)
    timestamp_ms = int(date_str.strip("/Date()/"))
    # Convert to seconds
    timestamp_s = timestamp_ms / 1000
    # Convert to UTC datetime
    utc_datetime = datetime.fromtimestamp(timestamp_s, timezone.utc)
    # Convert to UTC+3 timezone
    utc_plus_3 = utc_datetime + timedelta(hours=3)
    # Round up to the next minute
    if utc_plus_3.second > 0 or utc_plus_3.microsecond > 0:
        utc_plus_3 = (utc_plus_3 + timedelta(minutes=1)).replace(second=0, microsecond=0)
    formatted=utc_plus_3.strftime("%Y-%m-%d %H:%M")
    return formatted


def read_data_array(file_path):
    with open(file_path, 'r') as file:
        # Load the file partially to access "data"
        for lesson in json.load(file)["Data"]:
            yield lesson




def is_time_in_range(start, end, check_time):
    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M")
    check_time_dt = datetime.strptime(check_time, "%Y-%m-%d %H:%M")
    
    return start_dt <= check_time_dt <= end_dt


def find_lesson(date_time):
    for lesson in read_data_array("data.json"):
        start=datetime_converter(lesson["Start"])
        end=datetime_converter(lesson["End"])
        
        #current_datetime=str(datetime.now())[0:16]

        if is_time_in_range(start,end,date_time):
            return lesson["Title"]
    return "there is no lesson for you now"

###########################################################
def get_verification_token(session, url):
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        print(f"Giriş sayfasına erişim başarısız: {response.status_code}")
        return None

def login_to_aksis(session, username, password, login_url, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    response = session.post(login_url, data=login_data)
    if response.status_code == 200 and "Oturum açma başarısız" not in response.text:
        print("Aksis'e başarılı giriş")
        return True
    else:
        print("Aksis giriş başarısız")
        return False

def check_aksis_api(session, api_url):
    response = session.post(api_url)
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
    """HTML kaynağından dinamik URL'yi çıkartır."""
    script_tags = soup.find_all("script")
    for script in script_tags:
        if "Plans_Read" in script.text:
            start_idx = script.text.find("/OgrenimBilgileri/DersProgramiYeni/Plans_Read")
            if start_idx != -1:
                end_idx = script.text.find('"', start_idx)  # URL bitişi
                dynamic_url = script.text[start_idx:end_idx]        
                return dynamic_url
    return None

def extract_ids_from_url(dynamic_url):
    """Dinamik URL'den Öğrenci ID ve Birim ID'sini çıkarır."""
    # Unicode kaçış karakterlerini çözüyoruz
    fixed_url = dynamic_url.replace(r"\u0026", "&")
    
    print(f"Düzeltilmiş Dinamik URL: {fixed_url}")  # Debug için ekleme
    
    # URL'yi ayrıştırıyoruz
    query_params = parse_qs(urlparse(fixed_url).query)
    ogrenci_id = query_params.get("OgrenciId", [None])[0]
    birim_id = query_params.get("BirimId", [None])[0]
    return ogrenci_id, birim_id

def post_dynamic_api_data(session, base_url, dynamic_url, ogrenci_id, birim_id, yil, donem):
    """API'ye dinamik olarak POST isteği gönderir."""
    full_url = f"{base_url}{dynamic_url}"
    payload = {
        "OgrenciId": ogrenci_id,
        "BirimId": birim_id,
        "Yil": yil,
        "Donem": donem
    }
    response = session.post(full_url, data=payload)
    if response.status_code == 200:
        try:
            data = response.json()
            print("API Yanıtı:", data)
            return data
        except ValueError:
            print("API yanıtı JSON formatında değil.")
            return None
    else:
        print(f"API isteği başarısız: {response.status_code}")
        return None

def post_to_obs_results(session, url, base_url):
    """OBS üzerinden veriyi çeker ve API'ye ek sorgu gönderir."""
    payload = {
        "yil": '2024',
        "donem": '1'
    }
    response = session.post(url, data=payload)
    if response.status_code == 200:
        print("POST isteği başarılı.")
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Dinamik URL'yi çıkart
        dynamic_url = extract_dynamic_url(soup)
        if dynamic_url:
            print(f"Dinamik URL bulundu: {dynamic_url}")
            
            # Dinamik URL'den Öğrenci ID ve Birim ID'yi çıkar
            ogrenci_id, birim_id = extract_ids_from_url(dynamic_url)
            if ogrenci_id and birim_id:
                print(f"Öğrenci ID: {ogrenci_id}, Birim ID: {birim_id}")
                
                # Dinamik URL ile API'ye sorgu gönder
                post_dynamic_api_data(session, base_url, dynamic_url, ogrenci_id, birim_id, "2024", "1")
                student_date="2024-11-28 10:23"
                lesson=find_lesson(student_date)
                print (lesson)
            else:
                print("Dinamik URL'den ID'ler çıkarılamadı.")
        else:
            print("Dinamik URL bulunamadı.")
    else:
        print(f"POST isteğinde hata: {response.status_code}")

def main():
    username = input("TC: ")
    password = input("Şifre: ")
    aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    obs_url = "https://obs.istanbul.edu.tr"
    obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/DersProgramiYeni"

    session = requests.Session()
    token = get_verification_token(session, aksis_login_url)

    if token and login_to_aksis(session, username, password, aksis_login_url, token):
        if check_aksis_api(session, aksis_api_url):
            print("Aksis sayfasına erişim sağlandı")
            response_first = session.get(obs_url)
            if response_first.status_code == 200:
                print("İlk OBS sayfasına erişim sağlandı")
                
                # OBS giriş sonrası alınan çerezlerle post isteği yap
                post_to_obs_results(session, obs_post_url, obs_url)

            else:
                print(f"İlk OBS sayfasına erişim sağlanamadı: {response_first.status_code}")
        else:
            print("Aksis API erişimi sağlanamadı")
    else:
        print("Aksis giriş başarısız")

if __name__ == "__main__":
    main()
