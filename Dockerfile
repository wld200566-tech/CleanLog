# CleanLog - 无 xcode 依赖的 Docker 方案
FROM python:3.11-slim

WORKDIR /app

# 安装依赖（使用预编译 wheel，无需编译）
RUN pip install --no-cache-dir --prefer-binary \
    streamlit>=1.28.0 \
    pandas>=1.5.0 \
    plotly>=5.0.0 \
    pyyaml>=6.0 \
    matplotlib>=3.5.0 \
    seaborn>=0.12.0 \
    openpyxl>=3.0.0

COPY . .

# Streamlit 默认 8501，绑定所有接口
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
