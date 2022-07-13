## Contribution

You're welcome to contribute, though I can't promise the experience will be as smooth as I'd like it to. I'll let you figure out most of it, though feel free to ask for help on anything you're stuck.

### Things to know:

- Python3.10
- Use [Poetry](https://python-poetry.org/)
- Launch tests with `pytest`, config is in setup.cfg
- `black`, `isort`, `flake8` and once mypy will work with 3.10, we'll use it. There's `pre-commit`, so you can install hooks with `pre-commit install`.
- `docker`. Classic stuff.

### Launching locally

Use:

```console
$ source ./dev-env
```
This should take care of everything and will display instructions.
Feel free to read the script yourself to see what it does.

You'll need a GitHub token to test the action locally. You have 3 choices:
- Before launching `dev-env`, copy `dev-env-vars.dist` to `dev-env-vars` and
  set your token
- After launching `dev-env`, run `token-from-gh` to reuse your `gh` token
  for the action (you may need to define additional scopes with
  `gh auth refresh --scope=...`)
- After launching `dev-env`, run `create-token` to interactively create a
  personnal access token (feel free to then save it to `dev-env-vars`)

#### Manually
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

### End to end tests

To run the end-to-end tests, you'll need:

- `gh` [installed](https://cli.github.com/)
- 2 envvars `COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1` and `COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2` containing
  personnal access tokens for 2 distinct users. You may omit the 2nd user but
  some tests won't run. Use [this
  link](https://github.com/settings/tokens/new?scopes=repo,workflow,delete_repo&description=Python%20Coverage%20Comment%20Action%20CI%20-%20User%201)
  to generate tokens with the proper configuration.
  It's a good idea to **not** use your main GitHub user for this because the tests
  do some destructive actions (like deleting repos).
- Make sure you don't have a repository named "end_to_end_python_coverage_comment_action"
  (that would be a leftover of a previous test). If you do, delete it with
  `gh repo delete end_to_end_python_coverage_comment_action`.
- Please be aware that the tests will launch `gh auth setup-git` which might be
  surprising if you use `https` remotes (sadly, setting `GIT_CONFIG_GLOBAL`
  seems not to be enough to isolate tests.)
- You can disable the deletion of repositories after the tests by setting the
  environment variable `COVERAGE_COMMENT_E2E_CLEAN_GITHUB_AFTER_TESTS=false`
