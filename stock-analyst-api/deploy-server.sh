#!/usr/bin/env bash
# 在服务器 /opt/stock-analyst-api 目录执行: bash deploy-server.sh
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f app/main.py ]]; then
  echo "错误：请在包含 app/main.py 的 stock-analyst-api 目录下执行本脚本。"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "正在尝试安装 python3 / python3-venv（需 root）..."
  apt-get update -qq && apt-get install -y python3 python3-venv python3-pip
fi

python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -U pip wheel -q
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ""
  echo ">>> 已创建 .env ，请编辑填入 MINIMAX_API_KEY 后再运行："
  echo "    nano .env"
  echo ">>> 然后再次执行: bash deploy-server.sh"
  exit 0
fi

if ! grep -qE '^MINIMAX_API_KEY=.+' .env || grep -qE '^MINIMAX_API_KEY=\s*$' .env; then
  echo ">>> .env 里 MINIMAX_API_KEY 为空，请先 nano .env 填好密钥后再运行本脚本。"
  exit 1
fi

PORT="${PORT:-8788}"
PIDF="/tmp/stock-analyst-api.pid"
if [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "停止旧进程 $(cat "$PIDF") ..."
  kill "$(cat "$PIDF")" 2>/dev/null || true
  sleep 1
fi

nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT" >/tmp/stock-analyst-api.log 2>&1 &
echo $! >"$PIDF"
echo ""
echo "已启动。PID=$(cat "$PIDF")  端口=$PORT"
echo "日志: tail -f /tmp/stock-analyst-api.log"
echo "自检: curl -s http://127.0.0.1:${PORT}/health"
echo ""
