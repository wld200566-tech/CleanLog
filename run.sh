#!/bin/bash
# CleanLog 一键运行脚本
# 优先使用 Docker，其次本地 Python

set -e
cd "$(dirname "$0")"

if command -v docker &>/dev/null; then
    echo "使用 Docker 启动 CleanLog..."
    docker build -t cleanlog . 2>/dev/null || true
    docker run --rm -p 8501:8501 cleanlog
else
    echo "Docker 未安装，尝试本地 Python..."
    pip3 install -q streamlit pandas plotly pyyaml openpyxl matplotlib seaborn 2>/dev/null || {
        echo "依赖安装失败。若出现 xcode-select 错误，请："
        echo "  1. 在终端执行: xcode-select --install"
        echo "  2. 或安装 Docker 后重新运行此脚本"
        echo "  3. 详见 RUN.md"
        exit 1
    }
    python3 -m streamlit run app.py --server.address=0.0.0.0
fi
