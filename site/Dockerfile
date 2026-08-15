# Собирает site/dist. Используется docker-compose.prod.yml (профиль "build") и может
# запускаться отдельно: docker build -f site/Dockerfile -t ayka-site-builder . && \
#   docker run --rm -v $(pwd)/site/dist:/app/site/dist -e BUILD_ENV=prod ayka-site-builder
FROM python:3.12-slim

WORKDIR /app

COPY site/requirements.txt ./site/requirements.txt
RUN pip install --no-cache-dir -r site/requirements.txt

COPY site/ ./site/

ENV BUILD_ENV=prod
CMD ["python", "site/build.py"]
