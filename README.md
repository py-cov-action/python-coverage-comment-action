# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/py-cov-action/python-coverage-comment-action/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                |    Stmts |     Miss |   Branch |   BrPart |    Cover |   Missing |
|------------------------------------ | -------: | -------: | -------: | -------: | -------: | --------: |
| coverage\_comment/\_\_init\_\_.py   |        0 |        0 |        0 |        0 |     100% |           |
| coverage\_comment/\_\_main\_\_.py   |        6 |        0 |        2 |        0 |     100% |           |
| coverage\_comment/activity.py       |       11 |        0 |        6 |        0 |     100% |           |
| coverage\_comment/badge.py          |       31 |        0 |       12 |        0 |     100% |           |
| coverage\_comment/comment\_file.py  |        4 |        0 |        0 |        0 |     100% |           |
| coverage\_comment/communication.py  |        8 |        0 |        0 |        0 |     100% |           |
| coverage\_comment/coverage.py       |      120 |        0 |       36 |        0 |     100% |           |
| coverage\_comment/diff\_grouper.py  |       12 |        0 |        4 |        0 |     100% |           |
| coverage\_comment/files.py          |       60 |        0 |        6 |        0 |     100% |           |
| coverage\_comment/github.py         |      107 |        0 |       26 |        0 |     100% |           |
| coverage\_comment/github\_client.py |       65 |        0 |       14 |        0 |     100% |           |
| coverage\_comment/groups.py         |       35 |        0 |       11 |        0 |     100% |           |
| coverage\_comment/log.py            |        5 |        0 |        0 |        0 |     100% |           |
| coverage\_comment/log\_utils.py     |        9 |        0 |        0 |        0 |     100% |           |
| coverage\_comment/main.py           |      130 |        0 |       24 |        0 |     100% |           |
| coverage\_comment/settings.py       |      119 |        0 |       56 |        0 |     100% |           |
| coverage\_comment/storage.py        |       70 |        0 |       10 |        0 |     100% |           |
| coverage\_comment/subprocess.py     |       26 |        0 |        0 |        0 |     100% |           |
| coverage\_comment/template.py       |      105 |        0 |       24 |        0 |     100% |           |
|                           **TOTAL** |  **923** |    **0** |  **231** |    **0** | **100%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/py-cov-action/python-coverage-comment-action/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/py-cov-action/python-coverage-comment-action/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/py-cov-action/python-coverage-comment-action/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/py-cov-action/python-coverage-comment-action/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fpy-cov-action%2Fpython-coverage-comment-action%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/py-cov-action/python-coverage-comment-action/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.