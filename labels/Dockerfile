FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir aiohttp==3.13.5
ENV PYTHONUNBUFFERED=1
COPY app.py ./
COPY labels.json ./
USER 65534:65534
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["python", "app.py"]
