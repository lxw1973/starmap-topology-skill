#!/usr/bin/env bash
# 冒烟测试：渲染器能否从示例数据生成 HTML
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/render_topology.py assets/topology.json /tmp/_topo_test.html
grep -q "家庭网络拓扑" /tmp/_topo_test.html && echo "OK: render_topology"
