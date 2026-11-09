#!/usr/bin/env bash
# 公网演示：本机公网模式服务（127.0.0.1:8766，Basic 认证）+ cloudflared 临时隧道（HTTPS）。
# 用法：scripts/public.sh start|stop|status
# 隧道地址每次启动都会变；关闭电脑或停止后即失效。口令在 .public_token（600 权限，已 gitignore）。
set -euo pipefail
cd "$(dirname "$0")/.."
RUN=.run
mkdir -p "$RUN"
PORT="${SGTRACE_PUBLIC_PORT:-8766}"

url() { grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$RUN/cloudflared.log" 2>/dev/null | head -1; }
alive() { [ -f "$RUN/$1.pid" ] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }

case "${1:-status}" in
  start)
    command -v cloudflared >/dev/null || { echo "缺少 cloudflared"; exit 1; }
    if ! alive server; then
      SGTRACE_PUBLIC=1 SGTRACE_PORT="$PORT" nohup .venv/bin/python -m sgtrace.server >"$RUN/server.log" 2>&1 &
      echo $! >"$RUN/server.pid"
    fi
    if ! alive tunnel; then
      : >"$RUN/cloudflared.log"
      nohup cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" >"$RUN/cloudflared.log" 2>&1 &
      echo $! >"$RUN/tunnel.pid"
    fi
    for _ in $(seq 1 30); do [ -n "$(url)" ] && break; sleep 1; done
    echo "公网地址：$(url)"
    echo "用户名：demo"
    echo "口令：见 .public_token"
    ;;
  stop)
    for n in tunnel server; do
      if alive "$n"; then kill "$(cat "$RUN/$n.pid")" && echo "已停止 $n"; fi
      rm -f "$RUN/$n.pid"
    done
    ;;
  status)
    for n in server tunnel; do alive "$n" && echo "$n: 运行中" || echo "$n: 未运行"; done
    alive tunnel && echo "公网地址：$(url)"
    ;;
  *) echo "用法：$0 start|stop|status"; exit 1 ;;
esac
