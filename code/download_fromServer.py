import requests
import json
import os

def save_schedule_to_cache(data):
    try:
        with open('cached_schedule.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Cache saved")
    except Exception as e:
        print(f"Error saving cache: {e}")

def load_schedule_from_cache():
    try:
        with open('cached_schedule.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            print("Cache loaded")
            return data
    except FileNotFoundError:
        print("Cache file not found")
        return None
    except Exception as e:
        print(f"Error loading cache: {e}")
        return None

def fetch_schedule(server_ip='127.0.0.1'):
    url = f'http://{server_ip}:5000/api/schedule'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("OK - got data from server")
            return data
        else:
            print(f"Server error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return None