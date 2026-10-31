FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 KOBRA_DATA_DIR=/data KOBRA_LISTEN=0.0.0.0
WORKDIR /app
COPY requirements-lock.txt .
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements-lock.txt \
    && groupadd --gid 10001 monitor \
    && useradd --uid 10001 --gid monitor --no-create-home monitor \
    && mkdir /data && chown monitor:monitor /data
COPY --chown=monitor:monitor . .
USER monitor
VOLUME ["/data"]
EXPOSE 7125
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7125/health', timeout=3)"
CMD ["python", "monitor.py"]
