FROM python:3-slim

WORKDIR /tool
WORKDIR /workdir

COPY tool/requirements.txt /tool/
RUN set -eux; \
    apt-get update; \
    apt-get install -y git; \
    rm -rf /var/lib/apt/lists/*

RUN pip install -r /tool/requirements.txt
RUN ls /tool
COPY tool /tool
RUN ls /tool

CMD [ "/tool/entrypoint.py" ]
