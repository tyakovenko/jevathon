"""Step 7: tests (CI) + secrets (deterministic) + AI slop (Jev), on both the agent and dev paths."""

import re
from enum import StrEnum

from pydantic import BaseModel
from typesafe_sdk import Noul

from app.config import Settings
from app.services.github import CIStatus, GitHub
from app.services.jev import Jev
from app.services.secrets_scan import scan_diff

# PLACEHOLDERS — final list to be supplied (see project-log). Keys become finding labels.
SLOP_QUESTIONS: dict[str, str] = {
    "scope_creep": "Does this change add code the issue didn't ask for "
                   "(unrequested refactors, speculative abstractions, unused helpers)?",
    "filler_comments": "Do the comments narrate what the code does, or contain hedging or placeholder text "
                       "(e.g. 'for simplicity', 'in a real implementation', TODO stubs)?",
    "hidden_failures": "Does this change hide failures (swallowed exceptions, catch-and-return-default, "
                       "fallbacks that fake success)?",
}

_FILE_SPLIT = re.compile(r"^diff --git a/(\S+) b/\S+$", re.MULTILINE)


class Status(StrEnum):
    passed = "passed"
    failed = "failed"
    pending = "pending"   # CI still running; re-run on the check_suite webhook


class ChecksResult(BaseModel):
    status: Status
    findings: list[str]


def split_diff(diff: str) -> dict[str, str]:
    """Per-file hunks. Jev gets one file at a time: large irrelevant state lowers its accuracy."""
    parts = _FILE_SPLIT.split(diff)
    # split → [preamble, path1, body1, path2, body2, ...]
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


async def run_checks(pr_number: int, issue_title: str, github: GitHub, jev: Jev, cfg: Settings) -> ChecksResult:
    findings: list[str] = []

    ci = await github.ci_status(pr_number)
    if ci is CIStatus.failure:
        findings.append("tests: CI failed")

    diff = await github.pr_diff(pr_number)
    findings += [f"secrets: {f}" for f in scan_diff(diff)]

    for path, hunk in split_diff(diff).items():
        a = await jev.ask({"issue": issue_title, "file": path, "diff": hunk},
                          {k: Noul(instructions=q) for k, q in SLOP_QUESTIONS.items()})
        findings += [f"slop: {path}: {k} (p={a[k].noul:.2f})" for k in SLOP_QUESTIONS if a[k].noul > cfg.slop_noul_threshold]

    if findings:
        return ChecksResult(status=Status.failed, findings=findings)
    if ci is CIStatus.pending:
        return ChecksResult(status=Status.pending, findings=["tests: CI pending or not configured"])
    return ChecksResult(status=Status.passed, findings=[])
