FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download minimal generic spacy model if needed, or handle in entrypoint
RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["python", "src/main.py"]
