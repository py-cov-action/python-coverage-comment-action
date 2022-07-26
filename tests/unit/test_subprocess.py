import pytest

from coverage_comment import subprocess


def test_run__ok():
    subprocess.run("echo", "yay") == "yay"


def test_run__kwargs():
    subprocess.run("pwd", cwd="/") == "/"


def test_run__error():
    with pytest.raises(subprocess.SubProcessError):
        subprocess.run("false")


def test_git(mocker):
    run = mocker.patch("coverage_comment.subprocess.run")
    git = subprocess.Git()
    git.cwd = "/tmp"

    git.clone("https://some_address.git", "--depth", "1", text=True)
    git.add("some_file")

    assert run.call_args_list == [
        mocker.call(
            "git",
            "clone",
            "https://some_address.git",
            "--depth",
            "1",
            cwd="/tmp",
            text=True,
        ),
        mocker.call("git", "add", "some_file", cwd="/tmp"),
    ]


def test_git_env(mocker):
    run = mocker.patch("coverage_comment.subprocess.run")
    git = subprocess.Git()

    git.commit(env={"A": "B"})

    _, kwargs = run.call_args_list[0]

    assert kwargs["env"]["A"] == "B"
    assert "PATH" in kwargs["env"]


def test_git__error(mocker):
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )
    git = subprocess.Git()

    with pytest.raises(subprocess.GitError):
        git.add("some_file")
