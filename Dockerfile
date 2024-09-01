# See Dockerfile.build for instructions on bumping this.
FROM docker.io/ewjoachim/python-coverage-comment-action-base:v7

COPY coverage_comment ./
COPY pyproject.toml ./
RUN md5sum -c pyproject.toml.md5 || uv pip install --editable .
