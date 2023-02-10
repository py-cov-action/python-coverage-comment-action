import base64

import httpx
import pytest


@pytest.mark.repo_suffix("public")
def test_public_repo(
    gh_create_repo,
    wait_for_run_to_start,
    wait_for_run_triggered_by_user_to_start,
    get_sha1,
    gh_me,
    gh_other,
    repo_full_name,
    cd,
    git,
    add_coverage_line,
    token_me,
    token_other,
    gh_create_fork,
    gh_other_username,
):
    # Create a GitHub repo, make it public
    gh_create_repo("--public")

    # GitHub Actions should start soon
    run_id = wait_for_run_to_start(sha1=get_sha1(), branch="main", gh=gh_me)

    # AAAaand it's started. Now let's wait for it to end.
    # Also, raise if it doesn't end succefully. That half of the job.
    gh_me("run", "watch", run_id, "--exit-status")

    # Now to the other half: maybe it did nothing succesfully, so let's check
    # that the lob log contains the 3 links to our svg images
    repo_api_url = "/repos/{owner}/{repo}"

    # First get the job id
    job_list_url = f"{repo_api_url}/actions/runs/{run_id}/jobs"
    job_ids = gh_me("api", job_list_url, "--jq=.jobs[].id").strip().splitlines()
    assert len(job_ids) == 1
    job_id = job_ids[0]

    # Then check the logs for this job
    logs = gh_me("api", f"{repo_api_url}/actions/jobs/{job_id}/logs")

    print("Logs:", logs)
    log_lines = logs.splitlines()

    # The easiest way to check the links is to assume there will be no other
    # line with a link prefixed by 4 spaces. If at some point there is, we'll
    # change the test.
    links = {line.strip().split()[-1] for line in log_lines if "    https://" in line}
    # - html report
    # - badge 1, 2 and 3
    # - coverage branch readme url
    assert len(links) == 5

    client = httpx.Client()

    # Check that all 5 links are valid and lead to a 200
    # It's made this way to avoid hardcoding links in the test, because I assume
    # they'll be evolving.
    number_of_svgs = 0
    for link in links:
        response = client.get(link)
        response.raise_for_status()
        number_of_svgs += int(response.text.startswith("<svg"))

    assert number_of_svgs == 3

    # Check that logs point to the branch that has the readme file.
    data_branch_url = (
        f"https://github.com/{repo_full_name}/tree/python-coverage-comment-action-data"
    )
    assert data_branch_url in links

    # Time to check the Readme contents
    raw_url_prefix = (
        f"https://github.com/{repo_full_name}/raw/python-coverage-comment-action-data"
    )

    readme_url = f"{raw_url_prefix}/README.md"
    response = client.get(readme_url, follow_redirects=True)
    response.raise_for_status()
    # And all previously found links should be present
    readme = response.text
    for link in links - {data_branch_url}:
        assert link in readme

    # And while we're at it, there are 2 other files we want to check in this
    # branch. Once again, trying to avoid hardcoding too many specifics, that's what
    # unit tests are for.
    data = client.get(f"{raw_url_prefix}/data.json", follow_redirects=True).json()
    assert "coverage" in data

    endpoint = client.get(
        f"{raw_url_prefix}/endpoint.json", follow_redirects=True
    ).json()
    assert "schemaVersion" in endpoint

    # Ok, now let's create a PR
    with cd("repo"):
        git("checkout", "-b", "new_branch")
        add_coverage_line("a,b,c,,a-b-c")
        git("push", "origin", "new_branch", env={"GITHUB_TOKEN": token_me})
        sha1 = get_sha1()

    gh_me("pr", "create", "--fill")

    # Wait for the action to run on the PR
    run_id = wait_for_run_to_start(sha1=sha1, branch="new_branch", gh=gh_me)
    gh_me("run", "watch", run_id, "--exit-status")

    # Check that it added a comment saying coverage went up
    # Weird thing: apparently, GitHub returns `\n` as the content of a comment
    # for a few seconds after the comment post. And then it starts working.
    comment = gh_me(
        "pr",
        "view",
        "--json=comments",
        "--jq=.comments[0].body",
        fail_value="\n",
    )
    assert ":arrow_up:" in comment

    # Let's merge the PR and see if everything works fine
    gh_me("pr", "merge", "1", "--merge")
    git("fetch", env={"GITHUB_TOKEN": token_me})

    run_id = wait_for_run_to_start(
        sha1=get_sha1("origin/main"), branch="main", gh=gh_me
    )
    gh_me("run", "watch", run_id, "--exit-status")

    # And now let's create a PR from a fork of a different user
    gh_create_fork()
    with cd("fork"):
        git("checkout", "-b", "external_branch")
        add_coverage_line("a,b,c,,a-b-c")
        git("push", "origin", "external_branch", env={"GITHUB_TOKEN": token_other})
        ext_sha1 = get_sha1()

    full_branch_name = f"{gh_other_username}:external_branch"
    gh_other("pr", "create", "--fill", "--head", full_branch_name)

    # Wait for the action to start on the PR
    ext_run_id_1 = wait_for_run_to_start(
        sha1=ext_sha1,
        branch="external_branch",
        gh=gh_other,
    )

    # Extra step: this PR is from a first time contributor to the repo, we need to approve it.
    approve_url = f"{repo_api_url}/actions/runs/{ext_run_id_1}/approve"
    gh_me("api", "-X", "POST", approve_url)

    # Wait for the action to run
    gh_other("run", "watch", ext_run_id_1, "--exit-status")

    # When it's finished, the "Post coverage comment" action starts
    ext_run_id_2 = wait_for_run_triggered_by_user_to_start(
        workflow_name="Post coverage comment",
        triggering_user=gh_other_username,
        gh=gh_other,
    )
    gh_other("run", "watch", ext_run_id_2, "--exit-status")

    # Check that it added a comment saying coverage went up
    ext_comment = gh_other(
        "pr",
        "view",
        full_branch_name,
        "--json=comments",
        "--jq=.comments[0].body",
        fail_value="\n",
    )

    assert ":arrow_up:" in ext_comment


