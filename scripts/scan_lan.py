#!/usr/bin/env python3
"""LAN 发现 + 端口识别 -> topology.json（宿主机执行，适合 Parallels NAT 环境）。

用法: python3 scan_lan.py 192.168.1.0/24 > topology.json
依赖: nmap
"""
import json, re, subprocess, sys

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout

def discover(cidr):
    out = run(["nmap", "-sn", cidr])
    return re.findall(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", out)

def ports(ips):
    if not ips: return {}
    out = run(["nmap", "-sT", "-Pn", "-F", "--open", "-T4"] + ips)
    res, cur = {}, None
    for line in out.splitlines():
        m = re.match(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", line)
        if m: cur = res.setdefault(m.group(1), [])
        m = re.match(r"(\d+)/tcp\s+open\s+(\S+)", line)
        if m and cur is not None: cur.append(f"{m.group(1)}/{m.group(2)}")
    return res

def main():
    cidr = sys.argv[1]
    hosts = discover(cidr)
    p = ports(hosts)
    gw = cidr.rsplit(".", 1)[0] + ".1"
    data = {"network": cidr, "gateway": {"ip": gw, "role": "路由器/网关", "ports": p.get(gw, [])},
            "hosts": [{"ip": h, "role": "终端", "ports": p.get(h, [])} for h in hosts if h != gw]}
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
