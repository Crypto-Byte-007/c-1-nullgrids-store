FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password ctfuser

USER ctfuser

EXPOSE 5000

CMD ["sh", "-c", "gunicorn -w 4 -b 0.0.0.0:${PORT:-5000} app:app"]