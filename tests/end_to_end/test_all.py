def test_push_main_branch(gh_repo, wait_for_run_to_start, head_sha1, git, gh_me):

    run_id = wait_for_run_to_start(sha1=head_sha1(), branch="main", gh=gh_me)

    print(gh_me("run", "watch", f"{run_id}", "--exit-status"))

    # Check the coverage badge. Maybe even extract its exact URL from the watch
    # command above.


def test_self_pr(gh_repo, git, gh_me):
    # TODO
    pass


def test_external_pr(gh_repo, git, gh_me, gh_other):
    # TODO
    pass
