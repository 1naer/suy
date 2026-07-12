
import os
import json
import yaml
import time
import requests
import string
import random
import threading
import http.server
import socketserver
from urllib.parse import urlparse

# ================= VLESS REALITY 节点硬编码 =================
# 官方最新抓包节点，直接写死，彻底抛弃 txt 文件
BASE_NODE = {
    "server": "18.183.84.67",
    "port": 443,
    "type": "vless",
    "flow": "xtls-rprx-vision",
    "server_name": "s0.awsstatic.com",
    "public_key": "W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8",
    "short_id": "6a69fd63"
}

POOL_FILE = "suyou_pools.json"
pool_lock = threading.Lock()
account_pool = []

def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}")

def load_pool():
    global account_pool
    if os.path.exists(POOL_FILE):
        try:
            with open(POOL_FILE, "r", encoding="utf-8") as f:
                account_pool = json.load(f)
            log(f"[*] 成功加载本地存货，当前库存: {len(account_pool)} 个。")
        except:
            account_pool = []

def save_pool():
    try:
        with pool_lock:
            with open(POOL_FILE, "w", encoding="utf-8") as f:
                json.dump(account_pool, f, ensure_ascii=False, indent=2)
    except:
        pass

def generate_device_id():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(16))

def do_register():
    device_id = generate_device_id()
    url = "https://app.suyouapp.app/api/v1/passport/auth/registerByDevice"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12; Pixel 6 Pro Build/SQ3A.220705.004)"
    }
    data = {
        "device_id": device_id,
        "device_type": "android",
        "brand": "Google",
        "model": "Pixel 6 Pro",
        "os_version": "12",
        "app_version": "2.2.0"
    }

    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        resp_json = response.json()
        if resp_json.get("data") and resp_json["data"].get("token"):
            auth_data = resp_json["data"]
            token = auth_data["token"]
            uid = str(auth_data.get("id", ""))
            
            config_url = "https://app.suyouapp.app/api/v1/user/server/fetch"
            config_headers = {"Authorization": token, "User-Agent": headers["User-Agent"]}
            config_resp = requests.get(config_url, headers=config_headers, timeout=10)
            config_data = config_resp.json()
            
            uuid_str = ""
            if config_data.get("data"):
                for server in config_data["data"]:
                    if server.get("uuid"):
                        uuid_str = server["uuid"]
                        break
            
            if uuid_str:
                return {"uid": uid, "token": token, "uuid": uuid_str, "timestamp": int(time.time())}
    except:
        pass
    return None

def worker_thread():
    while True:
        with pool_lock:
            pool_size = len(account_pool)
        if pool_size < 10:
            log(f"[*] 库存不足 ({pool_size}/10)，开始自动注册...")
            acc = do_register()
            if acc:
                with pool_lock:
                    account_pool.append(acc)
                save_pool()
                log(f"[+] 注册成功！UID: {acc['uid']}")
            else:
                time.sleep(3)
        else:
            time.sleep(5)

def generate_clash_yaml(account):
    uid = account['uid']
    uuid = account['uuid']
    name = f"Suyou-VLESS-{uid}"
    
    proxy = {
        "name": name,
        "type": "vless",
        "server": BASE_NODE["server"],
        "port": BASE_NODE["port"],
        "uuid": uuid,
        "network": "tcp",
        "tls": True,
        "udp": True,
        "flow": BASE_NODE["flow"],
        "client-fingerprint": "chrome",
        "servername": BASE_NODE["server_name"],
        "reality-opts": {
            "public-key": BASE_NODE["public_key"],
            "short-id": BASE_NODE["short_id"]
        }
    }
    
    config = {
        "proxies": [proxy],
        "proxy-groups": [
            {"name": "🚀 自动选择", "type": "url-test", "proxies": [name], "url": "http://www.gstatic.com/generate_204", "interval": 300},
            {"name": "🌐 代理节点", "type": "select", "proxies": ["🚀 自动选择", name]}
        ],
        "rules": ["MATCH,🌐 代理节点"]
    }
    return yaml.dump(config, allow_unicode=True, sort_keys=False)

class ReqHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with pool_lock:
                pool_size = len(account_pool)
            html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>速游永动机</title></head>
            <body style="font-family:sans-serif;padding:20px;text-align:center;">
            <h2>🔥 自动存货池: {pool_size}</h2>
            <div style="margin:20px;padding:15px;background:#f0f2f5;border-radius:8px;">
            <b>🔗 订阅链接:</b> <span id="auto-link" style="color:#1890ff;font-weight:bold;">获取中...</span>
            <script>document.getElementById("auto-link").innerHTML = `<a href="${window.location.origin}/sub">${window.location.origin}/sub</a>`;</script>
            </div></body></html>'''
            self.wfile.write(html.encode("utf-8"))
        elif parsed.path == "/sub":
            acc = None
            with pool_lock:
                if account_pool:
                    acc = account_pool.pop(0)
            if acc:
                save_pool()
                yaml_data = generate_clash_yaml(acc)
                self.send_response(200)
                self.send_header('Content-type', 'text/yaml; charset=utf-8')
                self.end_headers()
                self.wfile.write(yaml_data.encode("utf-8"))
            else:
                self.send_response(503)
                self.end_headers()
                self.wfile.write("Empty Pool".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    load_pool()
    threading.Thread(target=worker_thread, daemon=True).start()
    PORT = int(os.environ.get("PORT", 7860))
    server = ThreadedServer(('0.0.0.0', PORT), ReqHandler)
    log(f"[*] 服务已启动，监听端口: {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
