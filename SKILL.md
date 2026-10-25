---
name: starmap-topology
description: 用 StarMap（星图）资产测绘平台给「自己的网络」做资产发现并画出网络拓扑图。当用户提到"网络拓扑、资产测绘、starmap、星图、内网资产梳理、画拓扑、家里网络怎么连的"等场景时使用。默认只对用户本人/已书面授权的网段操作；扫描前必须先确认授权范围。
---

# StarMap 网络拓扑测绘（Starmap Topology）

一条可复现的流水线：**部署 StarMap → 发现资产 → 建资产星图 → 渲染拓扑图 → 留档**。

> 核心边界：只扫**你自己的网段**。StarMap 本身是资产测绘平台，不是"打点"工具；本 skill 默认只读，不做爆破/利用。

---

## 0. 开工前：三个确认（缺一不做）

| 确认项 | 内容 |
|---|---|
| **授权** | 网段属于本人/本单位；记下授权人、时间、范围 |
| **范围** | 明确 CIDR（例：`192.168.1.0/24`）；默认排除运营商内网、他人网络 |
| **方式** | 只做存活发现 + 端口识别（TCP connect / ICMP / ARP），不碰口令、不做漏洞利用 |

---

## 1. 部署 StarMap（macOS 没有原生二进制）

StarMap 官方只发 **Linux x86_64 / Linux arm64 / Windows** 三个二进制，仓库只有 README 无源码。Apple Silicon 上的可行路径：跑在 **arm64 Linux 虚拟机**（Parallels 里的 Kali）里。

```bash
# 1) 下载（在宿主机，速度快）
curl -L -o /tmp/starmap \
  https://github.com/adminbugw/starmap/releases/download/v1.0.3/starmap-linux-arm64

# 2) 传进虚拟机（示例：Kali，IP 见下方"发现 VM 的 IP"）
scp /tmp/starmap bruce_xiaowei@<VM_IP>:/tmp/starmap

# 3) 启动（见第 3 条的 fd limit 坑，必须带 ulimit）
ssh bruce_xiaowei@<VM_IP> 'mkdir -p ~/starmap && mv /tmp/starmap ~/starmap/starmap && chmod +x ~/starmap/starmap && cd ~/starmap && bash -c "ulimit -n 65535; nohup ./starmap > starmap.log 2>&1 &" && sleep 6 && grep -A2 登录凭据 starmap.log'
```

**发现 VM 的 IP**：`prlctl list -a`（Parallels 共享网络下通常是 `10.211.55.x`；`prlctl` 走 `/usr/local/bin` 的包装脚本可能因沙箱/ps 失败，直接调
`/Applications/Parallels Desktop.app/Contents/MacOS/prlctl`）。

启动后：
- Web UI：`http://<VM_IP>:8080`
- 管理员密码**每次启动都会重新生成**，在 `~/starmap/starmap.log` 的「登录凭据」里
- 数据落盘：`~/starmap/data/asset_collector.db`（SQLite，表 `asset_libraries` / `star_map_nodes` / `star_map_edges`）

---

## 2. 资产发现（两种模式，按网络位置选）

### 模式 A：StarMap 自己扫（VM 与目标同二层时最准）

```bash
# 登录拿 cookie
curl -s -c /tmp/sm.jar -X POST -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<启动口令>"}' http://<VM_IP>:8080/api/auth/login

# 建任务（批量入口，inputs 里 \n 分隔多个目标）
curl -s -b /tmp/sm.jar -X POST -H 'Content-Type: application/json' \
  -d '{"name":"家庭网络","inputs":"192.168.1.0/24","enable_gogo":true,"auto_port_scan":true,"query_mode":"auto"}' \
  http://<VM_IP>:8080/api/tasks/batch

# 或直接端口扫描任务
curl -s -b /tmp/sm.jar -X POST -H 'Content-Type: application/json' \
  -d '{"name":"lan-scan","targets":"192.168.1.0/24","preset":"standard"}' \
  http://<VM_IP>:8080/api/portscan
```

