# See Dockerfile.build for instructions on bumping this.
FROM ghcr.io/py-cov-action/python-coverage-comment-action-base:v6

COPY coverage_comment ./coverage_comment
RUN md5sum -c pyproject.toml.md5 || pip install -e .
