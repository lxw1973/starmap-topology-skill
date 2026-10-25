# StarMap API 速查 & 排错笔记

Base URL：`http://<vm-ip>:8080`，前端请求统一前缀 `/api`，会话 Cookie：`asset_collector_session`。

## 认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/auth/login` | `{"username":"admin","password":"..."}`，密码每次启动重新生成 |
| GET | `/api/auth/me` | 校验会话 |
| POST | `/api/auth/logout` | 注销 |

## 任务 / 端口扫描

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/tasks/batch` | 批量建任务：`{name, inputs:"target1\ntarget2", enable_gogo, auto_port_scan, query_mode:"auto", project_id}` |
| GET | `/api/tasks` / `/api/tasks/{id}` | 任务列表/详情（status/progress 轮询） |
| GET | `/api/tasks/{id}/logs` | 任务日志 |
| POST | `/api/portscan` | 端口扫描：`{name, targets:"CIDR,IP", preset:"fast|standard|deep|database"}` |
| GET | `/api/portscan/{id}` | 结果分页：`?page=&page_size=` |
| GET | `/api/portscan/{id}/stats` | alive/open 统计 |

## 星图

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/starmaps` | `{company_name, project_id:0}` |
| POST | `/api/starmaps/{id}/rebuild` | 从资产库重建图（资产 `company_name` 必须对上） |
| GET | `/api/starmaps/{id}/data` | `{nodes:[...], edges:[...]}` |
| GET | `/api/starmaps/{id}/export?format=json` | 导出 |

## 数据模型（SQLite `data/asset_collector.db`）

- `asset_libraries`：资产主表。**IP 存在 `address`**，`name` 可留空；企业维度是 `company_name`；开放端口 `open_ports`（逗号分隔）
- `asset_relations`：`src_asset_id` / `dst_asset_id` / `relation`
- `star_map_nodes`：`graph_id`,`node_key`,`node_type`,`label`,`asset_id`,`asset_type`
- `star_map_edges`：`graph_id`,`source_node_id`,`target_node_id`,`relation_type`

## 踩坑记录

1. **fd limit 1024**：多目标扫描会瞬间结束且 0 结果。启动前必须 `ulimit -n 65535`（日志有 `[warn] System fd limit`）。
2. **NAT 下扫描失效**：Parallels 共享网络里 ARP/ICMP 发现到不了目标，`/24` 会 0 命中；同二层用 `nmap -sn` 才准。
3. **星图只有公司节点**：资产 `company_name` 与星图 `company_name` 不一致；改库后要 `rebuild`（不能只刷新页面）。
4. **PATCH `/api/assets/{id}` 不落 company**：接口返回 `{"ok":true}` 但 `company_name` 不变，需直接改库。
5. **UI WebGL**：headless Chrome 默认 `--disable-gpu` 会报 `Error creating WebGL context`；加
   `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`。
6. **Chrome 头less 起不来**：`Failed to create a unique user data directory for headless` → 必须 `--user-data-dir=<可写目录>`。
7. **虚拟机被自动挂起**：`prlctl resume "Kali Linux"`（直接调 `/Applications/Parallels Desktop.app/Contents/MacOS/prlctl`）。
8. **SSH 公钥被截断**：把长字符串经多层 shell 传递容易出问题，用 base64 中转最稳。
