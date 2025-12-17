# --- Single Stage (Simple) ---
# Reverted due to network failure during apt-get in multi-stage build
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download minimal generic spacy model if needed
RUN python -m spacy download en_core_web_sm

COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python", "src/main.py"]
