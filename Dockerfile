# See Dockerfile.build for instructions on bumping this.
FROM ewjoachim/python-coverage-comment-action-base:v1

COPY coverage_comment ./coverage_comment
RUN pipx run poetry install --no-dev
