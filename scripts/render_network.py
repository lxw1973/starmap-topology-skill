#!/usr/bin/env python3
"""多网段分层网络拓扑渲染器：JSON -> 自包含 HTML(SVG) -> 可截图成 PNG。

数据格式:
{
  "title": "单位网络拓扑",
  "subtitle": "2026-10-26 · 只读采集",
  "core": {"ip":"192.168.16.1","role":"主路由 TP-Link TL-WDR5620","ports":["80/http","1900/upnp"]},
  "segments": [
    {"cidr":"192.168.1.0/24",
     "gateway":{"ip":"192.168.1.1","role":"网段网关","ports":["53/dns","80/http","443/https"]},
     "hosts":[{"ip":"192.168.1.21","name":"fh18755-2","role":"Windows 7 + MSSQL",
               "ports":["445/smb","1433/mssql"],"kind":"server","tags":["telnet","vnc"]}]}
  ]
}
kind: router | server | pc | printer | device | mac
"""
import json, sys, html

COLORS = {
    "router":  ("#f59e0b", "#fbbf24"),
    "server":  ("#a78bfa", "#c4b5fd"),
    "pc":      ("#38bdf8", "#7dd3fc"),
    "printer": ("#34d399", "#6ee7b7"),
    "device":  ("#22d3ee", "#67e8f9"),
    "mac":     ("#94a3b8", "#cbd5e1"),
}
KIND_LABEL = {"router":"路由","server":"服务器","pc":"终端","printer":"打印","device":"设备","mac":"本机"}

def esc(s): return html.escape(str(s))

def host_card(x, y, w, h, host):
    kind = host.get("kind", "pc")
    border, light = COLORS.get(kind, COLORS["pc"])
    ip = host.get("ip", ""); name = host.get("name", ""); role = host.get("role", "")
    ports = host.get("ports", []); tags = host.get("tags", [])
    sub = f'{name} · {role}' if name else role
    p = []
    p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#0b1220" stroke="{border}" stroke-opacity="0.75" stroke-width="1.2"/>')
    p.append(f'<rect x="{x}" y="{y}" width="5" height="{h}" rx="3" fill="{border}"/>')
    p.append(f'<text x="{x+16}" y="{y+24}" font-size="14" font-weight="600" fill="#e2e8f0">{esc(ip)}</text>')
    p.append(f'<text x="{x+16}" y="{y+44}" font-size="11" fill="#8fa3bf">{esc(sub[:30])}</text>')
    for i, pt in enumerate(ports[:4]):
        p.append(f'<text x="{x+w-12}" y="{y+20+i*14}" font-size="10.5" fill="{light}" text-anchor="end" opacity="0.92">{esc(pt)}</text>')
    tx = x + 16
    for t in tags[:3]:
        tw = 11 + len(t)*7
        p.append(f'<rect x="{tx}" y="{y+h-22}" width="{tw}" height="15" rx="7" fill="#7f1d1d" stroke="#ef4444" stroke-width="0.8"/>')
        p.append(f'<text x="{tx+tw/2}" y="{y+h-11}" font-size="9.5" fill="#fecaca" text-anchor="middle">{esc(t)}</text>')
        tx += tw + 6
    p.append(f'<text x="{x+w-12}" y="{y+h-11}" font-size="9.5" fill="{border}" text-anchor="end" opacity="0.85">{KIND_LABEL.get(kind,kind)}</text>')
    return "".join(p)

