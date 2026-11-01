FROM python:3.12-slim

RUN useradd -m -u 1000 user && mkdir -p /data && chown user:user /data
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH DATA_DIR=/data
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

VOLUME ["/data"]
EXPOSE 7860
CMD ["sh", "-c", "python init_db.py && chainlit run app.py --host 0.0.0.0 --port ${PORT:-7860} --headless"]
