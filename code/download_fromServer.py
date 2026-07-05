import requests
import json

def fetch_schedule(server_ip='127.0.0.1'):
    url = f'http://{server_ip}:5000/api/schedule'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()  # преобразует JSON в словарь Python
            print("OK - got data")
            return data
        else:
            print(f"Server error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return None