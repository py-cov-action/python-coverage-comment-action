FROM python:3-slim

ADD https://install.python-poetry.org /tmp/get-poetry.py

RUN python /tmp/get-poetry.py
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workdir

COPY pyproject.toml ./
COPY poetry.lock ./
RUN poetry install --no-dev

COPY coverage_comment ./coverage_comment
COPY default.md.j2 ./

CMD [ "poetry", "run", "python", "-m", "coverage_comment" ]
