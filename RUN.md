# CleanLog 运行指南

## 方式一：Docker（推荐，无 xcode 依赖）

若遇到 `xcode-select` 错误，Docker 方案可直接运行，无需安装 Xcode 或 Python：

```bash
cd /Users/wenluodong/cleanlog

# 构建并运行
docker build -t cleanlog .
docker run -p 8501:8501 cleanlog
```

浏览器访问：http://localhost:8501

---

## 方式二：本地 Python（需先解决 xcode-select）

### 1. 安装 Xcode 命令行工具（一次性）

在**终端**中执行（会弹出安装窗口）：

```bash
xcode-select --install
```

安装完成后，再执行下面的依赖安装。

### 2. 安装依赖

```bash
cd /Users/wenluodong/cleanlog
pip3 install streamlit pandas plotly pyyaml openpyxl matplotlib seaborn
# 或使用 requirements.txt
pip3 install -r requirements.txt
```

### 3. 运行

```bash
python3 -m streamlit run app.py
```

浏览器访问：http://localhost:8501

---

## 方式三：Homebrew Python（无系统 Python 时）

若系统 Python 有问题，可先用 Homebrew 安装 Python：

```bash
brew install python
# 使用 Homebrew 的 pip
/opt/homebrew/bin/pip3 install -r requirements.txt
/opt/homebrew/bin/python3 -m streamlit run app.py
```

---

## 常见问题

| 错误 | 处理 |
|------|------|
| `xcode-select: error` | 使用 Docker 或执行 `xcode-select --install` |
| `ModuleNotFoundError` | 确认在 `cleanlog` 目录下运行 |
| 8501 端口被占用 | 使用 `streamlit run app.py --server.port 8502` 指定其他端口 |
