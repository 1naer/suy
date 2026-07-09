import os
import json
import base64
import yaml
import time
import requests
import string
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------- 自适应环境配置 ----------------
if os.path.exists("/sdcard"):
    # 手机环境
    BASE_DIR = "/sdcard/Download/Operit"
else:
    # 云端环境
    BASE_DIR = os.getcwd()

# 根据环境自动适配路径
NODE_FILE = os.path.join(BASE_DIR, "suyou_raw_nodes.txt")
POOL_FILE = os.path.join(BASE_DIR, "suyou_pools.json")

# 自动适配云端端口（如无指定则用 8080）
PORT = int(os.environ.get("PORT", 8080))

# =============== 核心逻辑配置 ===============
# ... (其余逻辑与你手机上的 app.py 相同)

def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}")

# ----------------- 代理节点加载 -----------------
def load_nodes():
    if not os.path.exists(NODE_FILE):
        log(f"[!] 本地节点文件不存在: {NODE_FILE}")
        return []
    
    with open(NODE_FILE, "r", encoding="utf-8") as f:
        content = f.read().strip()
        
    try:
        decoded = base64.b64decode(content).decode("utf-8")
        links = [line.strip() for line in decoded.split("\n") if line.strip() and line.startswith("vmess://")]
        
        nodes = []
        for link in links:
            try:
                b64_data = link[8:]
                missing_padding = len(b64_data) % 4
                if missing_padding:
                    b64_data += '=' * (4 - missing_padding)
                node_json = json.loads(base64.b64decode(b64_data).decode("utf-8"))
                nodes.append(node_json)
            except Exception:
                continue
                
        log(f"[*] 成功加载 {len(nodes)} 个节点模板。")
        return nodes
    except Exception as e:
        log(f"[!] 解析节点失败: {e}")
        return []

NODE_TEMPLATES = load_nodes()

# ----------------- 账号池持久化 -----------------
pool_lock = threading.Lock()
account_pool = []

def load_pool():
    global account_pool
    if os.path.exists(POOL_FILE):
        try:
            with open(POOL_FILE, "r", encoding="utf-8") as f:
                account_pool = json.load(f)
            log(f"[*] 成功加载本地存货，当前库存: {len(account_pool)} 个。")
        except Exception as e:
            log(f"[!] 存货加载失败: {e}")
            account_pool = []
    else:
        log("[*] 未找到本地存货，初始化空号池。")

def save_pool():
    try:
        with pool_lock:
            with open(POOL_FILE, "w", encoding="utf-8") as f:
                json.dump(account_pool, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"[!] 存货保存失败: {e}")

load_pool()

# ----------------- 注册逻辑核心 -----------------
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
            
            # 使用获取到的 token 再请求一次节点配置接口，获取真实的 port 和 uuid
            config_url = "https://app.suyouapp.app/api/v1/user/server/fetch"
            config_headers = {
                "Authorization": token,
                "User-Agent": headers["User-Agent"]
            }
            config_resp = requests.get(config_url, headers=config_headers, timeout=10)
            config_data = config_resp.json()
            
            uuid_str = ""
            port_num = 0
            
            if config_data.get("data"):
                for server in config_data["data"]:
                    if server.get("uuid") and server.get("port"):
                        uuid_str = server["uuid"]
                        port_num = int(server["port"])
                        break
            
            if uuid_str and port_num:
                return {
                    "uid": uid,
                    "token": token,
                    "uuid": uuid_str,
                    "port": port_num,
                    "timestamp": int(time.time())
                }
    except Exception:
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
                log(f"[+] 注册成功！UID: {acc['uid']} | 当前库存: {len(account_pool)}")
            else:
                log("[-] 注册失败，3秒后重试。")
                time.sleep(3)
        else:
            time.sleep(5)

