#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, time, uuid, ssl, threading, socketserver, http.server, os, random

HOST = "119.13.80.35"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

POOL_SIZE = 10         # 主池子容量
INVENTORY_SIZE = 20    # 备用存货池容量
POOL_FILE = "/sdcard/Download/Operit/suyou_pools.json"

account_pool = []      # 正在使用的主池
inventory_pool = []    # 备用的存货池
base_nodes = []

recent_logs = []
def log(msg):
    txt = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(txt)
    recent_logs.append(txt)
    if len(recent_logs) > 50: recent_logs.pop(0)

def load_pools():
    global account_pool, inventory_pool
    if os.path.exists(POOL_FILE):
        try:
            with open(POOL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                account_pool = data.get("account_pool", [])
                inventory_pool = data.get("inventory_pool", [])
            log(f"[持久化] 成功读取本地记录: 主池 {len(account_pool)} 个, 存货池 {len(inventory_pool)} 个")
        except Exception as e:
            log(f"[持久化] 读取记录失败: {e}")

def save_pools():
    try:
        with open(POOL_FILE, "w", encoding="utf-8") as f:
            json.dump({"account_pool": account_pool, "inventory_pool": inventory_pool}, f)
    except: pass

def get_random_ip():
    return f"{random.randint(11,250)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"
def reg():
    try:
        rip = get_random_ip()
        log(f"[*] [防封] 伪造随机公网IP: {rip} 注册新号...")
        h = {"Host": HOST, "app": "android", "version": "3.3.2", "User-Agent": "okhttp/4.12.0", "X-Forwarded-For": rip, "Client-IP": rip}
        req = urllib.request.Request(f"https://{HOST}/api/v1/passport/auth/loginByDeviceId", data=json.dumps({"device_id": f"android-{uuid.uuid4()}", "invite_token": None}).encode(), headers={**h, "Content-Type": "application/json"}, method='POST')
        auth = json.loads(urllib.request.urlopen(req, context=ctx, timeout=5).read().decode())['data']['auth_data']
        req2 = urllib.request.Request(f"https://{HOST}/api/v1/user/info", headers={**h, "Authorization": auth})
        return {"uuid": json.loads(urllib.request.urlopen(req2, context=ctx, timeout=5).read().decode())['data']['uuid'], "auth": auth}
    except Exception as e:
        log(f"[!] 注册网络超时/异常 ({e})")
        return None

def check_alive(acc):
    try:
        rip = get_random_ip()
        h = {"Host": HOST, "app": "android", "version": "3.3.2", "User-Agent": "okhttp/4.12.0", "Authorization": acc["auth"], "X-Forwarded-For": rip, "Client-IP": rip}
        req = urllib.request.Request(f"https://{HOST}/api/v1/user/getSubscribe", headers=h)
        d = json.loads(urllib.request.urlopen(req, context=ctx, timeout=5).read().decode())['data']
        left_mb = (d.get('transfer_enable', 0) - d.get('u', 0) - d.get('d', 0)) / (1024*1024)
        acc['left_mb'] = f"{left_mb:.2f}"
        return left_mb > 50
    except Exception as e:
        acc['left_mb'] = "网络检测超时"
        return True

def maintain_main_pool():
    log("[*] 启动主池监控线程...")
    while True:
        alive_pool = []
        for acc in account_pool:
            if check_alive(acc): alive_pool.append(acc)
            else: log(f"[-] 真实清除耗尽账号: {acc['uuid'][:8]}...")
        account_pool[:] = alive_pool
        
        while len(account_pool) < POOL_SIZE:
            if len(inventory_pool) > 0:
                acc = inventory_pool.pop(0)
                if check_alive(acc):
                    account_pool.append(acc)
                    log(f"[+] 从存货池秒速提号成功! 主池 {len(account_pool)}/{POOL_SIZE} | UUID: {acc['uuid'][:8]}")
            else:
                log(f"[!] 存货池为空，紧急注册新号补给主池...")
                acc = reg()
                if acc and check_alive(acc):
                    account_pool.append(acc)
        save_pools()
        time.sleep(30)

def maintain_inventory():
    log("[*] 启动存货池后台囤号线程...")
    while True:
        if len(inventory_pool) < INVENTORY_SIZE:
            log(f"[*] 存货池不满 ({len(inventory_pool)}/{INVENTORY_SIZE}), 正在后台空闲时间囤号...")
            acc = reg()
            if acc and check_alive(acc):
                inventory_pool.append(acc)
                log(f"[囤号] 存货池喜加一! 当前进度: {len(inventory_pool)}/{INVENTORY_SIZE} | 初始流量: {acc.get("left_mb", "?")} MB")
                save_pools()
        time.sleep(15)
def parse_vless(url, group_name):
    try:
        url = url.strip()
        if not url.startswith("vless://"): return None
        ps = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(ps.query)
        px = {"name": urllib.parse.unquote(ps.fragment), "type": "vless", "server": ps.hostname, "port": ps.port, "uuid": ps.username, "udp": True, "tls": True, "network": "ws"}
        if "sni" in qs: px["servername"] = qs["sni"][0]
        if qs.get("security", [""])[0] == "reality":
            px["network"] = "tcp"
            px["reality-opts"] = {"public-key": qs.get("pbk", [""])[0]}
            if "fp" in qs: px["client-fingerprint"] = qs["fp"][0]
            if "sni" in qs: px["reality-opts"]["short-id"] = qs.get("sid", [""])[0]
            px["flow"] = "xtls-rprx-vision"
            if "alpn" in qs: px["alpn"] = [qs["alpn"][0]]
        else:
            if "path" in qs: px["ws-opts"] = {"path": qs["path"][0], "headers": {"Host": qs.get("host", [ps.hostname])[0]}}
        return px
    except: return None

def to_y(d, ind=0):
    sp = "  " * ind
    s = ""
    if isinstance(d, list):
        for item in d:
            if isinstance(item, dict): s += sp + "- " + to_y(item, ind+1).lstrip()
            else: s += sp + "- " + str(item) + chr(10)
        return s
    for k, v in d.items():
        if isinstance(v, dict): s += sp + str(k) + ":" + chr(10) + to_y(v, ind+1)
        elif isinstance(v, list) and len(v) == 0: s += sp + str(k) + ": []" + chr(10)
        elif isinstance(v, list): s += sp + str(k) + ":" + chr(10) + to_y(v, ind+1)
        else: s += sp + str(k) + ": " + str(v) + chr(10)
    return s

def gen_yaml():
    y={"mode":"rule","allow-lan":False,"proxies":[],"proxy-groups":[]}
    m=[]
    for n in base_nodes:
        o=n.get("name","node")
        f=[]
        for a in account_pool:
            d=dict(n)
            d["uuid"]=a["uuid"]
            nm=f"{o}-{a['uuid'][:4]}"
            d["name"]=nm
            y["proxies"].append(d)
            f.append(nm)
        y["proxy-groups"].append({"name":o,"type":"fallback","proxies":f,"url":"http://www.gstatic.com/generate_204","interval":300})
        m.append(o)
    y["proxy-groups"].insert(0,{"name":"💡 主节点选择","type":"select","proxies":m})
    y["rules"]=["MATCH, 💡 主节点选择"]
    out=""
    for k,v in y.items():
        if isinstance(v,(list,dict)): out+=str(k)+":"+chr(10)+to_y(v,1)
        else: out+=str(k)+": "+str(v).lower()+chr(10)
    return out

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/sub':
                self.send_response(200)
                self.send_header("Content-type", "text/yaml; charset=utf-8")
                self.end_headers()
                self.wfile.write(gen_yaml().encode("utf-8"))
            elif self.path == '/api/status':
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                pool_data = []
                for a in account_pool: pool_data.append({"uuid": str(a.get("uuid", ""))[:8], "mb": str(a.get("left_mb", "?"))})
                inv_data = []
                for a in inventory_pool: inv_data.append({"uuid": str(a.get("uuid", ""))[:8], "mb": str(a.get("left_mb", "?"))})
                resp = {"pool": pool_data, "inventory": inv_data, "logs": recent_logs}
                import json
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            else:
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                
                h = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>永动机</title>'
                h += '<style>body{font-family:sans-serif;margin:20px;background:#f4f4f4;} .card{background:#fff;padding:15px;margin-bottom:15px;border-radius:8px;} pre{background:#222;color:#0f0;padding:10px;overflow-x:auto;} table{width:100%;border-collapse:collapse;} th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd;} </style></head>'
                h += '<body><h2>🔋 速游永动机控制台</h2>'
                h += '<div class="card"><b>🔗 订阅链接:</b> <a href="/sub">http://127.0.0.1:8080/sub</a></div>'
                h += '<div class="card"><b>🏠 主号池 (<span id="p-cnt">0</span>/10)</b><table><thead><tr><th>UUID</th><th>流量</th></tr></thead><tbody id="p-list"></tbody></table></div>'
                h += '<div class="card"><b>📦 存货池 (<span id="i-cnt">0</span>/20)</b><table><thead><tr><th>UUID</th><th>流量</th></tr></thead><tbody id="i-list"></tbody></table></div>'
                h += '<div class="card"><b>📜 日志</b><pre id="log-list">Loading...</pre></div>'
                h += '<script>'
                h += 'async function update(){'
                h += '    try {'
                h += '        let r = await fetch("/api/status"); let d = await r.json();'
                h += '        document.getElementById("p-cnt").innerText = d.pool.length;'
                h += '        document.getElementById("i-cnt").innerText = d.inventory.length;'
                h += '        let p_html = ""; for(let i=0;i<d.pool.length;i++){ p_html += "<tr><td>" + d.pool[i].uuid + "</td><td><b style=\'color:green\'>" + d.pool[i].mb + "</b></td></tr>"; } document.getElementById("p-list").innerHTML = p_html;'
                h += '        let i_html = ""; for(let i=0;i<d.inventory.length;i++){ i_html += "<tr><td>" + d.inventory[i].uuid + "</td><td><b style=\'color:green\'>" + d.inventory[i].mb + "</b></td></tr>"; } document.getElementById("i-list").innerHTML = i_html;'
                h += '        document.getElementById("log-list").innerText = d.logs.join("\\n");'
                h += '    } catch(e) { document.getElementById("log-list").innerText = "[ERROR] " + e.message; }'
                h += '}'
                h += 'setInterval(update, 2000); update();'
                h += '</script></body></html>'
                
                self.wfile.write(h.encode("utf-8"))
        except: pass
    def log_message(self, format, *args): pass

if __name__ == '__main__':
    path = "/sdcard/Download/Operit/suyou_raw_nodes.txt"
    if not os.path.exists(path):
        log(f"[!] 本地节点文件不存在: {path}"); exit()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            px = parse_vless(line, "Temp")
            if px: base_nodes.append(px)
    log(f"[*] 成功加载 {len(base_nodes)} 个节点模板。")
    load_pools()
    import threading, socketserver
    threading.Thread(target=maintain_main_pool, daemon=True).start()
    threading.Thread(target=maintain_inventory, daemon=True).start()
    LISTEN_PORT = 8080
    log(f"[*] 服务已启动: http://127.0.0.1:{LISTEN_PORT}/sub")
    
    class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    try:
        server = ThreadedServer(('0.0.0.0', LISTEN_PORT), H)
        server.serve_forever()
    except Exception as e:
        log(f"[!] 端口冲突，尝试强制夺取... ({e})")
