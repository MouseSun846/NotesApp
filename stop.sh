#!/bin/bash

# 确保脚本在项目根目录下执行
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "==========================================="
echo "🛑  正在停止 FunASR Notes 所有服务..."
echo "==========================================="

# 杀掉端口 3000 和 8010 上的进程
PIDS=$(lsof -ti:3000,8010)

if [ -n "$PIDS" ]; then
    echo "🧹 正在清理进程 PID:"
    echo "$PIDS"
    echo "$PIDS" | xargs kill -9 2>/dev/null
    echo "✅ 服务已成功关闭。"
else
    echo "ℹ️  未检测到运行在 3000 或 8010 端口上的服务。"
fi

echo "==========================================="