@pytest.mark.repo_suffix("private")
def test_private_repo(
    gh_create_repo,
    wait_for_run_to_start,
    get_sha1,
    gh_me,
    repo_full_name,
    cd,
    git,
    add_coverage_line,
    token_me,
):
    # Here we go again, this time with a private repo.
    gh_create_repo("--private")

    # Actions will start soon
    run_id = wait_for_run_to_start(sha1=get_sha1(), branch="main", gh=gh_me)

    # AAAaand it's started. Now let's wait for it to end.
    # Also, raise if it doesn't end succefully. That half of the job.
    gh_me("run", "watch", run_id, "--exit-status")

    # Now to the other half: maybe it did nothing succesfully. Let's check
    # Stdout contains the expected link. This time, there's only one link
    # (because shields.io can't access a private repo)

    # First get the job id
    repo_api_url = "/repos/{owner}/{repo}"
    job_list_url = f"{repo_api_url}/actions/runs/{run_id}/jobs"
    job_ids = gh_me("api", job_list_url, "--jq=.jobs[].id").strip().splitlines()
    assert len(job_ids) == 1
    job_id = job_ids[0]

    # Then check the logs for this job
    logs = gh_me("api", f"{repo_api_url}/actions/jobs/{job_id}/logs")
    print("Logs:", logs)

    # We can't check that the link loads, because it's a private repo but we
    # can check it's the expected link
    raw_url_prefix = (
        f"https://github.com/{repo_full_name}/raw/python-coverage-comment-action-data"
    )
    link = f"{raw_url_prefix}/badge.svg"
    assert link in logs

    file_api_url = "contents/{filename}?ref=python-coverage-comment-action-data"
    badge_api_url = f"{repo_api_url}/{file_api_url.format(filename='badge.svg')}"

    # To check the contents, we need to use the API
    base64_badge = gh_me("api", badge_api_url, "--jq=.content")
    badge = base64.b64decode(base64_badge.encode()).decode()
    assert badge.startswith("<svg")

    # Check that logs point to the branch that has the readme file.
    data_branch_url = (
        f"https://github.com/{repo_full_name}/tree/python-coverage-comment-action-data"
    )
    assert data_branch_url in logs

    readme_api_url = f"{repo_api_url}/{file_api_url.format(filename='README.md')}"
    # Now read the Readme
    base64_readme = gh_me("api", readme_api_url, "--jq=.content")
    readme = base64.b64decode(base64_readme.encode()).decode()

    # And the previously found link should be present
    assert link in readme

    # Ok, now let's create a PR
    with cd("repo"):
        git("checkout", "-b", "new_branch")
        add_coverage_line("a,b,c,,a-b-c")
        git("push", "origin", "new_branch", env={"GITHUB_TOKEN": token_me})
        sha1 = get_sha1()

    gh_me("pr", "create", "--fill")

    # Wait for the action to run on the PR
    run_id = wait_for_run_to_start(sha1=sha1, branch="new_branch", gh=gh_me)
    gh_me("run", "watch", run_id, "--exit-status")

    # Check that it added a comment saying coverage went up
    comment = gh_me(
        "pr",
        "view",
        "--json=comments",
        "--jq=.comments[0].body",
        fail_value="\n",
    )
    assert ":arrow_up:" in comment

    # Let's merge the PR and see if everything works fine
    gh_me("pr", "merge", "1", "--merge")

    git("fetch", env={"GITHUB_TOKEN": token_me})

    run_id = wait_for_run_to_start(
        sha1=get_sha1("origin/main"), branch="main", gh=gh_me
    )
    gh_me("run", "watch", run_id, "--exit-status")
