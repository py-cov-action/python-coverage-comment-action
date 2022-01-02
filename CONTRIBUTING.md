## Contribution

You're welcome to contribute, though I can't promise the experience will be as smooth as I'd like it to. I'll let you figure out most of it, though feel free to ask for help on anything you're stuck.

### Things to know:

- Python3.10
- Use [Poetry](https://python-poetry.org/)
- Launch tests with `pytest`, config is in setup.cfg
- `black`, `isort`, `flake8` and once mypy will work with 3.10, we'll use it. There's `pre-commit`, so you can install hooks with `pre-commit install`.
- `docker`. Classic stuff.

### Launching locally

```console
$ # Either push (compute & post badge), pull_request (compute comment) or workflow_run (post comment)
$ export GITHUB_EVENT_NAME=workflow_run
$ # Used only for push to test that the current branch is the repo default branch
$ export GITHUB_REF=
$ # Used only for workflow_run, set to a pull_request run id
$ export GITHUB_PR_RUN_ID=xxx
$ # Used only in pull_request to compute diff coverage
$ export GITHUB_BASE_REF=master
$ # Used everywhere
$ export GITHUB_REPOSITORY=ewjoachim/python-coverage-comment-action-example
$ # Used everywhere. Generate at https://github.com/settings/tokens/new?scopes=repo&description=test%20python-coverage-comment-action
$  export GITHUB_TOKEN=
```
Then either launch with `poetry run coverage_comment` or through docker.
