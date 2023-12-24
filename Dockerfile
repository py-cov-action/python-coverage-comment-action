# See Dockerfile.build for instructions on bumping this.
FROM ewjoachim/python-coverage-comment-action-base:v5

COPY coverage_comment ./coverage_comment
RUN md5sum -c pyproject.toml.md5 || pip install -e .
