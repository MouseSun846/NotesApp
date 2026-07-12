#!/bin/bash

# 确保脚本在项目根目录下执行
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "==========================================="
echo "🪐  正在初始化 FunASR Notes 运行环境..."
echo "==========================================="

# 1. 清理已占用的端口 (3000 和 8010)
echo "🧹 正在清理已占用的端口 3000 与 8010..."
lsof -ti:3000,8010 | xargs kill -9 2>/dev/null
sleep 1

# 2. 启动后端服务器
echo "🐍 正在使用 Homebrew Python 3.11 启动后端服务..."
BACKEND_PYTHON="/opt/homebrew/bin/python3.11"

if [ ! -f "$BACKEND_PYTHON" ]; then
    # 回退到默认 python3 检查
    echo "⚠️  未在 /opt/homebrew/bin/python3.11 找到 Python，尝试使用默认 python3..."
    BACKEND_PYTHON="python3"
fi

# 启动后端并重定向日志
nohup "$BACKEND_PYTHON" -m uvicorn backend.main:app --host 0.0.0.0 --port 8010 --reload > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)，日志输出至 backend.log"

# 3. 启动前端服务器
echo "⚡ 正在启动前端开发服务器..."
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)，日志输出至 frontend.log"

# 4. 等待并验证服务启动状态
echo "⏳ 正在等待服务就绪..."
sleep 3

if ps -p $BACKEND_PID > /dev/null; then
    echo "🎉 后端服务运行正常: http://localhost:8010"
else
    echo "❌ 后端服务启动失败，请检查 backend.log 文件！"
fi

if ps -p $FRONTEND_PID > /dev/null; then
    echo "🎉 前端服务运行正常: http://localhost:3000"
else
    echo "❌ 前端服务启动失败，请检查 frontend.log 文件！"
fi

echo "==========================================="
echo "💡 提示："
echo "   - 查看后端实时日志: tail -f backend.log"
echo "   - 查看前端实时日志: tail -f frontend.log"
echo "   - 停止所有服务:     ./stop.sh"
echo "==========================================="
