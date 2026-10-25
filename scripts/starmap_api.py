#!/usr/bin/env python3
"""StarMap API 小工具（零依赖，只标准库）。

用法:
  python3 starmap_api.py login  --base http://10.211.55.43:8080 --password XXXX
  python3 starmap_api.py task   --base ... --targets 192.168.1.0/24 --name 家庭网络
  python3 starmap_api.py ports  --base ... --targets 192.168.1.0/24 --preset standard
  python3 starmap_api.py star   --base ... --company 我的家庭网络 --out graph.json
  python3 starmap_api.py shot-ui --base ... --password XXXX --out ui.png
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.request, http.cookiejar

def client(base, cookiefile="/tmp/sm.jar"):
    cj = http.cookiejar.MozillaCookieJar(cookiefile)
    if os.path.exists(cookiefile):
        try: cj.load(ignore_discard=True, ignore_expires=True)
        except Exception: pass
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return op, cj

def call(op, base, path, method="GET", body=None, timeout=120):
    req = urllib.request.Request(base.rstrip("/") + path, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    with op.open(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "ignore")
    try: return json.loads(raw)
    except Exception: return raw

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["login","task","ports","star","shot-ui"])
    ap.add_argument("--base", required=True)
    ap.add_argument("--password", default="")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--cookiefile", default="/tmp/sm.jar")
    ap.add_argument("--targets", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--preset", default="standard")
    ap.add_argument("--company", default="")
    ap.add_argument("--graph-id", type=int, default=0)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    op, cj = client(a.base, a.cookiefile)

    if a.cmd == "login":
        print(call(op, a.base, "/api/auth/login", "POST", {"username": a.user, "password": a.password}))
        cj.save(ignore_discard=True, ignore_expires=True)
    elif a.cmd == "task":
        print(json.dumps(call(op, a.base, "/api/tasks/batch", "POST", {
            "name": a.name or "资产测绘", "inputs": a.targets, "enable_gogo": True,
            "auto_port_scan": True, "query_mode": "auto"}), ensure_ascii=False, indent=2))
    elif a.cmd == "ports":
        print(json.dumps(call(op, a.base, "/api/portscan", "POST", {
            "name": a.name or "portscan", "targets": a.targets, "preset": a.preset}),
            ensure_ascii=False, indent=2))
    elif a.cmd == "star":
        graphs = call(op, a.base, "/api/starmaps")
        gid = a.graph_id or next((g["ID"] for g in graphs if g.get("company_name") == a.company), 0)
        if not gid:
            gid = call(op, a.base, "/api/starmaps", "POST", {"company_name": a.company, "project_id": 0})["ID"]
        call(op, a.base, f"/api/starmaps/{gid}/rebuild", "POST")
        data = call(op, a.base, f"/api/starmaps/{gid}/data")
        out = a.out or "graph.json"
        open(out, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"graph #{gid} -> {out} (nodes={len(data.get('nodes',[]))}, edges={len(data.get('edges',[]))})")
    elif a.cmd == "shot-ui":
        shot_ui(a.base, a.user, a.password, a.out or "starmap-ui.png")

def shot_ui(base, user, password, out):
    """用 CDP 驱动 headless Chrome：登录 -> 打开星图页 -> 截图（需软件 WebGL）。"""
    import websocket  # pip install websocket-client
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    prof = "/tmp/chrome-prof"
    subprocess.run([chrome, "--headless=new", "--no-sandbox", "--remote-debugging-port=9227",
                    "--remote-allow-origins=*", "--user-data-dir=" + prof, "--no-first-run",
                    "--window-size=1600,1000", "--hide-scrollbars", "--use-gl=angle",
                    "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "about:blank"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tabs = None
    for _ in range(30):
        try:
            tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9227/json", timeout=2).read()); break
        except Exception: time.sleep(1)
    page = [t for t in tabs if t.get("type") == "page"][0]
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30, max_size=None)
    i = [0]
    def send(m, **p):
        i[0] += 1; mid = i[0]
        ws.send(json.dumps({"id": mid, "method": m, "params": p}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == mid: return msg
    send("Page.enable"); send("Runtime.enable")
    send("Page.navigate", url=base.rstrip("/") + "/login"); time.sleep(5)
    send("Runtime.evaluate", expression=(
        "fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},"
        f"body:JSON.stringify({{username:'{user}',password:'{password}'}})}}).then(r=>r.text())"),
        awaitPromise=True)
    send("Page.navigate", url=base.rstrip("/") + "/assets/starmap"); time.sleep(14)
    for _ in range(8):
        send("Input.dispatchMouseEvent", type="mouseWheel", x=900, y=500, deltaX=0, deltaY=-240)
        time.sleep(0.4)
    shot = send("Page.captureScreenshot", format="png")
    open(out, "wb").write(base64.b64decode(shot["result"]["data"]))
    print("saved", out)

if __name__ == "__main__":
    main()
