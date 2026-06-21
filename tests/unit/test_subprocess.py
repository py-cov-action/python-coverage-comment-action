from __future__ import annotations

import base64
import pathlib

import pytest

from coverage_comment import subprocess


def test_run__ok():
    assert subprocess.run("echo", "yay", path=pathlib.Path(".")).strip() == "yay"


def test_run__path():
    assert subprocess.run("pwd", path=pathlib.Path("/")).strip() == "/"


def test_run__kwargs():
    assert "A=B" in subprocess.run("env", env={"A": "B"}, path=pathlib.Path("."))


def test_run__error():
    with pytest.raises(subprocess.SubProcessError):
        subprocess.run("false", path=pathlib.Path("."))


def test_git(fake_process, monkeypatch):
    git = subprocess.Git()
    git.cwd = pathlib.Path("/tmp")
    monkeypatch.setenv("A", "B")

    clone_recorder = fake_process.register(
        ["git", "clone", "https://some_address.git", "--depth", "1"]
    )

    add_recorder = fake_process.register(["git", "add", "some_file"])

    fetch_recorder = fake_process.register(
        ["git", "--config-env=http.extraheader=GIT_EXTRA_HEADER", "fetch", "origin"],
    )
    basicauth = base64.b64encode(b"x-access-token:secret").decode()
    header = f"Authorization: basic {basicauth}"

    git.clone("https://some_address.git", "--depth", "1")
    git.add("some_file")
    git.fetch("origin", token="secret")

    assert clone_recorder.calls[0].kwargs["cwd"] == pathlib.Path("/tmp")
    assert clone_recorder.calls[0].kwargs["env"]["A"] == "B"
    assert add_recorder.calls[0].kwargs["cwd"] == pathlib.Path("/tmp")
    assert fetch_recorder.calls[0].kwargs["env"]["GIT_EXTRA_HEADER"] == header


def test_git_env(fake_process, monkeypatch):
    git = subprocess.Git()

    monkeypatch.setenv("A", "B")
    monkeypatch.setenv("C", "D")

    commit_recorder = fake_process.register(["git", "commit"])
    git.commit(env={"C": "E", "F": "G"})

    env = commit_recorder.calls[0].kwargs["env"]
    assert env["A"] == "B"
    assert env["C"] == "E"
    assert env["F"] == "G"


def test_git__error(fake_process):
    git = subprocess.Git()

    fake_process.register(["git", "add", "some_file"], returncode=1)

    with pytest.raises(subprocess.GitError):
        git.add("some_file")
