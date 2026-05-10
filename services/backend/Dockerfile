FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DJANGO_SETTINGS_MODULE=config.settings.production
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
