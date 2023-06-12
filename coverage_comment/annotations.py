from coverage_comment import coverage as coverage_module
from coverage_comment import github

MISSING_LINES_GROUP_TITLE = "Annotations of lines with missing coverage"


def create_pr_annotations(annotation_type: str, coverage: coverage_module.DiffCoverage):
    github.send_workflow_command(
        command="group", command_value=MISSING_LINES_GROUP_TITLE
    )

    for filepath, file_coverage in coverage.files.items():
        for missing_line in file_coverage.violation_lines:
            github.create_missing_coverage_annotation(
                annotation_type=annotation_type,
                file=filepath.name,
                line=missing_line,
            )

    github.send_workflow_command(command="endgroup", command_value="")
