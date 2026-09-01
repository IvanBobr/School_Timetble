import requests
import json
import os
import configparser
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

def get_server_ips_from_config():
    """Возвращает список IP-адресов из config.ini"""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    if os.path.exists(config_path):
        config.read(config_path)
        try:
            ips_str = config.get('Server', 'ips')
            # Разбиваем по запятой, удаляем пробелы, фильтруем пустые
            ips = [ip.strip() for ip in ips_str.split(',') if ip.strip()]
            return ips
        except (configparser.NoSectionError, configparser.NoOptionError):
            return []
    return []

def fetch_schedule(server_ip=None):
    if server_ip is None:
        # 1. Пробуем конфиг
        ips = get_server_ips_from_config()
        if ips:
            for ip in ips:
                print(f"Trying to connect to {ip}...")
                url = f'http://{ip}:5000/api/schedule'
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        print(f"OK - got data from {ip}")
                        return data
                    else:
                        print(f"Server {ip} returned error {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"Connection to {ip} failed: {e}")
            # Если ни один не подошёл
            print("All servers unreachable")
            return None
        else:
            # 2. Если конфига нет — fallback на один IP
            fallback_ip = '192.168.1.3'
            print(f"No config, using fallback {fallback_ip}")
            return fetch_schedule(fallback_ip)
    else:
        # 3. Если передан конкретный IP (например, из аргумента)
        url = f'http://{server_ip}:5000/api/schedule'
        try:
            response = requests.get(url, timeout=10)
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
