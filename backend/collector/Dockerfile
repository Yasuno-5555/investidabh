# Playwright公式イメージを使用 (ブラウザ同梱済み)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightのブラウザをインストール (Chromiumのみで軽量化)
RUN playwright install chromium && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/

# Pythonの出力バッファリングを無効化 (ログ即時出力のため)
ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]
