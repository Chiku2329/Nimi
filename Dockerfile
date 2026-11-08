FROM python:3.12-slim

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    DATA_DIR=/data \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 user && mkdir -p /data
WORKDIR /home/user/app

# Install dependencies as root so the runtime account cannot modify them.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code is read-only to the runtime account. Only persistent data,
# Chainlit's upload directory, and its runtime translations directory are writable.
COPY --chown=root:root . .
RUN mkdir -p /home/user/app/.files /home/user/app/.chainlit/translations \
    && chown -R user:user /data /home/user/app/.files /home/user/app/.chainlit/translations \
    && chmod 700 /data /home/user/app/.files \
    && chmod -R a-w /home/user/app \
    && chmod u+rwx /home/user/app/.files \
    && chmod -R u+rwX /home/user/app/.chainlit/translations

USER user
VOLUME ["/data"]
EXPOSE 7860
CMD ["sh", "-c", "umask 077 && python init_db.py && uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}"]
