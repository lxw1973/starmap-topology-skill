#!/usr/bin/env bash
# 安装并启动 StarMap 到 arm64 Linux 虚拟机
# 用法: ./install_starmap.sh <user@vm-ip> [version] [remote_dir]
set -euo pipefail
VM="${1:?用法: $0 <user@vm-ip> [version] [remote_dir]}"
VER="${2:-v1.0.3}"
DIR="${3:-/home/${VM%@*}/starmap}"
TMP=$(mktemp -d)

echo "[1/4] 下载 starmap-linux-arm64 $VER"
curl -L --retry 2 -o "$TMP/starmap" \
  "https://github.com/adminbugw/starmap/releases/download/$VER/starmap-linux-arm64"

echo "[2/4] 传到 $VM"
scp "$TMP/starmap" "$VM:/tmp/starmap"

echo "[3/4] 启动（带 ulimit -n 65535）"
ssh "$VM" "mkdir -p '$DIR' && mv /tmp/starmap '$DIR/starmap' && chmod +x '$DIR/starmap' && \
  cd '$DIR' && bash -c 'ulimit -n 65535; nohup ./starmap > starmap.log 2>&1 &' && sleep 6"

echo "[4/4] 启动凭据"
ssh "$VM" "grep -A3 登录凭据 '$DIR/starmap.log' | head -5; echo; ss -ltn | grep 8080 || echo '8080 未监听'"
rm -rf "$TMP"
echo "完成：http://${VM#*@}:8080 （用户名 admin，密码见上）"
