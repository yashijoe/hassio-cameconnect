ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8
RUN apk add --no-cache python3 py3-pip jq

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /app
COPY run.sh /run.sh
# Normalizza fine riga nel caso l'editor salvi CRLF
RUN sed -i 's/\r$//' /run.sh && chmod +x /run.sh

EXPOSE 8080
ENV PATH="/opt/venv/bin:${PATH}"

CMD ["/run.sh"]

