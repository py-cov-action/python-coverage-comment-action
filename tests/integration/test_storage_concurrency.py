from __future__ import annotations

import dataclasses
import os
import pathlib
import subprocess as process
from collections.abc import Callable
from typing import Any

import pytest

from coverage_comment import files, storage, subprocess

BRANCH = "coverage-data"


def git_at(path: pathlib.Path, *args: str) -> str:
    git = subprocess.Git()
    git.cwd = path
    return git(*args).strip()


class PublishingGit(subprocess.Git):
    def __init__(self, path: pathlib.Path):
        self.cwd = path
        self.before_push: Callable[[int], None] | None = None
        self.after_rejection: Callable[[], None] | None = None
        self.attempts = 0
        self.publications: list[str] = []
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, *args: str, **kwargs: Any) -> str:
        self.commands.append(args)
        if args[0] == "push":
            self.attempts += 1
            self.publications.append(self.rev_parse("HEAD").strip())
            if self.before_push is not None:
                self.before_push(self.attempts)
            try:
                return super().__call__(*args, **kwargs)
            except subprocess.GitError:
                if self.after_rejection is not None:
                    self.after_rejection()
                raise
        return super().__call__(*args, **kwargs)


@dataclasses.dataclass
class Sandbox:
    remote: pathlib.Path
    winner: pathlib.Path
    actor: PublishingGit
    initial: str | None
    commits: list[str] = dataclasses.field(default_factory=list)

    def compete(self, contents: dict[str, str]):
        if self.initial is None and not self.commits:
            git_at(self.winner, "switch", "--orphan", BRANCH)
        else:
            git_at(self.winner, "fetch", "origin", BRANCH)
            git_at(self.winner, "switch", BRANCH)
            git_at(self.winner, "reset", "--hard", "FETCH_HEAD")
        for name, value in contents.items():
            path = self.winner / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
            git_at(self.winner, "add", name)
        git_at(self.winner, "commit", "-m", f"competing report {len(self.commits)}")
        self.commits.append(git_at(self.winner, "rev-parse", "HEAD"))
        git_at(self.winner, "push", "origin", BRANCH)

    def read(self, path: str, revision: str = BRANCH) -> str:
        return git_at(self.remote, "show", f"{revision}:{path}")

    def assert_history(self):
        for revision in [self.actor.publications[0], *self.commits]:
            git_at(self.remote, "merge-base", "--is-ancestor", revision, BRANCH)
        assert not any(
            "--force" in command or "--force-with-lease" in command
            for command in self.actor.commands
        )

    def collide_once(self, contents: dict[str, str]):
        def advance(attempt: int):
            if attempt == 1:
                self.compete(contents)

        self.actor.before_push = advance


