FROM python:3-slim

WORKDIR /tool

RUN set -eux; \
    apt-get update; \
    apt-get install -y git; \
    rm -rf /var/lib/apt/lists/*; \
    pip install ghapi diff-cover

COPY entrypoint.py /entrypoint.py
COPY add-to-wiki.sh /add-to-wiki.sh

CMD [ "/entrypoint.py" ]