### 模式 B：宿主机 nmap 发现 + 回填 StarMap（NAT 下必须这样）

Parallels 共享网络（NAT）里，StarMap 的存活探测会大量漏报（ICMP/ARP 到不了对端），实测 `/24` 全段 0 命中。此时用**宿主机 nmap 做 ARP 发现**，再把结果写进 StarMap 资产库：

```bash
# 1) 宿主机的 ARP 发现（同二层最准）
nmap -sn 192.168.1.0/24

# 2) 对存活主机做 TCP 端口识别
nmap -sT -Pn -F --open -T4 <ip1> <ip2> <ip3>

# 3) 写进 StarMap 资产库（先停服务再改 SQLite，避免 WAL 竞争）
ssh <user>@<VM_IP> "pkill -x starmap; sleep 2"
sqlite3 ~/starmap/data/asset_collector.db <<'SQL'
update asset_libraries set company_name='<企业/网络名>', name=address, ignored=0,
       last_alive_at=datetime('now')
 where address in ('192.168.1.1','192.168.1.21','192.168.1.31');
update asset_libraries set open_ports='53,80,443' where address='192.168.1.1';
update asset_libraries set ignored=1 where (company_name is null or company_name='') and asset_type='ip';
SQL
# 4) 重启（带 ulimit）
```

> 资产 IP 存在 `asset_libraries.address`，不是 `name`/`root`；`company_name` 必须与星图的 company_name 一致才会被收进图。

---

## 3. 建图 + 出图

```bash
# 建星图（company_name 与资产库里的 company_name 对齐）
curl -s -b /tmp/sm.jar -X POST -H 'Content-Type: application/json' \
  -d '{"company_name":"<企业/网络名>","project_id":0}' http://<VM_IP>:8080/api/starmaps

# 重建（把资产灌进图）
curl -s -b /tmp/sm.jar -X POST http://<VM_IP>:8080/api/starmaps/<id>/rebuild

# 取图数据（nodes/edges JSON）
curl -s -b /tmp/sm.jar http://<VM_IP>:8080/api/starmaps/<id>/data > graph.json
```

**渲染成拓扑图**（不依赖 WebGL，输出 PNG）：

```bash
python3 scripts/render_topology.py assets/topology.json /tmp/topology.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-sandbox \
  --user-data-dir=/tmp/chrome-prof --screenshot=assets/network-topology.png \
  --window-size=1400,860 file:///tmp/topology.html
```

**要 StarMap 自己的星图界面**（3D 星图，需要 WebGL）：用 CDP 驱动 headless Chrome 登录后截图，
必须加 `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`，否则报
`Error creating WebGL context`。参考 `scripts/starmap_api.py` 的 `shot_ui()`。

---

## 4. 常见坑

| 现象 | 原因 / 解法 |
|---|---|
| 多目标扫描 2 秒结束、0 存活 | fd limit 1024。启动前 `ulimit -n 65535`（日志里有 `[warn] System fd limit` 提示） |
| `/24` 扫不到任何主机 | VM 在 NAT 里，ARP/ICMP 发现失效 → 用模式 B |
| 星图只有 1 个公司节点 | 资产的 `company_name` 没对上；改完库要 `rebuild` |
| UI 报 `Error creating WebGL context` | headless 缺软件 WebGL，加 SwiftShader 参数 |
| 登录 401 | 密码每次启动重新生成，重读 `starmap.log` |
| 服务被挂起后不可达 | 虚拟机被 Parallels 自动挂起：`prlctl resume "Kali Linux"` |

---

## 5. 交付物

- `assets/network-topology.png` — 拓扑图（本 skill 自带渲染器产出）
- `assets/starmap-ui.png` — StarMap 星图界面截图
- `assets/topology.json` — 拓扑数据（可版本化、可复跑）
- `assets/graph.json` — StarMap 导出的节点/边数据

## 6. 合规声明

仅用于本人或已书面授权网络的安全自查。禁止对未授权目标扫描、测绘或探测。