@pytest.fixture
def sandbox_factory(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.hooksPath")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", os.devnull)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    for key, value in storage.COMMIT_ENVIRONMENT.items():
        monkeypatch.setenv(key, value)

    def create(*, existing=True, detached=False):
        remote = tmp_path / "remote.git"
        seed = tmp_path / "seed"
        winner = tmp_path / "winner"
        pending = tmp_path / "pending"
        git_at(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
        git_at(tmp_path, "clone", str(remote), str(seed))
        (seed / "source.txt").write_text("synthetic source\n")
        git_at(seed, "add", "source.txt")
        git_at(seed, "commit", "-m", "seed source")
        git_at(seed, "push", "origin", "main")
        initial = None
        if existing:
            git_at(seed, "switch", "--orphan", BRANCH)
            (seed / "data.json").write_text('{"writer":"seed"}\n')
            (seed / "htmlcov").mkdir()
            (seed / "htmlcov/old.html").write_text("old report\n")
            git_at(seed, "add", ".")
            git_at(seed, "commit", "-m", "seed report")
            git_at(seed, "push", "origin", BRANCH)
            initial = git_at(remote, "rev-parse", BRANCH)
        git_at(tmp_path, "clone", str(remote), str(winner))
        git_at(tmp_path, "clone", str(remote), str(pending))
        if detached:
            git_at(pending, "switch", "--detach", "HEAD")
        monkeypatch.chdir(pending)
        return Sandbox(remote, winner, PublishingGit(pending), initial)

    return create


def publish(sandbox: Sandbox, contents: dict[str, str]):
    storage.commit_operations(
        [
            files.WriteFile(pathlib.Path(name), value)
            for name, value in contents.items()
        ],
        git=sandbox.actor,
        branch=BRANCH,
        token="synthetic",
    )


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("detached", [False, True])
def test_independent_reports_and_both_histories_survive(
    sandbox_factory, existing, detached
):
    sandbox = sandbox_factory(existing=existing, detached=detached)
    sandbox.collide_once({"first.json": '{"writer":"first"}\n'})
    publish(sandbox, {"second.json": '{"writer":"second"}\n'})
    assert sandbox.actor.attempts == 2
    assert sandbox.read("first.json") == '{"writer":"first"}'
    assert sandbox.read("second.json") == '{"writer":"second"}'
    assert sandbox.actor.branch("--show-current").strip() == (
        "" if detached else "main"
    )
    sandbox.assert_history()


@pytest.mark.parametrize(
    "pending,competing",
    [('{"a":1,"b":0}', '{"a":0,"b":2}'), ('{"same":true}', '{"same":true}')],
)
def test_same_path_uses_one_whole_snapshot_and_keeps_previous_reports(
    sandbox_factory, pending, competing
):
    sandbox = sandbox_factory()
    sandbox.collide_once({"data.json": competing + "\n"})
    publish(sandbox, {"data.json": pending + "\n"})
    assert sandbox.actor.attempts == 2
    assert sandbox.read("data.json") == pending
    assert sandbox.read("data.json", sandbox.commits[0]) == competing
    assert sandbox.read("data.json", sandbox.actor.publications[0]) == pending
    sandbox.assert_history()


@pytest.mark.parametrize("empty", [False, True])
def test_directory_snapshot_removes_remote_extras_without_replaying_move(
    sandbox_factory, tmp_path, empty
):
    sandbox = sandbox_factory()
    source = tmp_path / "generated"
    source.mkdir()
    if not empty:
        (source / "index.html").write_text("pending report\n")
    sandbox.collide_once(
        {
            "htmlcov/obsolete.html": "competing detail\n",
            "independent.json": "independent\n",
        }
    )
    storage.commit_operations(
        [files.ReplaceDir(source, pathlib.Path("htmlcov"))],
        git=sandbox.actor,
        branch=BRANCH,
        token="synthetic",
    )
    assert not source.exists()
    assert sandbox.read("independent.json") == "independent"
    assert (
        git_at(
            sandbox.remote,
            "ls-tree",
            "-r",
            "--name-only",
            BRANCH,
            "htmlcov/obsolete.html",
        )
        == ""
    )
    if empty:
        assert git_at(sandbox.remote, "ls-tree", "--name-only", BRANCH, "htmlcov") == ""
    else:
        assert sandbox.read("htmlcov/index.html") == "pending report"
    sandbox.assert_history()


@pytest.mark.parametrize("changed", [False, True])
def test_snapshot_already_in_remote_history(sandbox_factory, changed):
    sandbox = sandbox_factory()

    def advance(attempt: int):
        if attempt != 1:
            return
        git_at(
            sandbox.winner,
            "fetch",
            str(sandbox.actor.cwd),
            sandbox.actor.publications[0],
        )
        git_at(sandbox.winner, "switch", BRANCH)
        git_at(sandbox.winner, "reset", "--hard", "FETCH_HEAD")
        (sandbox.winner / "independent.json").write_text("independent\n")
        if changed:
            (sandbox.winner / "data.json").write_text("competing\n")
        git_at(sandbox.winner, "add", ".")
        git_at(sandbox.winner, "commit", "-m", "advance stored publication")
        sandbox.commits.append(git_at(sandbox.winner, "rev-parse", "HEAD"))
        git_at(sandbox.winner, "push", "origin", BRANCH)

    sandbox.actor.before_push = advance
    publish(sandbox, {"data.json": "pending\n"})
    assert sandbox.actor.attempts == (2 if changed else 1)
    assert sandbox.read("data.json") == "pending"
    assert sandbox.read("independent.json") == "independent"
    sandbox.assert_history()


@pytest.mark.parametrize("collisions", [2, 3])
def test_bounded_retries_keep_exhaustion_visible(sandbox_factory, collisions, caplog):
    sandbox = sandbox_factory()
    caplog.set_level("INFO", logger="coverage_comment")

    def advance(attempt: int):
        if attempt <= collisions:
            sandbox.compete({"data.json": f"competing-{attempt}\n"})

    sandbox.actor.before_push = advance
    if collisions == 3:
        with pytest.raises(subprocess.GitError):
            publish(sandbox, {"data.json": "pending\n"})
        assert sandbox.read("data.json") == "competing-3"
        assert "Files saved" not in caplog.text
    else:
        publish(sandbox, {"data.json": "pending\n"})
        assert sandbox.read("data.json") == "pending"
        sandbox.assert_history()
    assert sandbox.actor.attempts == 3
    assert sandbox.actor.branch("--show-current").strip() == "main"


@pytest.mark.parametrize("advance_remote", [False, True])
def test_policy_rejection_is_not_retried(
    sandbox_factory, monkeypatch, advance_remote, caplog
):
    sandbox = sandbox_factory()
    caplog.set_level("INFO", logger="coverage_comment")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(sandbox.remote / "hooks"))

    def reject(attempt: int):
        if attempt != 1:
            return
        if advance_remote:
            sandbox.compete({"independent.json": "independent\n"})
        hook = sandbox.remote / "hooks/pre-receive"
        hook.write_text(
            "#!/bin/sh\nprintf 'synthetic policy rejection\\n' >&2\nexit 1\n"
        )
        hook.chmod(0o755)

    sandbox.actor.before_push = reject
    with pytest.raises(subprocess.GitError, match="synthetic policy rejection"):
        publish(sandbox, {"data.json": "pending\n"})
    assert sandbox.actor.attempts == (2 if advance_remote else 1)
    assert sandbox.actor.branch("--show-current").strip() == "main"
    assert "Files saved" not in caplog.text


