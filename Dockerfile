FROM python:3.13-slim

LABEL description="search-hub"
LABEL maintainer="UHUH"

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=18081

WORKDIR /app

# 安装 ffmpeg, curl
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl && rm -rf /var/lib/apt/lists/*

# 安装 yt-dlp
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && chmod a+rx /usr/local/bin/yt-dlp

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

EXPOSE 18081

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:18081/api/sources || exit 1

ENTRYPOINT ["python", "run.py"]
CMD []
