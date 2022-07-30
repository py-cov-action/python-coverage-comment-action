import pytest

from coverage_comment import subprocess


def test_run__ok():
    subprocess.run("echo", "yay") == "yay"


def test_run__kwargs():
    subprocess.run("pwd", cwd="/") == "/"


def test_run__error():
    with pytest.raises(subprocess.SubProcessError):
        subprocess.run("false")


@pytest.fixture
def environ(mocker):
    return mocker.patch("os.environ", {})


def test_git(mocker, environ):
    run = mocker.patch("coverage_comment.subprocess.run")
    git = subprocess.Git()
    git.cwd = "/tmp"
    environ["A"] = "B"

    git.clone("https://some_address.git", "--depth", "1", text=True)
    git.add("some_file")

    run.assert_has_calls(
        [
            mocker.call(
                "git",
                "clone",
                "https://some_address.git",
                "--depth",
                "1",
                cwd="/tmp",
                text=True,
                env=mocker.ANY,
            ),
            mocker.call("git", "add", "some_file", cwd="/tmp", env=mocker.ANY),
        ]
    )

    assert run.call_args_list[0].kwargs["env"]["A"] == "B"


def test_git_env(mocker, environ):
    run = mocker.patch("coverage_comment.subprocess.run")
    git = subprocess.Git()

    environ.update({"A": "B", "C": "D"})

    git.commit(env={"C": "E", "F": "G"})

    _, kwargs = run.call_args_list[0]

    env = run.call_args_list[0].kwargs["env"]
    assert env["A"] == "B"
    assert env["C"] == "E"
    assert env["F"] == "G"


def test_git__error(mocker):
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )
    git = subprocess.Git()

    with pytest.raises(subprocess.GitError):
        git.add("some_file")
