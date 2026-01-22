FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces usa a porta 7860 por padrão
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