def main():
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    title = data.get("title", "网络拓扑"); sub = data.get("subtitle", "")
    core = data.get("core", {}); segs = data.get("segments", [])

    LEFT_W = 300           # 左侧核心区宽
    PANEL_X = LEFT_W + 60
    PANEL_W = 1240
    CARD_H = 74; CARD_GAP = 10; COLS = 4
    CARD_W = (PANEL_W - 40 - (COLS-1)*CARD_GAP) / COLS
    HEADER_H = 118
    PANEL_HDR = 96

    # 计算每个面板高度
    panels = []
    y = HEADER_H
    for s in segs:
        n = max(1, len(s.get("hosts", [])))
        rows = (n + COLS - 1) // COLS
        h = PANEL_HDR + rows*(CARD_H+CARD_GAP) + 14
        panels.append((s, y, h)); y += h + 22
    H = y + 40
    W = PANEL_X + PANEL_W + 40

    p = [f'<rect width="{W}" height="{H}" fill="#020617"/>',
         f'<text x="40" y="58" font-size="26" font-weight="700" fill="#e2e8f0">{esc(title)}</text>',
         f'<text x="40" y="84" font-size="13" fill="#64748b">{esc(sub)}</text>']

    # 左侧：互联网 -> 核心
    cx, cy, cw, chh = 40, 250, 220, 120
    p.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{chh}" rx="12" fill="#0b1220" stroke="#475569" stroke-width="1.2"/>')
    p.append(f'<text x="{cx+16}" y="{cy+28}" font-size="14" font-weight="600" fill="#cbd5e1">互联网 / 上级网络</text>')
    p.append(f'<text x="{cx+16}" y="{cy+48}" font-size="11" fill="#64748b">WAN 侧</text>')
    core_x, core_y, core_w, core_h = 40, 250+chh+40, 220, 120
    p.append(f'<rect x="{core_x}" y="{core_y}" width="{core_w}" height="{core_h}" rx="12" fill="#0b1220" stroke="#f59e0b" stroke-width="1.6"/>')
    p.append(f'<rect x="{core_x}" y="{core_y}" width="5" height="{core_h}" rx="3" fill="#f59e0b"/>')
    p.append(f'<text x="{core_x+16}" y="{core_y+26}" font-size="14" font-weight="600" fill="#e2e8f0">{esc(core.get("ip",""))}</text>')
    p.append(f'<text x="{core_x+16}" y="{core_y+46}" font-size="11" fill="#94a3b8">{esc(core.get("role","核心路由"))}</text>')
    for i, pt in enumerate(core.get("ports", [])[:3]):
        p.append(f'<text x="{core_x+16}" y="{core_y+66+i*14}" font-size="10.5" fill="#fbbf24">{esc(pt)}</text>')
    p.append(f'<path d="M {cx+cw/2} {cy+chh} L {cx+cw/2} {core_y}" stroke="#334155" stroke-width="1.5"/>')

    # 主干线
    trunk_x = core_x + core_w + 24
    p.append(f'<path d="M {core_x+core_w} {core_y+core_h/2} L {trunk_x} {core_y+core_h/2}" stroke="#1e40af" stroke-width="2"/>')

    for s, py, ph in panels:
        gw = s.get("gateway", {})
        # 面板
        p.append(f'<rect x="{PANEL_X}" y="{py}" width="{PANEL_W}" height="{ph}" rx="14" fill="#060d1a" stroke="#1e3a5f" stroke-width="1"/>')
        p.append(f'<text x="{PANEL_X+18}" y="{py+24}" font-size="13" font-weight="600" fill="#7dd3fc">{esc(s.get("cidr",""))}</text>')
        p.append(f'<text x="{PANEL_X+150}" y="{py+24}" font-size="11" fill="#64748b">{esc(s.get("note",""))}</text>')
        # 网关条
        gx, gy, gw_w, gw_h = PANEL_X+18, py+34, 420, 40
        p.append(f'<rect x="{gx}" y="{gy}" width="{gw_w}" height="{gw_h}" rx="8" fill="#0b1220" stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="4 3"/>')
        p.append(f'<text x="{gx+12}" y="{gy+17}" font-size="12" font-weight="600" fill="#fbbf24">{esc(gw.get("ip",""))}</text>')
        p.append(f'<text x="{gx+12}" y="{gy+32}" font-size="10.5" fill="#94a3b8">{esc(gw.get("role",""))}  {esc("  ".join(gw.get("ports",[])))}</text>')
        # 主干连接
        ymid = py + PANEL_HDR/2
        p.append(f'<path d="M {trunk_x} {core_y+core_h/2} L {trunk_x} {ymid} L {PANEL_X} {ymid}" fill="none" stroke="#1e40af" stroke-width="1.6"/>')
        # 主机网格
        hosts = s.get("hosts", [])
        for i, h in enumerate(hosts):
            r, c = divmod(i, COLS)
            x = PANEL_X + 20 + c*(CARD_W+CARD_GAP)
            yy = py + PANEL_HDR + r*(CARD_H+CARD_GAP)
            p.append(host_card(x, yy, CARD_W, CARD_H, h))

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif">' + "".join(p) + '</svg>')
    open(out, "w", encoding="utf-8").write(f'<!doctype html><html><body style="margin:0;background:#020617">{svg}</body></html>')
    print(f"wrote {out} ({W}x{H})")

if __name__ == "__main__":
    main()
