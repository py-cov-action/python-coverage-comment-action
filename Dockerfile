FROM python:3-slim

ADD https://install.python-poetry.org /tmp/get-poetry.py

RUN python /tmp/get-poetry.py
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workdir

COPY pyproject.toml ./
COPY poetry.lock ./
COPY coverage_comment ./coverage_comment
COPY default.md.j2 /var/default.md.j2
RUN pip install .

CMD [ "coverage_comment" ]
