import requests
import json
import os
import configparser
import sys

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CACHE_FILE = os.path.join(_get_base_dir(), 'cached_schedule.json')

def save_schedule_to_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Cache saved")
    except Exception as e:
        print(f"Error saving cache: {e}")

def load_schedule_from_cache():
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
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
    """Возвращает список IP-адресов из config.ini, который лежит рядом с исполняемым файлом."""
    config = configparser.ConfigParser()
    config_path = os.path.join(_get_base_dir(), 'config.ini')
    if os.path.exists(config_path):
        config.read(config_path)
        try:
            ips_str = config.get('Server', 'ips')
            ips = [ip.strip() for ip in ips_str.split(',') if ip.strip()]
            return ips
        except (configparser.NoSectionError, configparser.NoOptionError):
            return []
    return []

def fetch_schedule(server_ip=None):
    if server_ip is None:
        ips = get_server_ips_from_config()
        # Добавляем fallback в конец списка как запасной вариант
        fallback_ip = '192.168.1.3'
        if fallback_ip not in ips:
            ips.append(fallback_ip)

        if not ips:
            print("No IPs to try")
            return None

        for ip in ips:
            print(f"Trying to connect to {ip}...")
            url = f'http://{ip}:80/api/schedule'
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"OK - got data from {ip}")
                    return data
                else:
                    print(f"Server {ip} returned error {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Connection to {ip} failed: {e}")
            except ValueError:
                print(f"Server {ip} returned non-JSON response")

        print("All servers unreachable")
        return None
    else:
        # 3. Если передан конкретный IP (например, из аргумента)
        url = f'http://{server_ip}:80/api/schedule'
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
        except ValueError:
            print("Server returned non-JSON response")
            return None