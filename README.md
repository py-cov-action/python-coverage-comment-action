# GitHub Action: Python Coverage Comment

![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/wiki/ewjoachim/python-coverage-comment-action/python-coverage-comment-action-badge.json)

## Disclaimer

You're looking at the v2 version of this GitHub Action. The
[v3+](https://github.com/ewjoachim/python-coverage-comment-action) adds
significant improvements, such as not needing the wiki anymore, and working on
private repos. You're free to stay on v2, but we'll most likely not offer any
kind of updates to it.

## Presentation

Publish diff coverage report as PR comment, and create a coverage badge to
display on the readme.

See example at: https://github.com/ewjoachim/python-coverage-comment-action-example/tree/v2

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

See: https://github.com/ewjoachim/python-coverage-comment-action-example/pull/2#issuecomment-1003646299

### Default branch mode

On repository's default branch, it will extract the coverage
rate and create a small JSON file that will be stored on the repository's wiki.
This file will then have a stable URL, which means that if your repository is public,
you can create a [shields.io](https://shields.io/endpoint) badge from it.

See: https://github.com/ewjoachim/python-coverage-comment-action-example/tree/v2

## Usage

### Setup

Please ensure that the **repository wiki has been initialized** with at least a
single page created. Once it's done, you can disable the wiki for the
repository.

Also, please ensure that your `.coverage` file(s) is created with the option
[`relative_files = true`](https://coverage.readthedocs.io/en/6.2/config.html#config-run-relative-files).

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
    steps:
      - uses: actions/checkout@v2

      - name: Install everything, run the tests, produce the .coverage file
        run: make test  # This is the part where you put your own test command

      - name: Coverage comment
        id: coverage_comment
        uses: ewjoachim/python-coverage-comment-action@v2
        with:
          GITHUB_TOKEN: ${{ github.token }}

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@v2
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
    steps:
      # DO NOT run actions/checkout@v2 here, for securitity reasons
      # For details, refer to https://securitylab.github.com/research/github-actions-preventing-pwn-requests/
      - name: Post comment
        uses: ewjoachim/python-coverage-comment-action@v2
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
      - uses: actions/checkout@v2

      - name: Set up Python
        id: setup-python
        uses: actions/setup-python@v2
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
        uses: actions/upload-artifact@v2
        with:
          name: coverage
          path: .coverage.${{ matrix.python_version }}

  coverage:
    name: Coverage
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v2

      - uses: actions/download-artifact@v2
        id: download
        with:
          name: 'coverage'

      - name: Coverage comment
        id: coverage_comment
        uses: ewjoachim/python-coverage-comment-action@v2
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MERGE_COVERAGE_FILES: true

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@v2
        if: steps.coverage_comment.outputs.COMMENT_FILE_WRITTEN == 'true'
        with:
          name: python-coverage-comment-action
          path: python-coverage-comment-action.txt

```

### All options
```yaml
- name: Display coverage
  id: coverage_comment
  uses: ewjoachim/python-coverage-comment-action@v2
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

    # If true, produces more output. Useful for debugging.
    VERBOSE: false

    # Name of the json file containing badge informations stored in the repo wiki.
    # You typically don't have to change this unless you're already using this name for something else.
    BADGE_FILENAME: python-coverage-comment-action-badge.json

    # Name of the artifact in which the body of the comment to post on the PR is stored.
    # You typically don't have to change this unless you're already using this name for something else.
    COMMENT_ARTIFACT_NAME: python-coverage-comment-action

    # Name of the file in which the body of the comment to post on the PR is stored.
    # You typically don't have to change this unless you're already using this name for something else.
    COMMENT_FILENAME: python-coverage-comment-action.txt

    # An alternative template for the comment for pull requests. See details below.
    COMMENT_TEMPLATE: The coverage rate is `{{ coverage.info.percent_covered | pct }}`{{ marker }}
```

## Overriding the template

By default, comments are generated from a
[Jinja](https://jinja.palletsprojects.com) template that you can read
[here](https://github.com/ewjoachim/python-coverage-comment-action/blob/v2/coverage_comment/default.md.j2).

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
  [here](https://github.com/ewjoachim/python-coverage-comment-action/blob/v2/coverage_comment/template.py).
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
On the examples above, the version was set to `v2` (a branch). You can also pin
a specific version such as `v2.0.0` (a tag). There are still things left to
figure out in how to manage releases and version. If you're interested, please
open an issue to discuss this.

In terms of security/reproductibility, the best solution is probably to pin the
version to an exact tag, and use dependabot to update it regularily.

## Note on the state of this action

This action is tested with 100% coverage. That said, coverage isn't all, and
there may be a lot of remaining issues :)

I'm not prioritizing maintenance on this action, but I'll do my best to assist
questions and PRs. Feature requests are most likely not to be taken but if
you're ready to do a PR, I'll gladly work with you.

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
