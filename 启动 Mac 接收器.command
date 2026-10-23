#!/bin/bash
# 双击本文件即可启动 WatchMouse Mac 接收器；关闭终端窗口或按 Ctrl+C 停止。
cd "$(dirname "$0")/Mac" || exit 1

if [ ! -x ../.venv/bin/python ]; then
  echo "缺少 .venv 环境，请先在项目根目录执行："
  echo "  python3 -m venv .venv && .venv/bin/pip install -r Mac/requirements.txt"
  read -r -p "按回车关闭……" _
  exit 1
fi

exec ../.venv/bin/python app.py