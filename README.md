# GitHub Action: Python Coverage Comment

[![Coverage badge](https://raw.githubusercontent.com/py-cov-action/python-coverage-comment-action/python-coverage-comment-action-data/badge.svg)](https://github.com/py-cov-action/python-coverage-comment-action/tree/python-coverage-comment-action-data)

## Presentation

Publish diff coverage report as PR comment, create a coverage badge to
display on the readme, and a browsable HTML coverage report (hosted in a dedicated
branch of the repository)

[See this action in action](https://github.com/py-cov-action/python-coverage-comment-action-v3-example)

## What does it do?

This action operates on an already generated `.coverage` file from
[coverage](https://coverage.readthedocs.io/en/6.2/).

It has two main modes of operation:

### PR mode

On PRs, it will analyze the `.coverage` file, and produce a comment that
will be posted to the PR. If a comment had already previously be written,
it will be updated. The comment contains information on the evolution
of coverage rate attributed to this PR, as well as the rate of coverage
for lines that this PR introduces. There's also a small analysis for each
file in a collapsed block.

See [an example](https://github.com/py-cov-action/python-coverage-comment-action-v3-example/pull/2#issuecomment-1244431724).

### Default branch mode

On repository's default branch, it will extract the coverage rate and create
files that will be stored on a dedicated independant branch in your repository.

These files include:

- a `svg` badge to include in your README
- a `json` file that can be used by [shields.io](https://shields.io) if your
  repository is public to customize the look of your badge
- Another `json` file used internally by the action to report on coverage
  evolution (does a PR make the coverage go up or down?)
- A short file-by-file coverage report embedded directy into the branch's README
- The full HTML coverage report and links to make this report browsable

See [an example](https://github.com/py-cov-action/python-coverage-comment-action-v3-example)

## Usage

### Setup

Please ensure that your `.coverage` file(s) is created with the option
[`relative_files = true`](https://coverage.readthedocs.io/en/6.2/config.html#config-run-relative-files).

Please ensure that the branch `python-coverage-comment-action-data` is not
protected (there's no reason that it would be the case, except if you have very
sprecific wildcard rules). If it is, either adjust your rules, or set the
`COVERAGE_DATA_BRANCH` parameter as described below. GitHub Actions will create
this branch with initial data at the first run if it doesn't exist, and will
independently commit to that branch after each commit to your default branch.

### Badge

Once the action has run on your default branch, all the details for how to integrate the
badge to your Readme will be displayed in:

- The Readme of the `python-coverage-comment-action-data` branch
- The text output of the workflow run

### Basic usage
```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches:
      - 'main'

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    permissions:
      # Gives the action the necessary permissions for publishing new
      # comments in pull requests.
      pull-requests: write
      # Gives the action the necessary permissions for pushing data to the
      # python-coverage-comment-action branch, and for editing existing
      # comments (to avoid publishing multiple comments in the same PR)
      contents: write
    steps:
      - uses: actions/checkout@v3

      - name: Install everything, run the tests, produce the .coverage file
        run: make test  # This is the part where you put your own test command

      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ github.token }}

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@v3
        if: steps.coverage_comment.outputs.COMMENT_FILE_WRITTEN == 'true'
        with:
          # If you use a different name, update COMMENT_ARTIFACT_NAME accordingly
          name: python-coverage-comment-action
          # If you use a different name, update COMMENT_FILENAME accordingly
          path: python-coverage-comment-action.txt
```

```yaml
# .github/workflows/coverage.yml
name: Post coverage comment

on:
  workflow_run:
    workflows: ["CI"]
    types:
      - completed

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    if: github.event.workflow_run.event == 'pull_request' && github.event.workflow_run.conclusion == 'success'
    permissions:
      # Gives the action the necessary permissions for publishing new
      # comments in pull requests.
      pull-requests: write
      # Gives the action the necessary permissions for editing existing
      # comments (to avoid publishing multiple comments in the same PR)
      contents: write
      # Gives the action the necessary permissions for looking up the
      # workflow that launched this workflow, and download the related
      # artifact that contains the comment to be published
      actions: read
    steps:
      # DO NOT run actions/checkout here, for security reasons
      # For details, refer to https://securitylab.github.com/research/github-actions-preventing-pwn-requests/
      - name: Post comment
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_PR_RUN_ID: ${{ github.event.workflow_run.id }}
          # Update those if you changed the default values:
          # COMMENT_ARTIFACT_NAME: python-coverage-comment-action
          # COMMENT_FILENAME: python-coverage-comment-action.txt
```

### Merging multiple coverage reports

In case you have a job matrix and you want the report to be on the global
coverage, you can configure your `ci.yml` like this (`coverage.yml` remains the
same)

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - 'master'
    tags:
      - '*'

jobs:
  build:
    strategy:
      matrix:
        include:
          - python_version: "3.7"
          - python_version: "3.8"
          - python_version: "3.9"
          - python_version: "3.10"

    name: "Python ${{ matrix.python_version }}"
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        id: setup-python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python_version }}

      - name: Install everything, run the tests, produce a .coverage.xxx file
        run: make test  # This is the part where you put your own test command
        env:
          COVERAGE_FILE: ".coverage.${{ matrix.python_version }}"
          # Alternatively you can run coverage with the --parallel flag or add
          # `parallel = True` in the coverage config file.
          # If using pytest-cov, you can also add the `--cov-append` flag
          # directly or through PYTEST_ADD_OPTS.

      - name: Store coverage file
        uses: actions/upload-artifact@v3
        with:
          name: coverage
          path: .coverage.${{ matrix.python_version }}

  coverage:
    name: Coverage
    runs-on: ubuntu-latest
    needs: build
    permissions:
      pull-requests: write
      contents: write
    steps:
      - uses: actions/checkout@v3

      - uses: actions/download-artifact@v3
        id: download
        with:
          name: 'coverage'

      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@v3
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MERGE_COVERAGE_FILES: true

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@v3
        if: steps.coverage_comment.outputs.COMMENT_FILE_WRITTEN == 'true'
        with:
          name: python-coverage-comment-action
          path: python-coverage-comment-action.txt

```

### All options
```yaml
- name: Display coverage
  id: coverage_comment
  uses: py-cov-action/python-coverage-comment-action@v3
  with:
    GITHUB_TOKEN: ${{ github.token }}

    # Only necessary in the "workflow_run" workflow.
    GITHUB_PR_RUN_ID: ${{ inputs.GITHUB_PR_RUN_ID }}

    # If the coverage percentage is above or equal to this value, the badge will be green.
    MINIMUM_GREEN: 100

    # Same with orange. Below is red.
    MINIMUM_ORANGE: 70

    # If true, will run `coverage combine` before reading the `.coverage` file.
    MERGE_COVERAGE_FILES: false

    # If true, will create an annotation on every line with missing coverage on a pull request.
    ANNOTATE_MISSING_LINES: false

    # Only needed if ANNOTATE_MISSING_LINES is set to true. This parameter allows you to choose between
    # notice, warning and error as annotation type. For more information look here:
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message
    ANNOTATION_TYPE: warning

    # Name of the artifact in which the body of the comment to post on the PR is stored.
    # You typically don't have to change this unless you're already using this name for something else.
    COMMENT_ARTIFACT_NAME: python-coverage-comment-action

    # Name of the file in which the body of the comment to post on the PR is stored.
    # You typically don't have to change this unless you're already using this name for something else.
    COMMENT_FILENAME: python-coverage-comment-action.txt

    # An alternative template for the comment for pull requests. See details below.
    COMMENT_TEMPLATE: The coverage rate is `{{ coverage.info.percent_covered | pct }}`{{ marker }}

    # Name of the branch in which coverage data will be stored on the repository.
    # Please make sure that this branch is not protected.
    COVERAGE_DATA_BRANCH: python-coverage-comment-action-data

    # Deprecated, see https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/enabling-debug-logging
    VERBOSE: false
```

## Overriding the template

By default, comments are generated from a
[Jinja](https://jinja.palletsprojects.com) template that you can read
[here](https://github.com/py-cov-action/python-coverage-comment-action/blob/v3/coverage_comment/template_files/comment.md.j2).

If you want to change this template, you can set ``COMMENT_TEMPLATE``. This is
an advanced usage, so you're likely to run into more road bumps.

You will need to follow some rules for your template to be valid:

- Your template needs to be syntactically correct with Jinja2 rules
- You may define a new template from scratch, but in this case you are required
  to include ``{{ marker }}``, which includes an HTML comment (invisible on
  GitHub) that the action uses to identify its own comments.
- If you'd rather want to change parts of the default template, you can do so
  by starting your comment with ``{% extends "base" %}``, and then override the
  blocks (``{% block foo %}``) that you wish to change. If you're unsure how it
  works, see [the Jinja
  documentation](https://jinja.palletsprojects.com/en/3.0.x/templates/#template-inheritance)
- In either case, you will most likely want to get yourself familiar with the
  available context variables, the best is to read the code from
  [here](https://github.com/py-cov-action/python-coverage-comment-action/blob/v2/coverage_comment/template.py).
  Should those variables change, we'll do our best to bump the action's major version.

### Examples
In the first example, we change the emoji that illustrates coverage going down from
`:down_arrow:` to `:sob:`:

```jinja2
{% extends "base" %}
{% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
```

In this second example, we replace the whole comment by something much shorter with the
coverage (percentage) of the whole project from the PR build:

```jinja2
"Coverage: {{ coverage.info.percent_covered | pct }}{{ marker }}"
```

# Other topics
## Pinning
On the examples above, the version was set to `v3` (a branch). You can also pin
a specific version such as `v3.0.0` (a tag). There are still things left to
figure out in how to manage releases and version. If you're interested, please
open an issue to discuss this.

In terms of security/reproductibility, the best solution is probably to pin the
version to an exact tag, and use dependabot to update it regularily.

## Note on the state of this action

This action is tested with 100% coverage. That said, coverage isn't all, and
there may be a lot of remaining issues :)

We accept Pull Requests (for bug fixes and previously-discussed features), and bug
reports. For feature requests, this might depend on how much time we have on our hands
at the moment, and how well you manage to sell it but don't get your hopes too high.

## Generic coverage

Initially, the first iteration of this action was using the more generic
`coverage.xml` (Cobertura) in order to be language independent. It was later
discovered that this format is very badly specified, as are mostly all coverage
formats. For this reason, we switched to the much more specialized `.coverage`
file that is only produced for Python projects (also, the action was rewritten
from the ground up). Because this would likely completely break compatibility,
a brand new action (this action) was created.

You can find the (unmaintained) language-generic version
[here](https://github.com/marketplace/actions/coverage-comment).


## Why do we need `relative_files = true` ?

Yes, I agree, this is annoying! The reason is that by default, coverage writes
the full path to the file in the `.coverage` file, but the path is most likely
different between the moment where your coverage is generated (in your workflow)
and the moment where the report is computed (in the action, which runs inside a
docker).

## I swear I saw something about a wiki somewhere?

A previous version of this action did things with the wiki. This is not the case
anymore.

## .coverage file generated on a non-unix file system

If your project needs to be built and tested on a non-unix os adding 

```
[paths]
source =
    */project/module
    *\project\module
```

to .coveragerc will help the action to find the covered files.

## Private repositories

This action is supposedly compatible with private repository. Just make sure
to use the svg badge directly, and not the `shields.io` URL.

## Upgrading from v2 to v3

- When upgrading, we change the location and format where the coverage
  data is kept. Pull request that have not been rebased may be displaying
  slightly wrong information.