def test_fetch_failure_during_recovery_is_not_swallowed(sandbox_factory, tmp_path):
    sandbox = sandbox_factory()
    sandbox.collide_once({"independent.json": "independent\n"})
    sandbox.actor.after_rejection = lambda: git_at(
        sandbox.actor.cwd, "remote", "set-url", "origin", str(tmp_path / "missing.git")
    )
    with pytest.raises(subprocess.GitError) as error:
        publish(sandbox, {"data.json": "pending\n"})
    assert "fetch" in error.value.exc_args
    assert sandbox.actor.attempts == 1
    assert sandbox.actor.branch("--show-current").strip() == "main"


def test_unchanged_snapshot_does_not_push(sandbox_factory):
    sandbox = sandbox_factory()
    publish(sandbox, {"data.json": '{"writer":"seed"}\n'})
    assert sandbox.actor.attempts == 0
    assert git_at(sandbox.remote, "rev-parse", BRANCH) == sandbox.initial


@pytest.mark.parametrize("stage", ["initial-diff", "merge-base", "retry-diff"])
def test_permanent_inspection_errors_are_not_treated_as_changes_or_success(
    sandbox_factory, monkeypatch, caplog, stage
):
    sandbox = sandbox_factory()
    caplog.set_level("INFO", logger="coverage_comment")
    original_call = PublishingGit.__call__

    def failing_call(self: PublishingGit, *args: str, **kwargs: Any) -> str:
        target = "merge-base" if stage == "merge-base" else "diff"
        eligible = self.attempts == 0 if stage == "initial-diff" else self.attempts > 0
        if args[0] == target and eligible:
            raise subprocess.GitError.from_called_process_error(
                process.CalledProcessError(
                    128,
                    ["git", *args],
                    output="",
                    stderr="synthetic inspection failure",
                )
            )
        return original_call(self, *args, **kwargs)

    monkeypatch.setattr(PublishingGit, "__call__", failing_call)
    if stage == "merge-base":
        sandbox.collide_once({"independent.json": "independent\n"})
    elif stage == "retry-diff":

        def advance(attempt: int):
            if attempt == 1:
                git_at(
                    sandbox.winner,
                    "fetch",
                    str(sandbox.actor.cwd),
                    sandbox.actor.publications[0],
                )
                git_at(sandbox.winner, "switch", BRANCH)
                git_at(sandbox.winner, "reset", "--hard", "FETCH_HEAD")
                git_at(
                    sandbox.winner,
                    "commit",
                    "--allow-empty",
                    "-m",
                    "advance publication",
                )
                git_at(sandbox.winner, "push", "origin", BRANCH)

        sandbox.actor.before_push = advance
    with pytest.raises(subprocess.GitError, match="synthetic inspection failure"):
        publish(sandbox, {"data.json": "pending\n"})
    assert sandbox.actor.attempts == (0 if stage == "initial-diff" else 1)
    assert sandbox.actor.branch("--show-current").strip() == "main"
    assert "Files saved" not in caplog.text