# ----------------- 订阅生成逻辑 -----------------
def generate_clash_yaml(account):
    if not NODE_TEMPLATES:
        return "没有可用节点模板"

    proxies = []
    proxy_names = []
    
    uid = account['uid']
    uuid = account['uuid']
    port = account['port']
    
    for idx, tpl in enumerate(NODE_TEMPLATES):
        name = f"Suyou-{uid}-{idx+1}"
        
        proxy = {
            "name": name,
            "type": "vmess",
            "server": tpl.get("add", "1.1.1.1"),
            "port": port,
            "uuid": uuid,
            "alterId": int(tpl.get("aid", 0)),
            "cipher": "auto",
            "tls": False,
            "network": tpl.get("net", "tcp")
        }
        
        if proxy["network"] == "ws":
            proxy["ws-opts"] = {
                "path": tpl.get("path", "/"),
                "headers": {
                    "Host": tpl.get("host", tpl.get("add", ""))
                }
            }
            
        proxies.append(proxy)
        proxy_names.append(name)
        
    config = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "🚀 自动选择",
                "type": "url-test",
                "proxies": proxy_names,
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300
            },
            {
                "name": "🌐 代理节点",
                "type": "select",
                "proxies": ["🚀 自动选择"] + proxy_names
            }
        ],
        "rules": [
            "MATCH,🌐 代理节点"
        ]
    }
    
    return yaml.dump(config, allow_unicode=True, sort_keys=False)

# ----------------- Web UI -----------------
HTML_TPL = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>速游无限提号机</title>
    <style>
        body { font-family: -apple-system, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; background: #f0f2f5; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }
        .stat { font-size: 48px; font-weight: bold; color: #1890ff; margin: 10px 0; }
        .btn { display: inline-block; padding: 12px 24px; background: #1890ff; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; transition: 0.3s; cursor: pointer; border: none; font-size: 16px;}
        .btn:hover { background: #40a9ff; }
        .btn:active { transform: scale(0.98); }
        .footer { margin-top: 30px; color: #888; font-size: 12px; text-align: center; }
        .success-msg { display: none; margin-top: 15px; color: #52c41a; font-weight: bold; padding: 10px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔥 自动存货池</h2>
        <p>当前可用独立账号（自动补货）</p>
        <div class="stat" id="poolSize">{{pool_size}}</div>
        <p>点击下方按钮，秒提一条全新订阅配置</p>
        
        <button class="btn" onclick="copySub()">⚡️ 一键复制 Clash 订阅 ⚡️</button>
        <div id="msg" class="success-msg">✅ 复制成功！去 Clash 里导入吧</div>
    </div>
    
    <div class="footer">
        * 系统在后台 24 小时不断注册新号补货<br>
        * 提取时自动从池中消耗一个账号
    </div>

    <script>
        function copySub() {
            var subUrl = window.location.origin + "/sub";
            var tempInput = document.createElement("input");
            tempInput.value = subUrl;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand("copy");
            document.body.removeChild(tempInput);
            
            var msg = document.getElementById("msg");
            msg.style.display = "block";
            setTimeout(function() {
                msg.style.display = "none";
            }, 3000);
            
            // 提号后自动刷新页面更新数字
            setTimeout(function() {
                window.location.reload();
            }, 500);
        }
        
        // 自动刷新库存显示
        setInterval(function() {
            fetch('/api/pool_size')
                .then(r => r.json())
                .then(d => {
                    document.getElementById('poolSize').innerText = d.size;
                });
        }, 5000);
    </script>
</body>
</html>
"""

# ----------------- HTTP 服务器 -----------------
class ReqHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with pool_lock:
                html = HTML_TPL.replace("{{pool_size}}", str(len(account_pool)))
            self.wfile.write(html.encode("utf-8"))
            
        elif parsed.path == "/api/pool_size":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            with pool_lock:
                self.wfile.write(json.dumps({"size": len(account_pool)}).encode("utf-8"))
                
        elif parsed.path == "/sub":
            acc = None
            with pool_lock:
                if account_pool:
                    acc = account_pool.pop(0)
            
            if acc:
                save_pool()
                log(f"[+] 从存货池秒速提号成功！UID: {acc['uid']} | 剩余库存: {len(account_pool)}")
                yaml_data = generate_clash_yaml(acc)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/yaml; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="suyou_auto.yaml"')
                self.end_headers()
                self.wfile.write(yaml_data.encode("utf-8"))
            else:
                self.send_response(503)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write("存货池已空，正在拼命注册补货中，请稍后刷新重试...".encode("utf-8"))
                
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # 屏蔽 HTTP 默认日志

# ----------------- 启动入口 -----------------
if __name__ == "__main__":
    t = threading.Thread(target=worker_thread, daemon=True)
    t.start()
    
    server = HTTPServer(('0.0.0.0', PORT), ReqHandler)
    log(f"[*] 服务已启动，监听端口: {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
