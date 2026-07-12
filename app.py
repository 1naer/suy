import os
import json
import yaml
import time
import requests
import random
import threading
import urllib3
import uuid
import http.server
import socketserver
from urllib.parse import urlparse

# 忽略不安全的 SSL 警告（直连 IP 时需要）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= VLESS REALITY 节点集群 (共 19 个) =================
BASE_NODES = [{'name': 'AWS-HK-01', 'server': '16.163.107.170', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-HK-01'}, {'name': 'AWS-JP-02', 'server': '18.183.84.67', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP-02'}, {'name': 'AWS-JP-03', 'server': '35.78.200.186', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP-03'}, {'name': 'AWS-KR-02', 'server': '3.38.129.206', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-KR-02'}, {'name': 'AWS-SG-02', 'server': '18.142.122.25', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-SG-02'}, {'name': 'AWS-SG-03', 'server': '13.229.136.66', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-SG-03'}, {'name': 'AWS-JP-04', 'server': 'jp04.baiduhelp.com', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP-04'}, {'name': 'AWS-SG-05', 'server': '47.129.226.30', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 'aijccz.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-SG-05'}, {'name': 'AWS-JP-05', 'server': 'jp05.baiduhelp.com', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP-05'}, {'name': 'AWS-KR-05', 'server': '43.203.164.241', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-KR-05'}, {'name': 'AWS-JP2-01', 'server': '54.249.55.221', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP2-01'}, {'name': 'AWS-JP2-02', 'server': '35.78.103.60', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP2-02'}, {'name': 'AWS-JP2-03', 'server': '54.178.64.147', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP2-03'}, {'name': 'AWS-SG2-01', 'server': '18.141.170.11', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-SG2-01'}, {'name': 'AWS-SG2-02', 'server': '13.212.184.33', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-SG2-02'}, {'name': 'AWS-SG2-03', 'server': 'aws-sg3.sysydu.top', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-SG2-03'}, {'name': 'AWS-JP03-备用', 'server': '52.198.137.136', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-JP03-%E5%A4%87%E7%94%A8'}, {'name': 'AWS-HK01-备用', 'server': '18.166.225.151', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-HK01-%E5%A4%87%E7%94%A8'}, {'name': 'AWS-HK02-备用', 'server': '16.163.106.51', 'port': 443, 'flow': 'xtls-rprx-vision', 'server_name': 's0.awsstatic.com', 'public_key': 'W_6i8cZ-Bx8ED2sAQWFjzrlmCBIBHiMmcFyjqLPiFz8', 'short_id': '6a69fd63#AWS-HK02-%E5%A4%87%E7%94%A8'}]

POOL_FILE = "suyou_pools.json"
pool_lock = threading.RLock()
account_pool = []

HTML_TPL = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>速游 全球节点永动机</title>
    <style>
        body {{ font-family: Arial; padding: 20px; background: #f0f2f5; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .pool-count {{ font-size: 24px; color: #ff4757; font-weight: bold; }}
        .link-box {{ background: #f1f2f6; padding: 10px; border-radius: 4px; word-break: break-all; margin-top: 10px; font-family: monospace; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #dfe4ea; padding: 8px; text-align: left; }}
        th {{ background: #f1f2f6; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🔥 自动存货池状态</h2>
        <p>当前可用新号数量: <span class="pool-count">{count}</span> / 10</p>
        <p>点击下方链接导入至支持 Meta 内核的客户端 (FlClash/Clash Verge Rev) 测速！</p>
    </div>
    {content}
    <div class="card">
        <h3>📦 存货池明细</h3>
        <table>
            <tr><th>UID</th><th>UUID</th><th>状态</th></tr>
            {table_rows}
        </table>
    </div>
</body>
</html>'''

def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)

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
    return str(uuid.uuid4())

# 核心注册与抓取逻辑：100% 还原抓包指纹，采用直连 IP 与 JWT 授权
def do_register():
    device_id = generate_device_id()
    
    # 完美伪装原生 App 的 Headers
    headers = {
        "App": "android",
        "Version": "3.3.2",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/4.12.0"
    }

    # 第一步：请求 loginByDeviceId 获取 JWT auth_data
    url_login = "https://139.199.9.50/api/v1/passport/auth/loginByDeviceId"
    login_data = {
        "device_id": device_id,
        "is_simulator": 0,
        "system_version": "14",
        "device_model": "2211133C"
    }

    try:
        resp_login = requests.post(url_login, headers=headers, data=login_data, verify=False, timeout=15)
        login_json = resp_login.json()
        
        if login_json.get("data") and login_json["data"].get("auth_data"):
            auth_data = login_json["data"]["auth_data"]
            uid = str(login_json["data"].get("id", device_id[:8]))
            
            # 第二步：携带 JWT 凭证去获取订阅 UUID（官方会自动赠送流量）
            url_sub = "https://139.199.9.50/api/v1/user/getSubscribe"
            headers_sub = headers.copy()
            headers_sub["Authorization"] = auth_data
            
            resp_sub = requests.get(url_sub, headers=headers_sub, verify=False, timeout=15)
            sub_json = resp_sub.json()
            
            uuid_str = ""
            if sub_json.get("data"):
                # 处理返回可能是列表或字典的情况
                data_obj = sub_json["data"]
                if isinstance(data_obj, list) and len(data_obj) > 0:
                    uuid_str = data_obj[0].get("uuid", "")
                elif isinstance(data_obj, dict):
                    uuid_str = data_obj.get("uuid", "")

            if uuid_str:
                log(f"[+] 注册成功！UID: {uid}, 获得 UUID: {uuid_str[:8]}...")
                return {"uid": uid, "uuid": uuid_str, "auth_data": auth_data}
            else:
                log("[-] 注册成功但未能获取到 UUID")
        else:
            log(f"[-] 注册失败，接口返回: {login_json}")
            
    except Exception as e:
        log(f"[-] 请求异常: {e}")
    return None

# ================= 模拟真人防风控后台任务 =================
def background_task():
    log("[*] 后台打工兔（自动注册机）已启动！")
    while True:
        with pool_lock:
            pool_size = len(account_pool)
        
        if pool_size >= 10:
            # 满载时深度休眠 (40~80秒)，消除机器特征
            sleep_time = random.randint(40, 80)
            time.sleep(sleep_time)
            continue
        
        # 注册前犹豫，模拟真人打开App、加载界面的耗时 (10~25秒)
        time.sleep(random.randint(10, 25))
        
        acc = do_register()
        if acc:
            with pool_lock:
                account_pool.append(acc)
            save_pool()
            # 注册成功后切出去看番摸鱼 (20~50秒)
            time.sleep(random.randint(20, 50))
        else:
            # 失败了也休息一下，防止被官方拉黑 IP (15~30秒)
            time.sleep(random.randint(15, 30))

# ================= 订阅生成与网页服务 =================
def generate_clash_yaml(account):
    uid = account['uid']
    uuid_str = account['uuid']
    
    proxies = []
    proxy_names = []
    
    for node in BASE_NODES:
        node_name = node['name']
        proxy_names.append(node_name)
        proxies.append({
            "name": node_name,
            "type": "vless",
            "server": node['server'],
            "port": node['port'],
            "uuid": uuid_str,
            "udp": True,
            "tls": True,
            "network": "tcp",
            "servername": node['server_name'],
            "client-fingerprint": "chrome",
            "flow": node['flow'],
            "reality-opts": {
                "public-key": node['public_key'],
                "short-id": node['short_id'].split('#')[0]
            }
        })
        
    config = {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "Proxy",
                "type": "select",
                "proxies": ["AUTO"] + proxy_names
            },
            {
                "name": "AUTO",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": proxy_names
            }
        ],
        "rules": [
            "MATCH,Proxy"
        ]
    }
    return yaml.dump(config, allow_unicode=True, sort_keys=False)

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            with pool_lock:
                count = len(account_pool)
                if count > 0:
                    # 拿出一个号展示
                    acc = account_pool.pop(0)
                    save_pool()
                    host = self.headers.get('Host', 'localhost:8080')
                    # 动态生成当前服务的订阅链接
                    sub_link = f"https://{host}/sub"
                    
                    content_html = f'''
                    <div class="card">
                        <h3 style="color:#2ed573;">🎉 成功提取新号！</h3>
                        <p><b>UID:</b> {acc['uid']}</p>
                        <p><b>一键订阅链接（内置 19 个节点哦！）:</b></p>
                        <div class="link-box">{sub_link}</div>
                    </div>
                    '''
                    # 为了测试不断流，展示完暂时放回队尾（如果需要一次性提取可以删掉这行）
                    account_pool.append(acc)
                else:
                    content_html = '''
                    <div class="card">
                        <h3 style="color:#ffa502;">⏳ 存货池为空，正在全力打工注册中...</h3>
                        <p>请等待一两分钟后刷新页面哦！</p>
                    </div>
                    '''
                    
                rows = ""
                for a in account_pool:
                    rows += f"<tr><td>{a['uid']}</td><td>{a['uuid'][:8]}...</td><td>就绪</td></tr>"
                    
            # 渲染 HTML 并转义写入
            html = HTML_TPL.format(count=count, content=content_html, table_rows=rows)
            self.wfile.write(html.encode("utf-8"))
            
        elif parsed.path.startswith("/sub"):
            target_acc = None
            with pool_lock:
                if account_pool:
                    target_acc = account_pool[0] # 直接拿池子里的第一个
                    
            # 万一 Render 刚睡醒池子是空的，立刻现场注册一个发给客户端！
            if not target_acc:
                log("[*] 收到订阅请求，但池子为空，现场紧急抓取新号...")
                target_acc = do_register()
                if target_acc:
                    with pool_lock:
                        account_pool.append(target_acc)
                        
            if target_acc:
                self.send_response(200)
                self.send_header("Content-type", "text/yaml; charset=utf-8")
                self.end_headers()
                yaml_data = generate_clash_yaml(target_acc)
                self.wfile.write(yaml_data.encode("utf-8"))
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Server busy or official API failed, please try again")
        else:
            self.send_response(404)
            self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    load_pool()
    t = threading.Thread(target=background_task, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 8080))
    # 必须明确绑定到 0.0.0.0，否则 Render 会报 502 Bad Gateway
    server = ThreadedHTTPServer(("0.0.0.0", port), ProxyHandler)
    log(f"[*] 究极永动机 Web 服务已启动，监听 0.0.0.0:{port}")
    server.serve_forever()
