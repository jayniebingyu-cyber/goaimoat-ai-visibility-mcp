FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py geo_seo_audit.py ./

# stdio transport（Glama 等目录站的硬性假设）
CMD ["python", "server.py"]
