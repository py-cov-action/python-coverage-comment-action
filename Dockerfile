FROM python:3-slim

RUN set -eux; \
    apt-get update; \
    apt-get install -y git; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workdir

COPY pyproject.toml ./
COPY poetry.lock ./
COPY coverage_comment ./coverage_comment
RUN pip install .

CMD [ "coverage_comment" ]
