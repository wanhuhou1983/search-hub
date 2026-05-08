# ============================================================
# 统一搜索中心 — Docker 镜像
# ============================================================
# 构建：
#   docker build -t search-hub .
#
# 运行：
#   docker run -d --name search-hub -p 18080:18080 search-hub
#
# 自定义端口：
#   docker run -d --name search-hub -p 19080:19080 -e PORT=19080 search-hub
# ============================================================

FROM python:3.13-slim

LABEL description="统一搜索中心（网盘搜索 + 视频下载）"
LABEL maintainer="UHUH"

# 避免 Python 输出缓冲
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=18080

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT/api/sources')" || exit 1

EXPOSE ${PORT}

ENTRYPOINT ["python", "run.py"]
CMD []
