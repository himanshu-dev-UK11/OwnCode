"""
Consolidated Module: tools.git_and_github

Combines: core.git_service, core.github_service
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['core.git_service', 'core.github_service']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.git_service (core/git_service.py)
# ============================================================================
"""
Git Service — v1.1

A thin, synchronous wrapper over the `git` CLI for the Source Control panel.
Everything runs through `subprocess` with an explicit `cwd` and hidden console
flags on Windows so `git` never flashes a console window.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from core.process_utils import hidden_subprocess_kwargs


@dataclass
class GitFile:
    """One entry from `git status --porcelain`."""
    path: str
    index_status: str     # staged side  (X in "XY")
    work_status: str      # unstaged side (Y in "XY")
    renamed_from: str = ""

    @property
    def staged(self) -> bool:
        return self.index_status not in (" ", "?", "")

    @property
    def unstaged(self) -> bool:
        return self.work_status not in (" ", "")

    @property
    def untracked(self) -> bool:
        return self.index_status == "?" and self.work_status == "?"

    @property
    def label(self) -> str:
        """A single human letter for the badge: A/M/D/R/U/?."""
        if self.untracked:
            return "U"
        code = self.index_status if self.staged else self.work_status
        return code.strip() or "M"


def parse_porcelain(text: str) -> List[GitFile]:
    """Parse `git status --porcelain=v1 -z`-style output."""
    out: List[GitFile] = []
    records = text.split("\0") if "\0" in text else text.splitlines()
    for rec in records:
        if not rec or len(rec) < 3:
            continue
        xy = rec[:2]
        rest = rec[3:]
        renamed_from = ""
        path = rest
        if " -> " in rest:
            renamed_from, _, path = rest.partition(" -> ")
        out.append(GitFile(
            path=path.strip().strip('"'),
            index_status=xy[0],
            work_status=xy[1],
            renamed_from=renamed_from.strip().strip('"'),
        ))
    return out


