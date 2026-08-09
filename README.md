# GitHub Action: Python Coverage Comment

[![Coverage badge](https://raw.githubusercontent.com/py-cov-action/python-coverage-comment-action/python-coverage-comment-action-data/badge.svg)](https://github.com/py-cov-action/python-coverage-comment-action/tree/python-coverage-comment-action-data)

## Presentation

This action analyses the coverage data produced by the Python
[coverage](https://coverage.readthedocs.io) library and produces:

- A badge to display on your README
- A comment in the pull requests detailing how the PR impacts the coverage:
  - Old and new coverage rates per file and total
  - Coverage of new lines per file and total
- (optional) Annotations on lines missing coverage displayed in the PR directly
- A [Job Summary](https://github.blog/2022-05-09-supercharging-github-actions-with-job-summaries/)
- A browsable folder containing:
  - The coverage summary
  - The full HTML coverage in a browsable format (not available for private repos)

All of this runs on top of GitHub Action without extra-charges and runs on the GitHub
infrastructure: your code isn't sent anywhere out of GitHub.

[See this action in action](https://github.com/py-cov-action/python-coverage-comment-action-v3-example)

## What does it do?

This action operates on an already generated `.coverage` file from
[coverage](https://coverage.readthedocs.io).

It has two main modes of operation:

### PR mode

On PRs, it will analyze the `.coverage` file, and produce a comment that
will be posted to the PR. If a comment had already previously be written,
it will be updated. The comment contains information on the evolution
of coverage rate attributed to this PR, as well as the rate of coverage
for lines that this PR introduces. There's also a small analysis for each
file in a collapsed block.

This comment will also be output as a [job summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary).

See [an example](https://github.com/py-cov-action/python-coverage-comment-action-v3-example/pull/2#issuecomment-1244431724).

### Default branch mode

On repository's default branch, it will extract the coverage rate and create
files that will be stored on a dedicated independent branch in your repository.

These files include:

- a `svg` badge to include in your README
- a `json` file that can be used by [shields.io](https://shields.io) if your
  repository is public to customize the look of your badge
- Another `json` file used internally by the action to report on coverage
  evolution (does a PR make the coverage go up or down?)
- A short file-by-file coverage report embedded directly into the branch's README. An excerpt from this is also output directly as a [job summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary).
- The full HTML coverage report and links to make this report browsable

See [an example](https://github.com/py-cov-action/python-coverage-comment-action-v3-example)

### Determining the mode

By default, the action will attempt to pick the appropriate mode based on the
current branch, whether or not it's in a pull request, and if that pull request
is open or closed. This frequently results in the correct action taking place,
but is only a heuristic. If you need more precise control, you should specify
the `ACTIVITY` parameter to directly choose the mode. It may be one of:

- `process_pr`, to select [PR mode](#pr-mode)
- `save_coverage_data_files`, to select [Default branch mode](#default-branch-mode)
- `post_comment`, to select [Commenting on the PR on the `push` event](#commenting-on-the-pr-on-the-push-event)

Combining this with [Github's Expressions]
(https://docs.github.com/en/actions/reference/workflows-and-actions/expressions) you can
build out the the custom handling needed. For example:

```yaml title="docs/examples/activity/any-push.yml" lines=31-36
      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ github.token }}
          ACTIVITY: "${{ github.event_name == 'push' && 'save_coverage_data_files' || 'process_pr' }}"
```

Or, to only save the coverage data when pushing to the default branch:

```yaml title="docs/examples/activity/default-branch.yml" lines=31-36
      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ github.token }}
          ACTIVITY: "${{ (github.event_name == 'push' && github.ref_name == 'main') && 'save_coverage_data_files' || 'process_pr' }}"
```

## Usage

### Setup

Please ensure that your `.coverage` file(s) is created with the option
[`relative_files = true`](https://coverage.readthedocs.io/en/latest/config.html#config-run-relative-files).

Please ensure that the branch `python-coverage-comment-action-data` is not
protected (there's no reason that it would be the case, except if you have very
specific wildcard rules). If it is, either adjust your rules, or set the
`COVERAGE_DATA_BRANCH` parameter as described below. GitHub Actions will create
this branch with initial data at the first run if it doesn't exist, and will
independently commit to that branch after each commit to your default branch.

### Badge

Once the action has run on your default branch, all the details for how to integrate the
badge to your Readme will be displayed in:

- The Readme of the `python-coverage-comment-action-data` branch
- The text output of the workflow run

### Basic usage

The following snippet is targeted for cases where you expect PRs from
users that don't have write access to the repository. Posting the comment
is done in 2 steps:

1. Checkout the repository and generate the comment to be posted. For security
   reasons, we don't want to give permissions to a workflow that checks out
   untrusted code
2. From a trusted workflow, publish the comment on the PR

The write permissions in the `CI` workflow below are intentional. They are
used when the PR is trusted enough, usually because it comes from the same
repository, for this workflow to publish or update the comment directly.
When that happens, the second workflow can be skipped.
For `pull_request` runs coming from forks, which are untrusted by default,
GitHub downgrades requested write permissions to read-only unless the
repository is explicitly configured to send write tokens to workflows from
pull requests. In other words, these settings do not grant write access to
untrusted code.

```yaml title="docs/examples/basic-usage/ci.yml"
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches:
      - "main"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    permissions:
      # Forked pull_request runs are downgraded to read-only by GitHub, so
      # these do not grant write access to untrusted code.
      pull-requests: write # Publish/update the coverage comment on trusted PRs
      contents: write # Push the coverage data to the data branch
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Install everything, run the tests, produce the .coverage file
        run: make test # This is the part where you put your own test command

      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ github.token }}

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        if: steps.coverage_comment.outputs.COMMENT_FILE_WRITTEN == 'true'
        with:
          # If you use a different name, update COMMENT_ARTIFACT_NAME accordingly
          name: python-coverage-comment-action
          # If you use a different name, update COMMENT_FILENAME accordingly
          path: python-coverage-comment-action.txt
```

```yaml title="docs/examples/basic-usage/coverage.yml"
# .github/workflows/coverage.yml
name: Post coverage comment

on:  # zizmor: ignore[dangerous-triggers] We're using workflow_run to post a coverage comment on external PRs. This is safe because we don't checkout the external code or interact with the external code in any way but extracting an artifact containing the comment to post, and post it.
  workflow_run:
    workflows: ["CI"]
    types:
      - completed

concurrency:
  # Group by the PR's branch, so that runs for different PRs don't cancel
  # each other. `github.ref` is always the default branch on `workflow_run`.
  group: ${{ github.workflow }}-${{ github.event.workflow_run.head_branch }}
  cancel-in-progress: true

permissions: {}

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    if: github.event.workflow_run.event == 'pull_request' && github.event.workflow_run.conclusion == 'success'
    permissions:
      pull-requests: write # Post the comment, and edit it on later runs
      actions: read # Download the comment artifact from the triggering CI run
      contents: read
    steps:
      # DO NOT run actions/checkout here, for security reasons
      # For details, refer to https://securitylab.github.com/research/github-actions-preventing-pwn-requests/
      - name: Post comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_PR_RUN_ID: ${{ github.event.workflow_run.id }}
          # Update those if you changed the default values:
          # COMMENT_ARTIFACT_NAME: python-coverage-comment-action
          # COMMENT_FILENAME: python-coverage-comment-action.txt
```

### Basic usage without external contributors

If you don't expect external contributors, you don't need all the shenanigans
with the artifacts and the 2nd workflow. This is likely to be the most straightforward
way to configure it for private repositories. It might look like this:

```yaml title="docs/examples/no-external-contributors/ci.yml"
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches:
      - "main"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write # Publish the coverage comment, and edit it on later runs
      contents: write # Push the coverage data to the data branch
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Install everything, run the tests, produce the .coverage file
        run: make test # This is the part where you put your own test command

      - name: Coverage comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ github.token }}
```

### Using with merge queues

If you are using merge queues, you will need to add the `merge_group` event to your workflow's `on:` clause. This will ensure that the action is triggered when a pull request is added to the merge queue.

You will need to ensure the action is run only _after_ all the actual merge checks have run. Otherwise, coverage data will be incorrectly updated.

For instance

```yaml title="docs/examples/merge-queue/ci.yml"
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  merge_group:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  # Never cancel a merge_group run: that would dequeue the pull request.
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

permissions: {}

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write # Publish the coverage comment, and edit it on later runs
      contents: write # Push the coverage data to the data branch
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Install everything, run the tests, produce the .coverage file
        run: make test # This is the part where you put your own test command

      - name: Coverage comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ github.token }}
```

### Merging multiple coverage reports

In case you have a job matrix and you want the report to be on the global
coverage, you can configure your `ci.yml` like this (`coverage.yml` remains the
same)

```yaml title="docs/examples/matrix/ci.yml"
name: CI

on:
  pull_request:
  push:
    branches:
      - "master"
    tags:
      - "*"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

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
    permissions:
      contents: read # Checkout the repository

    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Python
        id: setup-python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: ${{ matrix.python_version }}

      - name: Install everything, run the tests, produce a .coverage.xxx file
        run: make test # This is the part where you put your own test command
        env:
          COVERAGE_FILE: ".coverage.${{ matrix.python_version }}"
          # The file name prefix must be ".coverage." for "coverage combine"
          # enabled by "MERGE_COVERAGE_FILES: true" to work. A "subprocess"
          # error with the message "No data to combine" will be triggered if
          # this prefix is not used.

      - name: Store coverage file
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: coverage-${{ matrix.python_version }}
          path: .coverage.${{ matrix.python_version }}
          # By default hidden files/folders (i.e. starting with .) are ignored.
          # You may prefer (for security reasons) not setting this and instead
          # set COVERAGE_FILE above to not start with a `.`, but you cannot
          # use "MERGE_COVERAGE_FILES: true" later on and need to manually
          # combine the coverage file using "pipx run coverage combine"
          include-hidden-files: true

  coverage:
    name: Coverage
    runs-on: ubuntu-latest
    needs: build
    permissions:
      pull-requests: write # Publish the coverage comment, and edit it on later runs
      contents: write # Push the coverage data to the data branch
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - uses: actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c # v8.0.1
        id: download
        with:
          pattern: coverage-*
          merge-multiple: true

      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MERGE_COVERAGE_FILES: true

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        if: steps.coverage_comment.outputs.COMMENT_FILE_WRITTEN == 'true'
        with:
          name: python-coverage-comment-action
          path: python-coverage-comment-action.txt
```

### Outputs

The action makes available some data for downstream processing.

| Name           | Description                                                                                         |
| -------------- | --------------------------------------------------------------------------------------------------- |
| `activity_run` | The type of activity that was run. One of `process_pr`, `post_comment`, `save_coverage_data_files`. |

All the following outputs are only available when running in PR mode.

| Name                             | Description                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------- |
| `comment_file_written`           | A boolean indicating whether a comment file was written to `COMMENT_FILENAME` or not. |
| `new_covered_lines`              | The number of covered lines in the pull request.                                      |
| `new_num_statements`             | The number of statements in the pull request.                                         |
| `new_percent_covered`            | The coverage percentage of the pull request.                                          |
| `new_missing_lines`              | The number of lines with missing coverage in the pull request.                        |
| `new_excluded_lines`             | The number of excluded lines in the pull request.                                     |
| `new_num_branches`               | The number of branches in the pull request.                                           |
| `new_num_partial_branches`       | The number of partial branches in the pull request.                                   |
| `new_covered_branches`           | The number of covered branches in the pull request.                                   |
| `new_missing_branches`           | The number of branches with missing coverage in the pull request.                     |
| `reference_covered_lines`        | The number of covered lines in the base branch.                                       |
| `reference_num_statements`       | The number of statements in the base branch.                                          |
| `reference_percent_covered`      | The coverage percentage of the base branch.                                           |
| `reference_missing_lines`        | The number of lines with missing coverage in the base branch.                         |
| `reference_excluded_lines`       | The number of excluded lines in the base branch.                                      |
| `reference_num_branches`         | The number of branches in the base branch.                                            |
| `reference_num_partial_branches` | The number of partial branches in the base branch.                                    |
| `reference_covered_branches`     | The number of covered branches in the base branch.                                    |
| `reference_missing_branches`     | The number of branches with missing coverage in the base branch.                      |
| `diff_total_num_lines`           | The total number of lines in the diff.                                                |
| `diff_total_num_violations`      | The total number of lines with missing coverage in the diff.                          |
| `diff_total_percent_covered`     | The coverage percentage of the diff.                                                  |
| `diff_num_changed_lines`         | The number of changed lines in the diff.                                              |

Usage may look like this

```yaml title="docs/examples/enforce-coverage/ci.yml" lines=31-39
      - name: Coverage comment
        id: coverage_comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ github.token }}

      - name: Enforce coverage
        if: ${{ steps.coverage_comment.outputs.new_percent_covered < steps.coverage_comment.outputs.reference_percent_covered }}
        run: echo "Coverage decreased." && exit 1
```

### All options

```yaml
- name: Display coverage
  id: coverage_comment
  uses: py-cov-action/python-coverage-comment-action@sha1  # vx.y.z
  with:
    GITHUB_TOKEN: ${{ github.token }}

    # Change this in case you use GitHub Entreprise with a different API endpoint
    GITHUB_BASE_URL: https://api.github.com

    # Only necessary in the "workflow_run" workflow.
    GITHUB_PR_RUN_ID: ${{ inputs.GITHUB_PR_RUN_ID }}

    # Use this in case the folder to run coverage commands from is not the
    # top level of your repository
    COVERAGE_PATH: my_project/

    # If the coverage percentage is above or equal to this value, the badge will be green.
    MINIMUM_GREEN: 100

    # Same with orange. Below is red.
    MINIMUM_ORANGE: 70

    # Maximum number of files to display in the comment. If there are more
    # files than this number, they will only appear in the workflow summary.
    # The selected files are the ones with the most new uncovered lines. The
    # closer this number gets to 35, the higher the risk that it reaches
    # GitHub's maximum comment size limit of 65536 characters. If you want
    # more files, you may need to use a custom comment template (see below).
    # (Feel free to open an issue.)
    MAX_FILES_IN_COMMENT: 25

    # If true, will run `coverage combine` before reading the `.coverage` file.
    MERGE_COVERAGE_FILES: false

    # If true, will create an annotation on every line with missing coverage on a pull request.
    ANNOTATE_MISSING_LINES: false

    # Only needed if ANNOTATE_MISSING_LINES is set to true. This parameter allows you to choose between
    # notice, warning and error as annotation type. For more information look here:
    # https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-notice-message
    ANNOTATION_TYPE: warning

    # If true, link the HTML coverage report to your GitHub Pages site, which
    # assumes you serve COVERAGE_DATA_BRANCH from there. If false, the link
    # goes through htmlpreview.github.io instead (or, on GitHub Enterprise,
    # straight to the file in the repository).
    USE_GH_PAGES_HTML_URL: false

    # Name of the artifact in which the body of the comment to post on the PR is stored.
    # You typically don't have to change this unless you're already using this name for something else.
    COMMENT_ARTIFACT_NAME: python-coverage-comment-action

    # Name of the file in which the body of the comment to post on the PR is stored.
    # In monorepo setting, see SUBPROJECT_ID.
    COMMENT_FILENAME: python-coverage-comment-action.txt

    # This setting is only necessary if you plan to run the action multiple times
    # in the same repository. It will be appended to the value of all the
    # settings that need to be unique, so as for the action to avoid mixing
    # up results of multiple runs.
    # Affects `COMMENT_FILENAME`, `COVERAGE_DATA_BRANCH`.
    # Ideally, use dashes (`-`) rather than underscrores (`_`) to split words,
    # for consistency
    SUBPROJECT_ID: null / "lib-name"

    # An alternative template for the comment for pull requests. See details below.
    COMMENT_TEMPLATE: The coverage rate is `{{ coverage.info.percent_covered | pct }}`{{ marker }}

    # Name of the branch in which coverage data will be stored on the repository.
    # Default is 'python-coverage-comment-action-data'. Please make sure that this
    # branch is not protected.
    # In monorepo setting, see SUBPROJECT_ID.
    COVERAGE_DATA_BRANCH: python-coverage-comment-action-data

    # Deprecated, see https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/enabling-debug-logging
    VERBOSE: false

    # The specific activity that should be taken on this event, see
    # [Determining the mode](#determining-the-mode) above.
    ACTIVITY: ""
```

### Commenting on the PR on the `push` event

This action's PR comments with coverage reports is designed to work when
running on the `pull_request` events. That being said, if your CI is running on
feature branches on the `push` events and not on the `pull_request` events, we
partly support a mode where the action can comment on the PR when running on
the `push` events instead. This is most likely only useful for setups not
accepting external PRs and you will not have the best user experience.
If that's something you need to do, please have a look at [this issue](https://github.com/py-cov-action/python-coverage-comment-action/issues/234).

### Updating the coverage information on the `pull_request/closed` event

Usually, the coverage data for the repository is updated on `push` events to the default
branch, but it can also work to do it on `pull_request/closed` events, especially if
you require all changes to go through a pull request.

In this case, your workflow's `on:` clause should look like this:

```yaml
on:
  pull_request:
    # opened, synchronize, reopened are the default value
    # closed will trigger when the PR is closed (merged or not)
    types: [opened, synchronize, reopened, closed]

jobs:
  build:
    # Optional: if you want to avoid doing the whole build on PRs closed without
    # merging, add the following clause. Note that this action won't update the
    # coverage data even if you don't specify this (it will raise an error instead),
    # but it can help you avoid a useless build.
    if: github.event.action != "closed" || github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    ...
```

> [!TIP]
> The action will also save repository coverage data on `schedule` workflows.

## Overriding the template

By default, comments are generated from a
[Jinja](https://jinja.palletsprojects.com) template that you can read
[here](https://github.com/py-cov-action/python-coverage-comment-action/blob/main/coverage_comment/template_files/comment.md.j2).

If you want to change this template, you can set `COMMENT_TEMPLATE`. This is
an advanced usage, so you're likely to run into more road bumps.

You will need to follow some rules for your template to be valid:

- Your template needs to be syntactically correct with Jinja2 rules
- You may define a new template from scratch, but in this case you are required
  to include `{{ marker }}`, which includes an HTML comment (invisible on
  GitHub) that the action uses to identify its own comments.
- If you'd rather want to change parts of the default template, you can do so
  by starting your comment with `{% extends "base" %}`, and then override the
  blocks (`{% block foo %}`) that you wish to change. If you're unsure how it
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

## Monorepo setting

In case you want to use the action multiple times with different parts of your
source (so you have multiple codebases into a single repo), you'll
need to use SUBPROJECT_ID with a different value for each launch. You may
still use the same step for storing all files as artifacts. You'll end up with
a different comment for each launch. Feel free to use the `COMMENT_TEMPLATE` if
you want each comment to clearly state what it relates to.

```yaml title="docs/examples/monorepo/ci.yml"
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches:
      - "main"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions: {}

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write # Publish the coverage comment, and edit it on later runs
      contents: write # Push the coverage data to the data branch
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Test project 1
        run: make -C project_1 test

      - name: Test project 2
        run: make -C project_2 test

      - name: Coverage comment (project 1)
        id: coverage_comment_1
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          COVERAGE_PATH: project_1
          SUBPROJECT_ID: project-1
          GITHUB_TOKEN: ${{ github.token }}

      - name: Coverage comment (project 2)
        id: coverage_comment_2
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          COVERAGE_PATH: project_2/src
          SUBPROJECT_ID: project-2
          GITHUB_TOKEN: ${{ github.token }}

      - name: Store Pull Request comment to be posted
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        if: steps.coverage_comment_1.outputs.COMMENT_FILE_WRITTEN == 'true' || steps.coverage_comment_2.outputs.COMMENT_FILE_WRITTEN == 'true'
        with:
          name: python-coverage-comment-action
          # Note the star
          path: python-coverage-comment-action*.txt
```

```yaml title="docs/examples/monorepo/coverage.yml"
# .github/workflows/coverage.yml
name: Post coverage comment

on:  # zizmor: ignore[dangerous-triggers] We're using workflow_run to post a coverage comment on external PRs. This is safe because we don't checkout the external code or interact with the external code in any way but extracting an artifact containing the comment to post, and post it.
  workflow_run:
    workflows: ["CI"]
    types:
      - completed

concurrency:
  # Group by the PR's branch, so that runs for different PRs don't cancel
  # each other. `github.ref` is always the default branch on `workflow_run`.
  group: ${{ github.workflow }}-${{ github.event.workflow_run.head_branch }}
  cancel-in-progress: true

permissions: {}

jobs:
  test:
    name: Run tests & display coverage
    runs-on: ubuntu-latest
    if: github.event.workflow_run.event == 'pull_request' && github.event.workflow_run.conclusion == 'success'
    permissions:
      pull-requests: write # Post the comment, and edit it on later runs
      actions: read # Download the comment artifact from the triggering CI run
      contents: read
    steps:
      - name: Post comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_PR_RUN_ID: ${{ github.event.workflow_run.id }}
          SUBPROJECT_ID: project-1
          COVERAGE_PATH: project_1

      - name: Post comment
        uses: py-cov-action/python-coverage-comment-action@5d8df5979747514c914e1c5a12335a7cf9a2745f # v4.1
        with:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_PR_RUN_ID: ${{ github.event.workflow_run.id }}
          SUBPROJECT_ID: project-2
          COVERAGE_PATH: project_2/src
```

# Other topics

## Pinning

We used to rewrite tags following the GitHub practices (and provide `@v3`, `@v3.1`, etc.).
The new accepted good practice is release immutability, so that's what we do.
Using standard tools like [Zizmor](https://docs.zizmor.sh/) or
[Pinact](https://github.com/suzuki-shunsuke/pinact), you're expected to pin to a
given commit sha, and use a comment to indicate the corresponding exact version.
This is format is understood and followed by dependabot/renovate.

## Persisted credentials

Starting with **v4.1**, the action hands the `GITHUB_TOKEN` you pass it directly to
`git` for every network operation (fetching and pushing the coverage data branch).
It never reads the credentials that `actions/checkout` writes to `.git/config`, so
you can — and should — check out with `persist-credentials: false`.

This keeps a write-scoped token out of `.git/config` on the runner, where any later
step in the job would be able to read it. It's what
[Zizmor](https://docs.zizmor.sh/) reports as
[`artipacked`](https://docs.zizmor.sh/audits/#artipacked).

This only concerns *persisted* credentials. The job that stores the coverage data
still needs `contents: write`, because that's the permission carried by the
`GITHUB_TOKEN` the action uses.

If you're pinned to a release older than v4.1 (that is, any `v3.x` release), the
action still relies on the credentials stored by `actions/checkout`. Keep
`persist-credentials: true` until you upgrade.

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

## .coverage file generated on a Windows file system

If your project's coverage was built on Windows, you may get an error like:

```
CoverageWarning: Couldn't parse 'yourproject\__init__.py': No source for code: 'yourproject\__init__.py'. (couldnt-parse)
```

This is likely due to coverage being confused with the coverage being computed with `\` but read with `/`. You can most probably fix it with the following in your [coverage configuration](https://coverage.readthedocs.io/en/latest/config.html):

```
[paths]
source =
    */project/module
    *\project\module
```

## Private repositories

This action is supposedly compatible with private repository. Just make sure
to use the svg badge directly, and not the `shields.io` URL.

## Github Enterprise (GHE) Support

This action should be compatible with GitHub Enterprise. Just make sure to set the `GITHUB_BASE_URL` input to your GHE URL.

## Upgrading from v2 to v3

When upgrading, we change the location and format where the coverage
data is kept. Pull request that have not been re-based may be displaying
slightly wrong information.

## New comment format starting with 3.19

Starting with 3.19, the format for the Pull Request changed to a table
with badges. We've been iterating a lot on the new format.
It's perfectly ok if you preferred the old format. In that case, see
#335 for instructions on how to emulate the old format using
`COMMENT_TEMPLATE`.

## Zizmor

[Zizmor](https://docs.zizmor.sh/) is an awesome security-minded linter for GitHub
Actions. You should use it. If you use it with this action, the way this action is
setup, it will complain about `workflow_run` unless you keep the `zizmor:
ignore[dangerous-triggers]`. Zizmor is right, `workflow_run` is dangerous if you don't
follow the [good
practice](https://securitylab.github.com/research/github-actions-preventing-pwn-requests/).

As far as we know, though, this action is safe because we're very purposefully **not**
doing things that make `workflow_run` dangerous such as checking out unsafe code or
interpolating unsafe strings inside bash scripts. As far as we know, it's acceptable to
silence Zizmor here. Of course, if you think you've found a flaw in the reasoning, let
us know.