class GitService:
    def __init__(self, repo_path: str):
        self.repo_path = str(repo_path)

    # -- low level -----------------------------------------------------------
    def _run(self, *args: str, timeout: int = 30) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                **hidden_subprocess_kwargs(),
            )
            return proc.returncode, proc.stdout, proc.stderr
        except FileNotFoundError:
            return 127, "", "git is not installed or not on PATH"
        except subprocess.TimeoutExpired:
            return 124, "", "git command timed out"
        except Exception as e:  # pragma: no cover - defensive
            return 1, "", str(e)

    # -- queries -------------------------------------------------------------
    def is_repo(self) -> bool:
        code, out, _ = self._run("rev-parse", "--is-inside-work-tree")
        return code == 0 and out.strip() == "true"

    def current_branch(self) -> str:
        code, out, _ = self._run("symbolic-ref", "--quiet", "--short", "HEAD")
        if code == 0 and out.strip():
            return out.strip()
        code, out, _ = self._run("rev-parse", "--abbrev-ref", "HEAD")
        return out.strip() if code == 0 and out.strip() != "HEAD" else ""

    def branches(self) -> List[str]:
        code, out, _ = self._run("branch", "--format=%(refname:short)")
        if code != 0:
            return []
        return [b.strip() for b in out.splitlines() if b.strip()]

    def status(self) -> List[GitFile]:
        code, out, _ = self._run("status", "--porcelain=v1")
        return parse_porcelain(out) if code == 0 else []

    def diff(self, path: str, staged: bool = False) -> str:
        args = ["diff", "--no-color"]
        if staged:
            args.append("--staged")
        args.extend(["--", path])
        code, out, err = self._run(*args)
        return out if code == 0 else (err or "")

    def ahead_behind(self) -> Tuple[int, int]:
        """(ahead, behind) vs the upstream, or (0, 0) if none."""
        code, out, _ = self._run(
            "rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        if code != 0:
            return 0, 0
        try:
            behind, ahead = out.split()
            return int(ahead), int(behind)
        except Exception:
            return 0, 0

    # -- mutations -----------------------------------------------------------
    def stage(self, paths: List[str]) -> Tuple[bool, str]:
        code, _, err = self._run("add", "--", *paths)
        return code == 0, err

    def stage_all(self) -> Tuple[bool, str]:
        code, _, err = self._run("add", "-A")
        return code == 0, err

    def unstage(self, paths: List[str]) -> Tuple[bool, str]:
        code, _, err = self._run("restore", "--staged", "--", *paths)
        return code == 0, err

    def discard(self, paths: List[str]) -> Tuple[bool, str]:
        code, _, err = self._run("checkout", "--", *paths)
        return code == 0, err

    def commit(self, message: str) -> Tuple[bool, str]:
        if not message.strip():
            return False, "Empty commit message"
        code, out, err = self._run("commit", "-m", message)
        return code == 0, (err or out)

    def push(self) -> Tuple[bool, str]:
        code, out, err = self._run("push", timeout=120)
        message = err or out
        if code != 0 and "no upstream branch" in message.lower():
            branch = self.current_branch()
            if branch:
                retry_code, retry_out, retry_err = self._run(
                    "push", "--set-upstream", "origin", branch, timeout=120)
                return retry_code == 0, (retry_err or retry_out)
        return code == 0, message

    def pull(self) -> Tuple[bool, str]:
        code, out, err = self._run("pull", timeout=120)
        return code == 0, (err or out)

    def checkout(self, branch: str) -> Tuple[bool, str]:
        code, out, err = self._run("checkout", branch)
        return code == 0, (err or out)


# ============================================================================
# SECTION: core.github_service (core/github_service.py)
# ============================================================================
"""Secure GitHub account integration through the GitHub CLI.

Authentication is delegated to ``gh``. Credentials stay in the GitHub CLI's
OS-backed keyring and are never copied into OwnCode settings or logs.
"""

import json
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from typing import Any

from core.process_utils import hidden_subprocess_kwargs


@dataclass(frozen=True)
class GitHubAccount:
    login: str
    host: str = "github.com"
    protocol: str = ""
    active: bool = False


def parse_auth_accounts(
    payload: str, host: str = "github.com"
) -> list[GitHubAccount]:
    """Parse all linked accounts without exposing tokens."""
    try:
        data: dict[str, Any] = json.loads(payload)
    except (TypeError, ValueError):
        return []
    hosts = data.get("hosts", {})
    entries = hosts.get(host, []) if isinstance(hosts, dict) else []
    if not isinstance(entries, list):
        return []
    accounts = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        login = str(entry.get("login", "")).strip()
        if login:
            accounts.append(GitHubAccount(
                login=login,
                host=host,
                protocol=str(
                    entry.get("git_protocol") or entry.get("gitProtocol") or ""
                ).strip(),
                active=bool(entry.get("active")),
            ))
    return accounts


def parse_auth_status(payload: str, host: str = "github.com") -> GitHubAccount | None:
    """Parse the active GitHub account from ``gh auth status`` JSON."""
    accounts = parse_auth_accounts(payload, host)
    return next((account for account in accounts if account.active), None)


class GitHubService:
    """Run safe, non-token GitHub account operations through ``gh``."""

    def _run(self, *args: str, timeout: int = 30) -> tuple[int, str, str]:
        try:
            process = subprocess.run(
                ["gh", *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                **hidden_subprocess_kwargs(),
            )
            return process.returncode, process.stdout, process.stderr
        except FileNotFoundError:
            return 127, "", "GitHub CLI (gh) is not installed or not on PATH."
        except subprocess.TimeoutExpired:
            return 124, "", "GitHub CLI command timed out."
        except OSError as exc:
            return 1, "", str(exc)

    def status(self) -> tuple[GitHubAccount | None, str]:
        code, out, err = self._run("auth", "status", "--json", "hosts")
        account = parse_auth_status(out, "github.com")
        if account:
            return account, ""
        return None, err.strip() or "No active GitHub account is linked."

    def accounts(self) -> tuple[list[GitHubAccount], str]:
        code, out, err = self._run("auth", "status", "--json", "hosts")
        accounts = parse_auth_accounts(out, "github.com")
        if accounts:
            return accounts, ""
        return [], err.strip() or "No GitHub CLI accounts are linked."

    def login(self) -> tuple[bool, str]:
        if not shutil.which("gh"):
            return self.open_browser_fallback()
        try:
            subprocess.Popen(
                ["gh", "auth", "login", "--hostname", "github.com", "--web",
                 "--git-protocol", "https"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **hidden_subprocess_kwargs(),
            )
        except OSError as exc:
            return False, f"Could not start GitHub CLI login: {exc}"
        return True, (
            "GitHub login opened in your browser. Finish it there; "
            "the IDE will verify the account automatically.")

    def switch(self, login: str) -> tuple[bool, str]:
        if not login.strip():
            return False, "Choose a GitHub account first."
        code, out, err = self._run(
            "auth", "switch", "--hostname", "github.com", "--user", login.strip())
        return code == 0, (err or out).strip()

    def open_browser_fallback(self) -> tuple[bool, str]:
        try:
            opened = webbrowser.open("https://github.com/login")
        except OSError as exc:
            return False, f"Could not open the browser: {exc}"
        if opened:
            return True, (
                "GitHub opened in your browser. Install GitHub CLI (gh) and "
                "click Login again to securely link the account.")
        return False, "Could not open the default browser."

    def logout(self, login: str) -> tuple[bool, str]:
        if not login.strip():
            return False, "No GitHub account is currently linked."
        code, out, err = self._run(
            "auth", "logout", "--hostname", "github.com",
            "--user", login.strip(), "--yes")
        return code == 0, (err or out).strip()

