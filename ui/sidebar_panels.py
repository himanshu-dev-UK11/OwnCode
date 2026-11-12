"""
Consolidated Module: ui.sidebar_panels

Combines: ui.panels.search_panel, ui.panels.git_panel, ui.panels.run_panel, ui.panels.test_panel, ui.panels.tasks_panel, ui.panels.memory_panel, ui.panels.sidebar
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['ui.panels.search_panel', 'ui.panels.git_panel', 'ui.panels.run_panel', 'ui.panels.test_panel', 'ui.panels.tasks_panel', 'ui.panels.memory_panel', 'ui.panels.sidebar']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: ui.panels.search_panel (ui/panels/search_panel.py)
# ============================================================================
"""
Search panel — v1.0

Full-text search (and optional replace) across the workspace. Walks the tree on
a worker thread so a big repo never blocks the UI, honouring the workspace
exclude patterns from settings. Results are grouped by file; clicking a match
opens the file in the editor.

Signals
  file_open_requested(str, int)  — (absolute path, 1-based line) open + jump
  toast(str, str)                — (message, level)
"""

import os
import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QLabel,
)
from PySide6.QtCore import Qt, Signal, QThread

from ui.design_system import get_design_system, Spacing, FontSize
from ui.widgets.controls import SectionHeader, IconButton


# Directories we never descend into regardless of settings — cheap wins that
# also stop the walk from wandering into VCS internals or dependency dumps.
_ALWAYS_SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv",
                ".idea", ".vscode", "dist", "build", ".mypy_cache"}
_MAX_FILE_BYTES = 2_000_000     # skip anything bigger — likely a binary/asset
_MAX_RESULTS = 2000             # keep the UI responsive on pathological queries


class _SearchWorker(QThread):
    """Runs one full-text search off the UI thread."""
    result = Signal(object)     # list[(path, [(line_no, line_text)])] or Exception

    def __init__(self, root: str, query: str, *, regex: bool, case: bool,
                 excludes: list[str], parent=None):
        super().__init__(parent)
        self._root = root
        self._query = query
        self._regex = regex
        self._case = case
        self._excludes = set(excludes or []) | _ALWAYS_SKIP
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _matcher(self):
        flags = 0 if self._case else re.IGNORECASE
        if self._regex:
            return re.compile(self._query, flags)
        return re.compile(re.escape(self._query), flags)

    def run(self):
        try:
            pattern = self._matcher()
        except re.error as e:
            self.result.emit(RuntimeError(f"Invalid regex: {e}"))
            return
        try:
            grouped: list[tuple[str, list]] = []
            total = 0
            for dirpath, dirnames, filenames in os.walk(self._root):
                if self._cancel:
                    break
                dirnames[:] = [d for d in dirnames if d not in self._excludes]
                for fn in filenames:
                    if self._cancel or total >= _MAX_RESULTS:
                        break
                    full = os.path.join(dirpath, fn)
                    try:
                        if os.path.getsize(full) > _MAX_FILE_BYTES:
                            continue
                        with open(full, "r", encoding="utf-8", errors="ignore") as f:
                            hits = []
                            for i, line in enumerate(f, 1):
                                if pattern.search(line):
                                    hits.append((i, line.rstrip("\n")[:400]))
                                    total += 1
                                    if total >= _MAX_RESULTS:
                                        break
                    except (OSError, UnicodeError):
                        continue
                    if hits:
                        grouped.append((full, hits))
            self.result.emit(grouped)
        except Exception as e:                        # pragma: no cover - defensive
            self.result.emit(e)


class SearchPanel(QWidget):

    file_open_requested = Signal(str, int)
    toast = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._root = ""
        self._worker: _SearchWorker | None = None
        self._regex = False
        self._case = False
        self._build()
        self._apply_style()

    # -- construction --------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = SectionHeader("Search")
        self._regex_btn = IconButton("code", "Use regular expression", size=24,
                                     icon_size=14, checkable=True)
        self._regex_btn.toggled.connect(self._on_regex_toggled)
        self._case_btn = IconButton("type", "Match case", size=24,
                                    icon_size=14, checkable=True)
        self._case_btn.toggled.connect(self._on_case_toggled)
        for b in (self._case_btn, self._regex_btn):
            header.add_action(b)
        lay.addWidget(header)

        box = QWidget()
        br = QVBoxLayout(box)
        br.setContentsMargins(Spacing.lg, 0, Spacing.lg, Spacing.sm)
        br.setSpacing(4)
        self._query = QLineEdit()
        self._query.setObjectName("SearchInput")
        self._query.setPlaceholderText("Search")
        self._query.returnPressed.connect(self._run_search)
        self._query.textChanged.connect(self._debounced)
        self._replace = QLineEdit()
        self._replace.setObjectName("SearchInput")
        self._replace.setPlaceholderText("Replace")
        br.addWidget(self._query)

        replace_row = QWidget()
        rr = QHBoxLayout(replace_row)
        rr.setContentsMargins(0, 0, 0, 0)
        rr.setSpacing(4)
        rr.addWidget(self._replace, 1)
        self._replace_all_btn = IconButton("check", "Replace all matches",
                                           size=24, icon_size=14)
        self._replace_all_btn.clicked.connect(self._on_replace_all)
        rr.addWidget(self._replace_all_btn)
        br.addWidget(replace_row)
        lay.addWidget(box)

        self._summary = QLabel("")
        self._summary.setProperty("role", "muted")
        self._summary.setContentsMargins(Spacing.lg, 0, Spacing.lg, Spacing.xs)
        lay.addWidget(self._summary)

        self._results = QTreeWidget()
        self._results.setObjectName("SearchResults")
        self._results.setHeaderHidden(True)
        self._results.setIndentation(12)
        self._results.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self._results, 1)

        # Debounce timer for type-to-search.
        from PySide6.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._run_search)

    # -- public API ----------------------------------------------------------
    def set_root(self, path: str):
        self._root = str(path or "")
        self._results.clear()
        self._summary.setText("")

    # -- search --------------------------------------------------------------
    def _debounced(self, _text: str):
        self._timer.start()

    def _on_regex_toggled(self, on: bool):
        self._regex = on
        self._run_search()

    def _on_case_toggled(self, on: bool):
        self._case = on
        self._run_search()

    def _excludes(self) -> list[str]:
        try:
            from ui.settings_manager import get_settings_manager
            return get_settings_manager().get_exclude_patterns() or []
        except Exception:
            return []

    def _run_search(self):
        self._timer.stop()
        query = self._query.text()
        self._results.clear()
        self._summary.setText("")
        if not self._root:
            self._summary.setText("Open a folder to search.")
            return
        if len(query) < 2:
            return
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(50)
        self._summary.setText("Searching…")
        self._worker = _SearchWorker(
            self._root, query, regex=self._regex, case=self._case,
            excludes=self._excludes(), parent=self)
        self._worker.result.connect(self._on_results)
        self._worker.start()

    def _on_results(self, payload):
        if isinstance(payload, Exception):
            self._summary.setText(str(payload))
            self.toast.emit(str(payload), "warning")
            return
        self._results.clear()
        files = len(payload)
        matches = sum(len(hits) for _, hits in payload)
        self._summary.setText(
            f"{matches} result{'s' if matches != 1 else ''} in "
            f"{files} file{'s' if files != 1 else ''}"
            if matches else "No results.")
        c = get_design_system().colors
        from PySide6.QtGui import QColor
        for path, hits in payload:
            rel = os.path.relpath(path, self._root)
            top = QTreeWidgetItem([f"{Path(rel).name}   {str(Path(rel).parent)}"])
            top.setData(0, Qt.UserRole, (path, hits[0][0]))
            top.setForeground(0, QColor(c.text_primary))
            for line_no, text in hits:
                child = QTreeWidgetItem([f"{line_no}: {text.strip()}"])
                child.setData(0, Qt.UserRole, (path, line_no))
                child.setForeground(0, QColor(c.text_secondary))
                top.addChild(child)
            self._results.addTopLevelItem(top)
            top.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        data = item.data(0, Qt.UserRole)
        if data:
            path, line_no = data
            self.file_open_requested.emit(path, int(line_no))

    def _on_replace_all(self):
        query = self._query.text()
        replacement = self._replace.text()
        if not self._root or len(query) < 2:
            return
        try:
            flags = 0 if self._case else re.IGNORECASE
            pattern = (re.compile(query, flags) if self._regex
                       else re.compile(re.escape(query), flags))
        except re.error as e:
            self.toast.emit(f"Invalid regex: {e}", "error")
            return
        changed_files = 0
        changed_hits = 0
        excludes = set(self._excludes()) | _ALWAYS_SKIP
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = [d for d in dirnames if d not in excludes]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(full) > _MAX_FILE_BYTES:
                        continue
                    with open(full, "r", encoding="utf-8") as f:
                        original = f.read()
                except (OSError, UnicodeError):
                    continue
                new, n = pattern.subn(replacement, original)
                if n and new != original:
                    try:
                        with open(full, "w", encoding="utf-8") as f:
                            f.write(new)
                        changed_files += 1
                        changed_hits += n
                    except OSError:
                        continue
        self.toast.emit(
            f"Replaced {changed_hits} occurrence(s) in {changed_files} file(s).",
            "success" if changed_hits else "info")
        self._run_search()

    # -- style ---------------------------------------------------------------
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #SearchPanel {{ background: {c.surface}; }}
            #SearchInput {{
                background: {c.surface_inset}; color: {c.text_primary};
                border: 1px solid {c.border_subtle}; border-radius: 4px;
                padding: 4px 6px; font-size: {FontSize.small}px;
            }}
            #SearchInput:focus {{ border: 1px solid {c.accent}; }}
            #SearchResults {{
                background: {c.surface}; color: {c.text_secondary};
                border: none; font-size: {FontSize.small}px; outline: none;
            }}
            #SearchResults::item {{ padding: 2px 4px; }}
            #SearchResults::item:hover {{ background: {c.surface_raised}; }}
            #SearchResults::item:selected {{ background: {c.selection}; color: {c.text_primary}; }}
        """)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.panels.git_panel (ui/panels/git_panel.py)
# ============================================================================
"""
GitHub / Git panel — v2.0

A real Git panel over `core/git_service.GitService`: branch + ahead/behind,
a clean 2-row GitHub account card (never clipping `@username` or `Switch Account`),
a commit box, and staged / unstaged change lists with stage, unstage, discard
and per-file diff. Long-running calls (push/pull/refresh) run on a worker thread
so the UI never blocks.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPlainTextEdit, QAbstractItemView, QMessageBox, QInputDialog, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer

from ui.design_system import get_design_system, Spacing, FontSize, Radius
from ui.widgets.controls import SectionHeader, TextButton, IconButton
from core.git_service import GitService, GitFile
from core.github_service import GitHubAccount, GitHubService


class _Worker(QThread):
    """Runs one callable off the UI thread and delivers its result."""
    done = Signal(object)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:                     # pragma: no cover
            self.done.emit(e)


class GitPanel(QFrame):

    file_open_requested = Signal(str)
    diff_requested = Signal(str, str)
    toast = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GitPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._root = ""
        self._service: GitService | None = None
        self._github = GitHubService()
        self._account: GitHubAccount | None = None
        self._account_check_running = False
        self._account_checked_once = False
        self._auth_poll_count = 0
        self._auth_poll_timer = QTimer(self)
        self._auth_poll_timer.setInterval(2000)
        self._auth_poll_timer.timeout.connect(self._poll_auth_status)
        self._workers: list[_Worker] = []
        self._build()
        self._apply_style()

    # -- construction --------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.xs)

        self._header = SectionHeader("GitHub / Git")
        self._refresh_btn = IconButton("refresh", "Refresh", size=24, icon_size=14)
        self._refresh_btn.clicked.connect(self._on_manual_refresh)
        self._pull_btn = IconButton("chevron-down", "Pull", size=24, icon_size=14)
        self._pull_btn.clicked.connect(self._on_pull)
        self._push_btn = IconButton("chevron-right", "Push", size=24, icon_size=14)
        self._push_btn.clicked.connect(self._on_push)
        for b in (self._refresh_btn, self._pull_btn, self._push_btn):
            self._header.add_action(b)
        lay.addWidget(self._header)

        # Clean 2-row GitHub Account Card (never clips username or buttons!)
        self._account_card = QFrame()
        self._account_card.setObjectName("GitAccountCard")
        self._account_card.setAttribute(Qt.WA_StyledBackground, True)
        ac_lay = QVBoxLayout(self._account_card)
        ac_lay.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, Spacing.xs)
        ac_lay.setSpacing(Spacing.xs)

        self._account_label = QLabel("GitHub: not checked")
        self._account_label.setObjectName("GitAccountLabel")
        self._account_label.setWordWrap(True)
        self._account_label.setMinimumWidth(0)
        ac_lay.addWidget(self._account_label)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(Spacing.xs)
        self._login_btn = TextButton("Login", icon_name="git", tooltip="Sign in or switch GitHub account")
        self._login_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._login_btn.clicked.connect(self._on_login)
        self._logout_btn = TextButton("Logout", tooltip="Sign out of current GitHub account")
        self._logout_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._logout_btn.clicked.connect(self._on_logout)
        self._logout_btn.setEnabled(False)
        btn_row.addWidget(self._login_btn, 1)
        btn_row.addWidget(self._logout_btn, 1)
        ac_lay.addLayout(btn_row)

        card_wrap = QWidget()
        cw_lay = QVBoxLayout(card_wrap)
        cw_lay.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, 0)
        cw_lay.addWidget(self._account_card)
        lay.addWidget(card_wrap)

        self._branch = QLabel("Open a folder to use GitHub / Git.")
        self._branch.setProperty("role", "muted")
        self._branch.setWordWrap(True)
        self._branch.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, Spacing.xs)
        lay.addWidget(self._branch)

        self._commit_msg = QPlainTextEdit()
        self._commit_msg.setObjectName("CommitMessage")
        self._commit_msg.setPlaceholderText("Commit message (Ctrl+Enter to commit)")
        self._commit_msg.setFixedHeight(64)
        self._commit_msg.installEventFilter(self)
        lay.addWidget(self._commit_msg)

        commit_row = QWidget()
        cr = QHBoxLayout(commit_row)
        cr.setContentsMargins(Spacing.md, 2, Spacing.md, Spacing.xs)
        cr.setSpacing(Spacing.xs)
        self._stage_all_btn = TextButton("Stage All", icon_name="plus")
        self._stage_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._stage_all_btn.clicked.connect(self._on_stage_all)
        self._commit_btn = TextButton("Commit", icon_name="tasks", variant="primary", tooltip="Commit staged changes (Ctrl+Enter)")
        self._commit_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._commit_btn.clicked.connect(self._on_commit)
        cr.addWidget(self._stage_all_btn, 1)
        cr.addWidget(self._commit_btn, 1)
        lay.addWidget(commit_row)

        self._staged_label = QLabel("STAGED CHANGES")
        self._staged_label.setProperty("role", "subheading")
        self._staged_label.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, 2)
        lay.addWidget(self._staged_label)
        self._staged = QListWidget()
        self._staged.setObjectName("GitList")
        self._staged.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._staged.itemClicked.connect(lambda it: self._show_diff(it, staged=True))
        self._staged.itemDoubleClicked.connect(lambda it: self._unstage(it))
        lay.addWidget(self._staged, 1)

        self._changes_label = QLabel("CHANGES")
        self._changes_label.setProperty("role", "subheading")
        self._changes_label.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, 2)
        lay.addWidget(self._changes_label)
        self._changes = QListWidget()
        self._changes.setObjectName("GitList")
        self._changes.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._changes.itemClicked.connect(lambda it: self._show_diff(it, staged=False))
        self._changes.itemDoubleClicked.connect(lambda it: self._stage(it))
        lay.addWidget(self._changes, 1)

        self._empty = QLabel("Working tree clean — no uncommitted changes.")
        self._empty.setProperty("role", "muted")
        self._empty.setWordWrap(True)
        self._empty.setContentsMargins(Spacing.md, Spacing.sm, Spacing.md, Spacing.md)
        self._empty.setVisible(False)
        lay.addWidget(self._empty)

        # Bottom stretch keeps controls compact at the top when lists are hidden
        self._bottom_spacer = QWidget()
        self._bottom_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self._bottom_spacer, 1)

        self._render_not_repo("Open a folder to use GitHub / Git.")

    # -- public API ----------------------------------------------------------
    def set_root(self, path: str):
        """Point the panel at a workspace root and refresh."""
        self._root = str(path or "")
        self._service = GitService(self._root) if self._root else None
        if self.isVisible():
            self._refresh_account()
            self.refresh()

    def _on_manual_refresh(self):
        self._refresh_account(force=True)
        self.refresh()

    def _refresh_account(self, force: bool = False):
        if self._account_check_running:
            return
        if not force and self._account_checked_once and not self._auth_poll_timer.isActive():
            return
        if not shutil.which("gh"):
            self._account_checked_once = True
            self._account_label.setText("GitHub: CLI (gh) not installed")
            self._logout_btn.setEnabled(False)
            return
        self._account_check_running = True
        self._account_checked_once = True
        self._run_async(self._github.status, self._on_account_status)

    def _on_account_status(self, result):
        self._account_check_running = False
        account, message = result
        self._account = account
        if account:
            if self._auth_poll_timer.isActive():
                self._auth_poll_timer.stop()
            self._account_label.setText(f"● GitHub: @{account.login}")
            self._login_btn.setText("Switch Account")
            try:
                self._login_btn.clicked.disconnect()
            except Exception:
                pass
            self._login_btn.clicked.connect(self._on_switch_account)
            self._logout_btn.setEnabled(True)
        else:
            self._account_label.setText("○ GitHub: not linked")
            self._login_btn.setText("Login")
            try:
                self._login_btn.clicked.disconnect()
            except Exception:
                pass
            self._login_btn.clicked.connect(self._on_login)
            self._logout_btn.setEnabled(False)
            if message and "not active" not in message.lower() and "no active" not in message.lower():
                self.toast.emit(message, "warning")

    def _on_login(self):
        self._login_btn.setEnabled(False)
        self.toast.emit("Starting GitHub browser login…", "info")
        self._run_async(self._github.login, self._on_auth_finished)

    def _on_switch_account(self):
        self._login_btn.setEnabled(False)
        self._run_async(self._github.accounts, self._on_accounts_ready)

    def _on_accounts_ready(self, result):
        accounts, message = result
        if len(accounts) > 1:
            labels = [f"@{account.login}" for account in accounts]
            selected, ok = QInputDialog.getItem(
                self, "Switch GitHub account", "Use account:", labels, 0, False)
            if ok and selected:
                login = selected.removeprefix("@")
                self._run_async(
                    lambda: self._github.switch(login), self._on_auth_finished)
                return
        if accounts:
            self._on_login()
            return
        self._login_btn.setEnabled(True)
        self.toast.emit(message or "No GitHub account is linked.", "warning")

    def _on_logout(self):
        if not self._account:
            return
        answer = QMessageBox.question(
            self, "Log out of GitHub",
            f"Unlink GitHub account @{self._account.login} from this computer?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self._logout_btn.setEnabled(False)
        self._run_async(
            lambda: self._github.logout(self._account.login),
            self._on_auth_finished)

    def _on_auth_finished(self, result):
        ok, message = result
        self.toast.emit(
            message or ("GitHub account linked." if ok else "GitHub authentication failed."),
            "success" if ok else "error")
        self._login_btn.setEnabled(True)
        if ok and shutil.which("gh"):
            self._auth_poll_count = 0
            self._auth_poll_timer.start()
        else:
            self._refresh_account(force=True)

    def _poll_auth_status(self):
        self._auth_poll_count += 1
        self._refresh_account(force=True)
        if self._account or self._auth_poll_count >= 15:
            self._auth_poll_timer.stop()
            if not self._account:
                self.toast.emit(
                    "GitHub login is still incomplete. Finish it in the browser and "
                    "click Refresh to verify.", "warning")

    def showEvent(self, event):
        """Refresh account and repo state when the GitHub view is actually opened."""
        self._refresh_account()
        self.refresh()
        super().showEvent(event)

    def refresh(self):
        if not self._service:
            self._render_not_repo("Open a folder to use GitHub / Git.")
            return

        def work():
            svc = self._service
            if not svc.is_repo():
                return {"repo": False}
            return {
                "repo": True,
                "branch": svc.current_branch(),
                "ahead_behind": svc.ahead_behind(),
                "files": svc.status(),
            }

        self._run_async(work, self._on_status_ready)

    # -- threading -----------------------------------------------------------
    def _run_async(self, fn, on_done):
        worker = _Worker(fn, self)
        self._workers.append(worker)

        def _finish(result):
            if worker in self._workers:
                self._workers.remove(worker)
            worker.deleteLater()
            if isinstance(result, Exception):
                self.toast.emit(f"Git error: {result}", "error")
            else:
                on_done(result)

        worker.done.connect(_finish)
        worker.start()

    # -- rendering -----------------------------------------------------------
    def _on_status_ready(self, data: dict):
        if not data.get("repo"):
            self._render_not_repo("This folder is not a Git repository.")
            return
        branch = data.get("branch", "")
        ahead, behind = data.get("ahead_behind", (0, 0))
        suffix = ""
        if ahead or behind:
            suffix = f"   ↑{ahead} ↓{behind}"
        self._branch.setText(f"⑃ Branch: {branch}{suffix}" if branch else "⑃ Repository ready")

        files: list[GitFile] = data.get("files", [])
        self._staged.clear()
        self._changes.clear()
        for f in files:
            if f.staged:
                self._staged.addItem(self._make_item(f))
            if f.unstaged or f.untracked:
                self._changes.addItem(self._make_item(f))

        has_staged = self._staged.count() > 0
        has_changes = self._changes.count() > 0
        has_any = has_staged or has_changes

        self._staged.setVisible(has_staged)
        self._staged_label.setVisible(has_staged)
        self._changes.setVisible(has_changes)
        self._changes_label.setVisible(has_changes)
        self._empty.setVisible(not has_any)
        self._bottom_spacer.setVisible(not has_any)
        self._set_controls_enabled(True)

    def _render_not_repo(self, message: str):
        self._branch.setText(message)
        self._staged.clear()
        self._changes.clear()
        self._staged.setVisible(False)
        self._staged_label.setVisible(False)
        self._changes.setVisible(False)
        self._changes_label.setVisible(False)
        self._empty.setVisible(False)
        self._bottom_spacer.setVisible(True)
        self._set_controls_enabled(False)

    def _set_controls_enabled(self, on: bool):
        for w in (self._commit_msg, self._commit_btn, self._stage_all_btn,
                  self._push_btn, self._pull_btn):
            w.setEnabled(on)

    def _make_item(self, f: GitFile) -> QListWidgetItem:
        c = get_design_system().colors
        name = Path(f.path).name
        folder = str(Path(f.path).parent) if str(Path(f.path).parent) != "." else ""
        item = QListWidgetItem(f"{f.label}  {name}    {folder}")
        item.setData(Qt.UserRole, f.path)
        tone = {"U": c.info, "A": c.success, "M": c.warning,
                "D": c.error, "R": c.info}.get(f.label, c.text_secondary)
        from PySide6.QtGui import QColor
        item.setForeground(QColor(tone))
        item.setToolTip(f.path)
        return item

    # -- actions -------------------------------------------------------------
    def _selected_paths(self, listw: QListWidget) -> list[str]:
        return [it.data(Qt.UserRole) for it in listw.selectedItems()]

    def _stage(self, item: QListWidgetItem):
        if self._service:
            self._service.stage([item.data(Qt.UserRole)])
            self.refresh()

    def _unstage(self, item: QListWidgetItem):
        if self._service:
            self._service.unstage([item.data(Qt.UserRole)])
            self.refresh()

    def _on_stage_all(self):
        if self._service:
            self._service.stage_all()
            self.refresh()

    def _on_commit(self):
        if not self._service:
            return
        msg = self._commit_msg.toPlainText().strip()
        if not msg:
            self.toast.emit("Enter a commit message first.", "warning")
            return
        if self._staged.count() == 0:
            self._service.stage_all()
        ok, out = self._service.commit(msg)
        if ok:
            self._commit_msg.clear()
            self.toast.emit("Committed.", "success")
        else:
            self.toast.emit(f"Commit failed: {out.strip()[:200]}", "error")
        self.refresh()

    def _on_push(self):
        self.push()

    def _on_pull(self):
        self.pull()

    def push(self):
        if not self._service:
            self.toast.emit("Open a Git repository before pushing.", "warning")
            return
        self.toast.emit("Pushing…", "info")
        self._run_async(self._service.push,
                        lambda r: self._on_remote_done("Push", r))

    def pull(self):
        if not self._service:
            self.toast.emit("Open a Git repository before pulling.", "warning")
            return
        self.toast.emit("Pulling…", "info")
        self._run_async(self._service.pull,
                        lambda r: self._on_remote_done("Pull", r))

    def _on_remote_done(self, label: str, result):
        ok, out = result
        self.toast.emit(f"{label} {'succeeded' if ok else 'failed'}: {out.strip()[:200]}",
                        "success" if ok else "error")
        self.refresh()

    def _show_diff(self, item: QListWidgetItem, staged: bool):
        if not self._service:
            return
        path = item.data(Qt.UserRole)
        diff = self._service.diff(path, staged=staged)
        if diff.strip():
            self.diff_requested.emit(f"{Path(path).name} (diff)", diff)
        else:
            self.file_open_requested.emit(str(Path(self._root) / path))

    def eventFilter(self, obj, event):
        if obj is self._commit_msg and event.type() == event.Type.KeyPress:
            if (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                    and event.modifiers() & Qt.ControlModifier):
                self._on_commit()
                return True
        return super().eventFilter(obj, event)

    # -- style ---------------------------------------------------------------
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #GitPanel {{ background: {c.surface}; }}
            #GitAccountCard {{
                background: {c.surface_raised};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.md}px;
            }}
            #GitAccountLabel {{
                color: {c.text_secondary};
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            #GitPanel QPushButton {{
                padding: 5px 8px;
                font-size: {FontSize.tiny}px;
            }}
            #CommitMessage {{
                background: {c.surface_inset}; color: {c.text_primary};
                border: 1px solid {c.border_subtle}; border-radius: {Radius.sm}px;
                margin: 0 {Spacing.md}px; padding: 6px;
                font-size: {FontSize.small}px;
            }}
            #GitList {{
                background: {c.surface}; color: {c.text_secondary};
                border: none; font-size: {FontSize.small}px; outline: none;
                padding: 0 {Spacing.xs}px;
            }}
            #GitList::item {{ padding: 4px 8px; border-radius: {Radius.sm}px; }}
            #GitList::item:hover {{ background: {c.surface_raised}; color: {c.text_primary}; }}
            #GitList::item:selected {{ background: {c.selection}; color: {c.text_primary}; }}
        """)

    def refresh_theme(self):
        self._apply_style()


# ============================================================================
# SECTION: ui.panels.run_panel (ui/panels/run_panel.py)
# ============================================================================
"""
Run & Debug panel — v1.2

A clean control surface over `core.run_manager.RunManager`. Shows the
detected run configuration for the current file / project, offers Run, Quick
Test, and Stop buttons in a non-clipping flex row, and reflects process state
in the header pill.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, FontSize, Radius
from ui.widgets.controls import SectionHeader, TextButton, IconButton, Pill


class RunPanel(QFrame):

    toast = Signal(str, str)

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.setObjectName("RunPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._bus = event_bus
        self._root = ""
        self._current_file = ""
        self._running = False
        self._build()
        self._apply_style()
        if self._bus is not None:
            self._bus.subscribe("process_output", self._on_output)
            self._bus.subscribe("process_finished", self._on_finished)
            self._bus.subscribe("log_message", self._on_log)

    # -- construction --------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(Spacing.xs)

        header = SectionHeader("Run & Debug")
        self._status = Pill("Idle", "muted")
        self._refresh_btn = IconButton("refresh", "Re-detect configuration", size=24, icon_size=14)
        self._refresh_btn.clicked.connect(self._update_config)
        header.add_action(self._status)
        header.add_action(self._refresh_btn)
        lay.addWidget(header)

        row = QWidget()
        rr = QHBoxLayout(row)
        rr.setContentsMargins(Spacing.md, Spacing.xs, Spacing.md, Spacing.xs)
        rr.setSpacing(Spacing.xs)
        self._run_btn = TextButton("Run", icon_name="play", variant="primary", tooltip="Run current file in Interactive Terminal  (F5)")
        self._run_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._run_btn.clicked.connect(self._on_run)
        self._test_btn = TextButton("Test", icon_name="flask")
        self._test_btn.setToolTip("Quick Test with auto-detected dummy inputs  (F6)")
        self._test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._test_btn.clicked.connect(self._on_test)
        self._stop_btn = TextButton("Stop", icon_name="square", tooltip="Stop currently running process  (Shift+F5)")
        self._stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        rr.addWidget(self._run_btn, 1)
        rr.addWidget(self._test_btn, 1)
        rr.addWidget(self._stop_btn, 1)
        lay.addWidget(row)

        self._config_label = QLabel("No file selected.")
        self._config_label.setProperty("role", "muted")
        self._config_label.setWordWrap(True)
        self._config_label.setContentsMargins(Spacing.md, 0, Spacing.md, Spacing.xs)
        lay.addWidget(self._config_label)

        self._log = QPlainTextEdit()
        self._log.setObjectName("RunLog")
        self._log.setReadOnly(True)
        lay.addWidget(self._log, 1)

    # -- public API ----------------------------------------------------------
    def set_root(self, path: str):
        self._root = str(path or "")
        self._update_config()

    def set_current_file(self, path: str):
        self._current_file = str(path or "")
        self._update_config()

    # -- config detection ----------------------------------------------------
    def _detect(self):
        try:
            from core.run_manager import RunManager
            rm = RunManager.__new__(RunManager)
            if self._current_file:
                cfg = rm.detect_file_run_config(Path(self._current_file))
                if cfg:
                    return cfg
            if self._root:
                return rm.detect_project_run_config(Path(self._root))
        except Exception:
            return None
        return None

    def _update_config(self):
        cfg = self._detect()
        if cfg is not None:
            cmd = " ".join(cfg.command)
            self._config_label.setText(f"{cfg.name}\n{cmd}")
            self._run_btn.setEnabled(not self._running)
            self._test_btn.setEnabled(not self._running)
        else:
            where = self._current_file or self._root
            self._config_label.setText(
                "No run configuration detected."
                if where else "Open a file or folder to run.")
            self._run_btn.setEnabled(bool(where) and not self._running)
            self._test_btn.setEnabled(bool(where) and not self._running)

    # -- actions -------------------------------------------------------------
    def _on_run(self):
        if self._bus is None:
            self.toast.emit("Run backend is not connected.", "warning")
            return
        self._log.clear()
        self._set_running(True)
        data = {"file_path": self._current_file} if self._current_file else {}
        self._bus.publish("run_requested", data)

    def _on_test(self):
        if self._bus is None:
            self.toast.emit("Test backend is not connected.", "warning")
            return
        self._log.clear()
        self._set_running(True)
        data = {"file_path": self._current_file} if self._current_file else {}
        self._bus.publish("test_requested", data)

    def _on_stop(self):
        if self._bus is not None:
            self._bus.publish("stop_requested", {})

    def _set_running(self, on: bool):
        self._running = on
        self._run_btn.setEnabled(not on)
        self._test_btn.setEnabled(not on)
        self._stop_btn.setEnabled(on)
        self._status.set_tone("info" if on else "muted")
        self._status.setText("Running" if on else "Idle")

    # -- bus handlers --------------------------------------------------------
    def _on_output(self, data: dict):
        text = data.get("output", "")
        if text:
            self._log.appendPlainText(text.rstrip("\n"))

    def _on_finished(self, data: dict):
        code = data.get("exit_code", 0)
        self._set_running(False)
        self._status.set_tone("success" if code == 0 else "error")
        self._status.setText("Exit 0" if code == 0 else f"Exit {code}")

    def _on_log(self, data: dict):
        msg = data.get("message", "")
        if msg:
            self._log.appendPlainText(msg)

    # -- style ---------------------------------------------------------------
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #RunPanel {{ background: {c.surface}; }}
            #RunPanel QPushButton {{
                padding: 5px 8px;
                font-size: {FontSize.tiny}px;
            }}
            #RunLog {{
                background: {c.surface_inset}; color: {c.text_secondary};
                border: 1px solid {c.border_subtle};
                margin: 0 {Spacing.md}px {Spacing.md}px {Spacing.md}px;
                border-radius: {Radius.sm}px; padding: 6px;
                font-family: monospace; font-size: {FontSize.small}px;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        self._status.refresh_theme()


# ============================================================================
# SECTION: ui.panels.test_panel (ui/panels/test_panel.py)
# ============================================================================
"""
Program & Terminal Tests Panel — v3.0 (Compact Sidebar-Optimized Layout)

Left-sidebar panel for testing any program or algorithm in any language, plus
in-app terminal diagnostics. Designed specifically for narrow sidebar widths
(220px–320px) so zero labels, spinboxes, checkboxes, or buttons ever clip.
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QLineEdit, QPlainTextEdit, QScrollArea, QSizePolicy,
    QAbstractSpinBox,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, FontSize, Radius
from ui.widgets.controls import SectionHeader, TextButton, IconButton, Pill, hline
from core.program_tester import (
    analyze_program,
    generate_test_inputs,
    ProgramInputProfile,
)


def _compact_spin(min_v: int, max_v: int, val: int, tip: str = "") -> QSpinBox:
    """Create a clean, compact spinbox without oversized native arrow buttons."""
    sb = QSpinBox()
    sb.setRange(min_v, max_v)
    sb.setValue(val)
    sb.setButtonSymbols(QAbstractSpinBox.PlusMinus)
    sb.setMinimumWidth(0)
    sb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    if tip:
        sb.setToolTip(tip)
    return sb


class TestPanel(QFrame):
    """Left sidebar panel for customizable & automated program and terminal testing."""

    toast = Signal(str, str)
    quick_test_requested = Signal()
    custom_test_requested = Signal(dict)
    terminal_test_requested = Signal()

    _MODES = [
        ("auto", "Auto-Detect (Smart)"),
        ("array", "Array (N Elements)"),
        ("entity", "Student / Entity Records"),
        ("menu", "Menu Loop (Stack / CRUD)"),
        ("sequence", "Sequential Inputs"),
        ("raw", "Manual Raw Stdin"),
    ]

    _VALUE_TYPES = [
        ("auto", "Auto (Match Code)"),
        ("int", "Random Integers"),
        ("sorted_int", "Sorted Ints (Binary Search)"),
        ("float", "Random Decimals"),
        ("name", "Full Names"),
        ("string", "Random Words"),
        ("student_preset", "Student (Name, Age, ID, Marks)"),
        ("employee_preset", "Employee (Name, ID, Age, Salary)"),
    ]

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.setObjectName("TestPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._bus = event_bus
        self._root = ""
        self._current_file = ""
        self._code_provider: Optional[Callable[[], str]] = None
        self._running = False
        self._last_profile: Optional[ProgramInputProfile] = None

        self._build()
        self._apply_style()

        if self._bus is not None:
            self._bus.subscribe("test_finished", self._on_test_finished)
            self._bus.subscribe("terminal_test_finished", self._on_terminal_test_finished)
            self._bus.subscribe("process_finished", self._on_process_finished)

    # ------------------------------------------------------------------ #
    #  Construction                                                        #
    # ------------------------------------------------------------------ #
    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = SectionHeader("Tests")
        self._status = Pill("Idle", "muted")
        self._detect_btn = IconButton("refresh", "Auto-detect inputs from active code", size=24, icon_size=14)
        self._detect_btn.clicked.connect(self.refresh_detection)
        header.add_action(self._status)
        header.add_action(self._detect_btn)
        outer.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        host = QWidget()
        host.setObjectName("TestPanelHost")
        host.setMinimumWidth(0)
        lay = QVBoxLayout(host)
        lay.setContentsMargins(Spacing.md, Spacing.sm, Spacing.md, Spacing.md)
        lay.setSpacing(Spacing.sm)

        # ── Top primary actions (equal 1:1 flex width, never clips) ──
        top_row = QHBoxLayout()
        top_row.setSpacing(Spacing.xs)
        self._quick_btn = TextButton("Quick Test", icon_name="flask", variant="primary")
        self._quick_btn.setToolTip(
            "Auto-detect required inputs, pass random dummy values, and test program  (F6)"
        )
        self._quick_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._quick_btn.clicked.connect(self._on_quick_test)

        self._custom_btn = TextButton("Run Custom", icon_name="play")
        self._custom_btn.setToolTip("Run test using the customized input settings below")
        self._custom_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._custom_btn.clicked.connect(self._on_custom_test)

        top_row.addWidget(self._quick_btn, 1)
        top_row.addWidget(self._custom_btn, 1)
        lay.addLayout(top_row)

        # ── Detected profile summary ─────────────────────────────────
        self._profile_label = QLabel("Open a code file to auto-detect its input structure.")
        self._profile_label.setObjectName("TestProfileBanner")
        self._profile_label.setWordWrap(True)
        self._profile_label.setMinimumWidth(0)
        lay.addWidget(self._profile_label)

        lay.addWidget(hline())

        # ── Customization Controls (Sidebar-fitted 2-col layout) ─────
        cfg_title = QLabel("CUSTOMIZE TEST INPUTS")
        cfg_title.setProperty("role", "subheading")
        lay.addWidget(cfg_title)

        combo_grid = QGridLayout()
        combo_grid.setContentsMargins(0, 0, 0, 0)
        combo_grid.setHorizontalSpacing(Spacing.sm)
        combo_grid.setVerticalSpacing(Spacing.xs)

        lbl_mode = QLabel("Mode")
        lbl_mode.setObjectName("FieldCap")
        self._mode_combo = QComboBox()
        self._mode_combo.setMinimumWidth(0)
        self._mode_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        for key, label in self._MODES:
            self._mode_combo.addItem(label, key)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        combo_grid.addWidget(lbl_mode, 0, 0)
        combo_grid.addWidget(self._mode_combo, 0, 1)

        lbl_type = QLabel("Type")
        lbl_type.setObjectName("FieldCap")
        self._type_combo = QComboBox()
        self._type_combo.setMinimumWidth(0)
        self._type_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        for key, label in self._VALUE_TYPES:
            self._type_combo.addItem(label, key)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        combo_grid.addWidget(lbl_type, 1, 0)
        combo_grid.addWidget(self._type_combo, 1, 1)
        combo_grid.setColumnStretch(1, 1)
        lay.addLayout(combo_grid)

        # Compact 2x2 numeric grid with labels above spinboxes so nothing overflows
        num_grid = QGridLayout()
        num_grid.setContentsMargins(0, 2, 0, 0)
        num_grid.setHorizontalSpacing(Spacing.sm)
        num_grid.setVerticalSpacing(2)

        c_lbl = QLabel("Count / Ops (N)"); c_lbl.setObjectName("FieldCap")
        r_lbl = QLabel("Batch Runs"); r_lbl.setObjectName("FieldCap")
        num_grid.addWidget(c_lbl, 0, 0)
        num_grid.addWidget(r_lbl, 0, 1)

        self._count_spin = _compact_spin(
            1, 500, 10, "Number of elements, student records, or menu operations to generate"
        )
        self._scenarios_spin = _compact_spin(
            1, 10, 1, "Number of randomized test scenarios to run in a batch"
        )
        num_grid.addWidget(self._count_spin, 1, 0)
        num_grid.addWidget(self._scenarios_spin, 1, 1)

        min_lbl = QLabel("Min Value"); min_lbl.setObjectName("FieldCap")
        max_lbl = QLabel("Max Value"); max_lbl.setObjectName("FieldCap")
        num_grid.addWidget(min_lbl, 2, 0)
        num_grid.addWidget(max_lbl, 2, 1)

        self._min_spin = _compact_spin(-10000, 100000, 10, "Minimum random numeric value")
        self._max_spin = _compact_spin(-10000, 100000, 99, "Maximum random numeric value")
        num_grid.addWidget(self._min_spin, 3, 0)
        num_grid.addWidget(self._max_spin, 3, 1)
        num_grid.setColumnStretch(0, 1)
        num_grid.setColumnStretch(1, 1)
        lay.addLayout(num_grid)

        # Checkboxes stacked cleanly in a compact 2-col row with short labels
        chk_row = QHBoxLayout()
        chk_row.setContentsMargins(0, 2, 0, 0)
        chk_row.setSpacing(Spacing.sm)
        self._prefix_chk = QCheckBox("Send N First")
        self._prefix_chk.setToolTip("Send the number of elements/records (N) on the first line of stdin")
        self._prefix_chk.setChecked(True)
        self._target_chk = QCheckBox("Search Key")
        self._target_chk.setToolTip("Append a search target value at the end (for linear/binary search)")
        chk_row.addWidget(self._prefix_chk, 1)
        chk_row.addWidget(self._target_chk, 1)
        lay.addLayout(chk_row)

        # Entity / Object Fields row
        self._fields_box = QWidget()
        self._fields_box.setMinimumWidth(0)
        flay = QVBoxLayout(self._fields_box)
        flay.setContentsMargins(0, 2, 0, 0)
        flay.setSpacing(2)
        f_lbl = QLabel("Record Fields (comma-separated):")
        f_lbl.setObjectName("FieldCap")
        flay.addWidget(f_lbl)
        self._fields_edit = QLineEdit("name, age, id, marks")
        self._fields_edit.setMinimumWidth(0)
        self._fields_edit.setPlaceholderText("name, age, id, marks")
        flay.addWidget(self._fields_edit)
        lay.addWidget(self._fields_box)

        # Menu Options row (Push, Pop, Peek, Show, Exit) with mini headers
        self._menu_box = QWidget()
        self._menu_box.setMinimumWidth(0)
        mlay = QVBoxLayout(self._menu_box)
        mlay.setContentsMargins(0, 2, 0, 0)
        mlay.setSpacing(2)
        m_lbl = QLabel("Menu Option Numbers:")
        m_lbl.setObjectName("FieldCap")
        mlay.addWidget(m_lbl)

        mgrid = QGridLayout()
        mgrid.setContentsMargins(0, 0, 0, 0)
        mgrid.setHorizontalSpacing(4)
        mgrid.setVerticalSpacing(1)
        self._menu_push = QLineEdit("1")
        self._menu_pop = QLineEdit("2")
        self._menu_peek = QLineEdit("3")
        self._menu_disp = QLineEdit("4")
        self._menu_exit = QLineEdit("5")
        menu_specs = [
            ("Push", self._menu_push),
            ("Pop", self._menu_pop),
            ("Peek", self._menu_peek),
            ("Show", self._menu_disp),
            ("Exit", self._menu_exit),
        ]
        for col_idx, (cap_text, edit_w) in enumerate(menu_specs):
            cap = QLabel(cap_text)
            cap.setObjectName("MicroCap")
            cap.setAlignment(Qt.AlignCenter)
            edit_w.setObjectName("MenuChoiceInput")
            edit_w.setMinimumWidth(0)
            edit_w.setAlignment(Qt.AlignCenter)
            edit_w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            mgrid.addWidget(cap, 0, col_idx)
            mgrid.addWidget(edit_w, 1, col_idx)
            mgrid.setColumnStretch(col_idx, 1)
        mlay.addLayout(mgrid)
        lay.addWidget(self._menu_box)

        # Sample preview & terminal test buttons (equal 1:1 flex width)
        sample_bar = QHBoxLayout()
        sample_bar.setContentsMargins(0, 2, 0, 0)
        sample_bar.setSpacing(Spacing.xs)
        self._sample_btn = TextButton("New Sample", icon_name="refresh")
        self._sample_btn.setToolTip("Generate a fresh random sample of dummy inputs below")
        self._sample_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._sample_btn.clicked.connect(self.generate_preview_sample)

        self._clear_log_btn = TextButton("Clear Log", icon_name="trash")
        self._clear_log_btn.setToolTip("Clear test result output below")
        self._clear_log_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._clear_log_btn.clicked.connect(lambda: self._log.clear())

        sample_bar.addWidget(self._sample_btn, 1)
        sample_bar.addWidget(self._clear_log_btn, 1)
        lay.addLayout(sample_bar)

        self._stdin_preview = QPlainTextEdit()
        self._stdin_preview.setObjectName("TestStdinPreview")
        self._stdin_preview.setMinimumWidth(0)
        self._stdin_preview.setPlaceholderText(
            "Generated dummy inputs appear here (or type custom stdin in Manual mode)…"
        )
        self._stdin_preview.setFixedHeight(80)
        lay.addWidget(self._stdin_preview)

        lay.addWidget(hline())

        # ── Concise Verdict & Diagnosis Banner ───────────────────────
        verdict_head = QLabel("TEST RESULT & QUICK FIX")
        verdict_head.setProperty("role", "subheading")
        lay.addWidget(verdict_head)

        self._verdict_box = QFrame()
        self._verdict_box.setObjectName("TestVerdictBox")
        self._verdict_box.setAttribute(Qt.WA_StyledBackground, True)
        self._verdict_box.setMinimumWidth(0)
        vlay = QVBoxLayout(self._verdict_box)
        vlay.setContentsMargins(Spacing.sm, Spacing.xs, Spacing.sm, Spacing.xs)
        vlay.setSpacing(2)
        self._verdict_title = QLabel("No test run yet.")
        self._verdict_title.setWordWrap(True)
        self._verdict_title.setMinimumWidth(0)
        self._verdict_fix = QLabel("")
        self._verdict_fix.setWordWrap(True)
        self._verdict_fix.setMinimumWidth(0)
        self._verdict_fix.setVisible(False)
        vlay.addWidget(self._verdict_title)
        vlay.addWidget(self._verdict_fix)
        lay.addWidget(self._verdict_box)

        self._log = QPlainTextEdit()
        self._log.setObjectName("TestResultLog")
        self._log.setReadOnly(True)
        self._log.setMinimumWidth(0)
        self._log.setMinimumHeight(160)
        lay.addWidget(self._log, 1)

        scroll.setWidget(host)
        outer.addWidget(scroll, 1)

        self._sync_mode_visibility()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def set_root(self, path: str):
        self._root = str(path or "")

    def set_code_provider(self, provider: Callable[[], str]):
        self._code_provider = provider

    def set_current_file(self, path: str):
        new_path = str(path or "")
        if new_path != self._current_file:
            self._current_file = new_path
            # Reset mode to Auto-Detect when switching files so the panel adapts to the new file's structure
            self._mode_combo.blockSignals(True)
            self._mode_combo.setCurrentIndex(0)
            self._mode_combo.blockSignals(False)
            self._sync_mode_visibility()
        self.refresh_detection()

    def refresh_detection(self):
        """Analyze the active file/buffer and update the detected profile & defaults."""
        code = ""
        if callable(self._code_provider):
            try:
                code = self._code_provider() or ""
            except Exception:
                code = ""
        if not code and self._current_file and Path(self._current_file).is_file():
            try:
                code = Path(self._current_file).read_text(encoding="utf-8", errors="replace")
            except Exception:
                code = ""

        if not code and not self._current_file:
            self._profile_label.setText("Open a code file to auto-detect its input structure.")
            self._last_profile = None
            return

        file_path = Path(self._current_file) if self._current_file else None
        profile = analyze_program(code, file_path)
        self._last_profile = profile
        self._profile_label.setText(f"Detected: {profile.summary}")

        if profile.fixed_count is not None:
            self._count_spin.setValue(profile.fixed_count)
        elif profile.count:
            self._count_spin.setValue(profile.count)
        self._prefix_chk.setChecked(bool(profile.has_count_prefix))
        self._target_chk.setChecked(bool(profile.needs_search_target))
        if profile.entity_fields:
            self._fields_edit.setText(", ".join(profile.entity_fields))
        if profile.menu_options:
            for opt in profile.menu_options:
                if opt.role == "push":
                    self._menu_push.setText(opt.choice)
                elif opt.role == "pop":
                    self._menu_pop.setText(opt.choice)
                elif opt.role == "peek":
                    self._menu_peek.setText(opt.choice)
                elif opt.role == "display":
                    self._menu_disp.setText(opt.choice)
                elif opt.role == "exit":
                    self._menu_exit.setText(opt.choice)
        self.generate_preview_sample()

    def build_custom_config(self, force_auto: bool = False) -> Dict[str, Any]:
        """Build the test configuration dictionary from the panel's controls."""
        if force_auto:
            return {"mode": "auto", "scenarios": int(self._scenarios_spin.value())}

        mode = self._mode_combo.currentData() or "auto"
        val_type = self._type_combo.currentData() or "auto"
        fields_text = self._fields_edit.text().strip()

        if val_type == "student_preset":
            val_type = "auto"
            if mode == "auto":
                mode = "entity"
            fields_text = "name, age, id, marks"
        elif val_type == "employee_preset":
            val_type = "auto"
            if mode == "auto":
                mode = "entity"
            fields_text = "name, id, age, salary, department"

        cfg: Dict[str, Any] = {
            "mode": mode,
            "value_type": val_type,
            "count": int(self._count_spin.value()),
            "scenarios": int(self._scenarios_spin.value()),
            "min_val": int(self._min_spin.value()),
            "max_val": int(self._max_spin.value()),
            "include_count_prefix": bool(self._prefix_chk.isChecked()),
            "include_search_target": bool(self._target_chk.isChecked()),
            "entity_fields": [f.strip() for f in fields_text.split(",") if f.strip()],
            "menu_push": self._menu_push.text().strip() or "1",
            "menu_pop": self._menu_pop.text().strip() or "2",
            "menu_peek": self._menu_peek.text().strip() or "3",
            "menu_display": self._menu_disp.text().strip() or "4",
            "menu_exit": self._menu_exit.text().strip() or "5",
            "override_menu_choices": (mode == "menu"),
        }
        if mode == "raw":
            cfg["raw_stdin"] = self._stdin_preview.toPlainText()
        return cfg

    def generate_preview_sample(self):
        """Generate a fresh random sample and display it in the preview box."""
        profile = self._last_profile
        if profile is None:
            profile = ProgramInputProfile(
                language="python",
                requires_input=True,
                mode="array_elements",
                summary="Default Sample",
                count=int(self._count_spin.value()),
                has_count_prefix=bool(self._prefix_chk.isChecked()),
            )
        mode = self._mode_combo.currentData() or "auto"
        if mode == "raw":
            return
        cfg = self.build_custom_config(force_auto=(mode == "auto"))
        case = generate_test_inputs(profile, cfg)
        self._stdin_preview.setPlainText(case.stdin_text.rstrip("\n"))

    # ------------------------------------------------------------------ #
    #  Internal UI events                                                  #
    # ------------------------------------------------------------------ #
    def _on_mode_changed(self, _idx: int):
        self._sync_mode_visibility()
        self.generate_preview_sample()

    def _on_type_changed(self, _idx: int):
        vtype = self._type_combo.currentData()
        if vtype == "student_preset":
            self._fields_edit.setText("name, age, id, marks")
        elif vtype == "employee_preset":
            self._fields_edit.setText("name, id, age, salary, department")
        self.generate_preview_sample()

    def _sync_mode_visibility(self):
        mode = self._mode_combo.currentData() or "auto"
        is_raw = (mode == "raw")
        self._fields_box.setVisible(mode in ("auto", "entity", "sequence"))
        self._menu_box.setVisible(mode in ("auto", "menu"))
        self._prefix_chk.setEnabled(not is_raw)
        self._target_chk.setEnabled(not is_raw)
        self._count_spin.setEnabled(not is_raw)

    def _on_quick_test(self):
        self.refresh_detection()
        self.set_running(True)
        self.quick_test_requested.emit()

    def _on_custom_test(self):
        cfg = self.build_custom_config(force_auto=False)
        self.set_running(True)
        self.custom_test_requested.emit(cfg)

    def _on_test_terminal(self):
        self.set_running(True)
        self.terminal_test_requested.emit()

    def set_running(self, running: bool):
        self._running = running
        self._quick_btn.setEnabled(not running)
        self._custom_btn.setEnabled(not running)
        if running:
            self._status.set_tone("info")
            self._status.setText("Testing…")

    # ------------------------------------------------------------------ #
    #  EventBus result handlers                                            #
    # ------------------------------------------------------------------ #
    def _on_test_finished(self, data: dict):
        self.set_running(False)
        ok = bool(data.get("success"))
        duration = data.get("duration_ms", 0.0)
        pattern = data.get("pattern_name", "")
        stdin_used = data.get("stdin_text", "")
        if stdin_used and (self._mode_combo.currentData() or "auto") != "raw":
            self._stdin_preview.setPlainText(stdin_used.rstrip("\n"))

        c = get_design_system().colors
        if ok:
            self._status.set_tone("success")
            self._status.setText("Passed")
            self._verdict_title.setText(
                f"✓ Code ran and tested successfully! ({duration:.1f} ms · {pattern})"
            )
            self._verdict_title.setStyleSheet(f"color: {c.success}; font-weight: 600;")
            self._verdict_fix.setVisible(False)
            self._verdict_box.setStyleSheet(
                f"#TestVerdictBox {{ background: {c.success_muted}; border: 1px solid {c.success}; border-radius: {Radius.sm}px; }}"
            )
        else:
            self._status.set_tone("error")
            self._status.setText("Failed")
            issue = data.get("issue_summary") or "Program exited with an error."
            fix = data.get("quick_fix") or "Inspect the error line in Output."
            self._verdict_title.setText(f"✗ Issue: {issue}")
            self._verdict_title.setStyleSheet(f"color: {c.error}; font-weight: 600;")
            self._verdict_fix.setText(f"💡 Fix: {fix}")
            self._verdict_fix.setStyleSheet(f"color: {c.text_primary}; font-size: {FontSize.tiny}px;")
            self._verdict_fix.setVisible(True)
            self._verdict_box.setStyleSheet(
                f"#TestVerdictBox {{ background: {c.error_muted}; border: 1px solid {c.error}; border-radius: {Radius.sm}px; }}"
            )

        report = data.get("formatted_output", "")
        if report:
            self._log.setPlainText(report)

    def _on_terminal_test_finished(self, data: dict):
        self.set_running(False)
        ok = bool(data.get("passed"))
        c = get_design_system().colors
        if ok:
            self._status.set_tone("success")
            self._status.setText("Term OK")
            self._verdict_title.setText(
                f"✓ Terminal tested ({data.get('shell', 'shell')} · {data.get('latency_ms', 0):.1f} ms · 0 popup windows)"
            )
            self._verdict_title.setStyleSheet(f"color: {c.success}; font-weight: 600;")
            self._verdict_fix.setVisible(False)
            self._verdict_box.setStyleSheet(
                f"#TestVerdictBox {{ background: {c.success_muted}; border: 1px solid {c.success}; border-radius: {Radius.sm}px; }}"
            )
        else:
            self._status.set_tone("error")
            self._status.setText("Term Err")
            self._verdict_title.setText("✗ Issue: Integrated shell failed self-test.")
            self._verdict_title.setStyleSheet(f"color: {c.error}; font-weight: 600;")
            self._verdict_fix.setText("💡 Fix: Check Settings → Terminal → Default Shell.")
            self._verdict_fix.setVisible(True)

        report = data.get("formatted_report", "")
        if report:
            self._log.setPlainText(report)

    def _on_process_finished(self, _data: dict):
        if self._running:
            self.set_running(False)

    # ------------------------------------------------------------------ #
    #  Styling                                                             #
    # ------------------------------------------------------------------ #
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #TestPanel, #TestPanelHost {{
                background: {c.surface};
            }}
            #TestProfileBanner {{
                background: {c.surface_raised};
                color: {c.text_secondary};
                border: 1px solid {c.border_subtle};
                border-left: 3px solid {c.accent};
                border-radius: {Radius.sm}px;
                padding: 5px 8px;
                font-size: {FontSize.tiny}px;
            }}
            #FieldCap {{
                color: {c.text_muted};
                font-size: {FontSize.tiny}px;
                font-weight: 500;
            }}
            #MicroCap {{
                color: {c.text_faint};
                font-size: {FontSize.micro}px;
                font-weight: 600;
            }}
            #MenuChoiceInput {{
                background: {c.surface_inset};
                color: {c.text_primary};
                border: 1px solid {c.border};
                border-radius: {Radius.sm}px;
                padding: 3px 2px;
                font-size: {FontSize.tiny}px;
                font-weight: 600;
            }}
            #TestPanel QPushButton {{
                padding: 5px 8px;
                font-size: {FontSize.tiny}px;
            }}
            #TestPanel QComboBox {{
                padding: 4px 6px;
                font-size: {FontSize.tiny}px;
                min-height: 18px;
            }}
            #TestPanel QSpinBox {{
                padding: 3px 6px;
                font-size: {FontSize.tiny}px;
            }}
            #TestPanel QCheckBox {{
                font-size: {FontSize.tiny}px;
                spacing: 5px;
            }}
            #TestPanel QLineEdit {{
                padding: 4px 6px;
                font-size: {FontSize.tiny}px;
            }}
            #TestVerdictBox {{
                background: {c.surface_raised};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
            }}
            #TestStdinPreview, #TestResultLog {{
                background: {c.surface_inset};
                color: {c.text_secondary};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
                padding: 5px;
                font-family: monospace;
                font-size: {FontSize.tiny}px;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        self._status.refresh_theme()


# ============================================================================
# SECTION: ui.panels.tasks_panel (ui/panels/tasks_panel.py)
# ============================================================================
"""
Tasks panel — v2.0

A live activity monitor for the assistant, program runner, and smart tester.
Renders each task as a clean two-row card with a status badge, timestamp, and
non-clipping task title so filenames never overlap or get cut off vertically.
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QSizePolicy,
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFontMetrics

from ui.design_system import get_design_system, Spacing, FontSize, Radius
from ui.widgets.controls import SectionHeader, IconButton, Pill


class _TaskRow(QFrame):
    """Two-row task activity card: [Status Pill + Timestamp] on top, full title below."""

    def __init__(self, title: str, tone: str, status: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskRowCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(Spacing.md, 8, Spacing.md, 8)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(Spacing.xs)
        self.chip = Pill(status, tone)
        self.time = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.time.setObjectName("TaskTime")
        self.time.setToolTip("Task timestamp")
        top.addWidget(self.chip, 0, Qt.AlignLeft | Qt.AlignVCenter)
        top.addStretch(1)
        top.addWidget(self.time, 0, Qt.AlignRight | Qt.AlignVCenter)
        lay.addLayout(top)

        self.title = QLabel(title)
        self.title.setObjectName("TaskTitle")
        self.title.setWordWrap(True)
        self.title.setToolTip(title)
        lay.addWidget(self.title)

        self._apply_style()
        self._update_height()

    def set_title(self, text: str):
        self.title.setText(text)
        self.title.setToolTip(text)
        self._update_height()

    def set_status(self, tone: str, status: str):
        self.chip.set_tone(tone)
        self.chip.setText(status)

    def _update_height(self):
        fm = QFontMetrics(self.title.font())
        rect = fm.boundingRect(0, 0, 210, 400, int(Qt.TextWordWrap | Qt.AlignLeft), self.title.text())
        text_h = max(20, rect.height() + 4)
        self.title.setMinimumHeight(text_h)
        self.setMinimumHeight(text_h + 38)

    def preferred_size(self) -> QSize:
        self._update_height()
        return QSize(220, max(62, self.minimumHeight() + 4))

    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #TaskRowCard {{
                background: {c.surface_raised};
                border: 1px solid {c.border_subtle};
                border-radius: {Radius.sm}px;
            }}
            #TaskTitle {{
                color: {c.text_primary};
                font-size: {FontSize.small}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
            #TaskTime {{
                color: {c.text_muted};
                font-size: {FontSize.tiny}px;
                background: transparent;
                border: none;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        self.chip.refresh_theme()


class TasksPanel(QFrame):

    toast = Signal(str, str)

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.setObjectName("TasksPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._bus = event_bus
        self._active_ai: tuple[QListWidgetItem, _TaskRow] | None = None
        self._active_run: tuple[QListWidgetItem, _TaskRow] | None = None
        self._build()
        self._apply_style()
        if self._bus is not None:
            self._bus.subscribe("ai_chat_streaming_started", self._on_ai_started)
            self._bus.subscribe("ai_chat_streaming_complete", self._on_ai_complete)
            self._bus.subscribe("ai_chat_error", self._on_ai_error)
            self._bus.subscribe("run_started", self._on_run_started)
            self._bus.subscribe("test_requested", self._on_test_started)
            self._bus.subscribe("process_finished", self._on_run_finished)

    # -- construction --------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = SectionHeader("Tasks")
        self._clear_btn = IconButton("trash", "Clear all task activity", size=24, icon_size=15)
        self._clear_btn.clicked.connect(self._clear)
        header.add_action(self._clear_btn)
        lay.addWidget(header)

        self._list = QListWidget()
        self._list.setObjectName("TasksList")
        self._list.setSelectionMode(QListWidget.NoSelection)
        self._list.setSpacing(4)
        lay.addWidget(self._list, 1)

        self._empty = QLabel("No activity yet. Program runs, tests, and AI tasks appear here.")
        self._empty.setProperty("role", "muted")
        self._empty.setWordWrap(True)
        self._empty.setAlignment(Qt.AlignTop)
        self._empty.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.lg)
        lay.addWidget(self._empty)

    # -- rows ----------------------------------------------------------------
    def _add_row(self, title: str, tone: str, status: str) -> tuple[QListWidgetItem, _TaskRow]:
        self._empty.setVisible(False)
        row = _TaskRow(title, tone, status)
        item = QListWidgetItem()
        item.setSizeHint(row.preferred_size())
        self._list.insertItem(0, item)
        self._list.setItemWidget(item, row)
        return item, row

    def _clear(self):
        self._list.clear()
        self._active_ai = None
        self._active_run = None
        self._empty.setVisible(True)

    # -- AI lifecycle --------------------------------------------------------
    def _on_ai_started(self, data: dict):
        model = (data or {}).get("model_id", "") or (data or {}).get("model", "")
        title = f"AI Assistant{f' · {model}' if model else ''}"
        self._active_ai = self._add_row(title, "info", "Running")

    def _on_ai_complete(self, data: dict):
        if self._active_ai is not None:
            item, row = self._active_ai
            row.set_status("success", "Done")
            row.set_title("AI Assistant response complete")
            item.setSizeHint(row.preferred_size())
            self._active_ai = None
        else:
            self._add_row("AI Assistant response complete", "success", "Done")

    def _on_ai_error(self, data: dict):
        msg = (data or {}).get("error", "Assistant error")
        if self._active_ai is not None:
            item, row = self._active_ai
            row.set_status("error", "Failed")
            row.set_title(str(msg)[:120])
            item.setSizeHint(row.preferred_size())
            self._active_ai = None
        else:
            self._add_row(str(msg)[:120], "error", "Failed")

    # -- Run & Test lifecycle ------------------------------------------------
    def _on_run_started(self, data: dict):
        name = (data or {}).get("name") or Path((data or {}).get("file_path", "program")).name
        self._active_run = self._add_row(f"▶ {name}", "info", "Running")

    def _on_test_started(self, data: dict):
        fp = (data or {}).get("file_path") or "buffer"
        name = Path(fp).name if fp else "buffer"
        self._active_run = self._add_row(f"🧪 Test: {name}", "info", "Testing")

    def _on_run_finished(self, data: dict):
        code = (data or {}).get("exit_code", 0)
        stopped = bool((data or {}).get("stopped"))
        if stopped:
            tone, status = "warning", "Stopped"
        elif code == 0:
            tone, status = "success", "Success"
        else:
            tone, status = "error", f"Exit {code}"

        if self._active_run is not None:
            item, row = self._active_run
            row.set_status(tone, status)
            item.setSizeHint(row.preferred_size())
            self._active_run = None
        else:
            self._add_row("Process finished", tone, status)

    # -- style ---------------------------------------------------------------
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #TasksPanel {{ background: {c.surface}; }}
            #TasksList {{
                background: {c.surface};
                border: none;
                outline: none;
                padding: 6px 8px;
                font-size: {FontSize.small}px;
            }}
            #TasksList::item {{
                border: none;
                margin-bottom: 4px;
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        for i in range(self._list.count()):
            w = self._list.itemWidget(self._list.item(i))
            if isinstance(w, _TaskRow):
                w.refresh_theme()


# ============================================================================
# SECTION: ui.panels.memory_panel (ui/panels/memory_panel.py)
# ============================================================================
"""
Project Memory panel — v1.0

Surfaces what the assistant remembers about the open project (from
`ai.memory.project_memory.ProjectMemory`, disk-backed at
config/project_memory.json). Facts can be added, pinned, edited and forgotten.

Signals
  toast(str, str)  — (message, level)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QLineEdit, QInputDialog,
)
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, FontSize
from ui.widgets.controls import SectionHeader, IconButton, Pill


_CATEGORY_TONE = {
    "architecture": "accent", "issue": "error", "convention": "info",
    "file": "success", "general": "muted",
}


class _FactRow(QWidget):
    """A single remembered fact with pin / edit / forget controls."""

    pin_toggled = Signal(str, bool)     # (fact_id, pinned)
    edit_requested = Signal(str)        # fact_id
    forget_requested = Signal(str)      # fact_id

    def __init__(self, fact, parent=None):
        super().__init__(parent)
        self._fact = fact
        pinned = bool(fact.metadata.get("pinned"))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(Spacing.lg, 4, Spacing.sm, 4)
        lay.setSpacing(Spacing.sm)

        chip = Pill(fact.category, _CATEGORY_TONE.get(fact.category, "muted"))
        body = QLabel(fact.content)
        body.setWordWrap(True)
        body.setProperty("role", "body")

        self._pin = IconButton("star", "Unpin" if pinned else "Pin",
                               size=22, icon_size=13, checkable=True)
        self._pin.setChecked(pinned)
        self._pin.toggled.connect(lambda on: self.pin_toggled.emit(self._fact.fact_id, on))
        edit = IconButton("edit", "Edit", size=22, icon_size=13)
        edit.clicked.connect(lambda: self.edit_requested.emit(self._fact.fact_id))
        forget = IconButton("trash", "Forget", size=22, icon_size=13)
        forget.clicked.connect(lambda: self.forget_requested.emit(self._fact.fact_id))

        lay.addWidget(chip)
        lay.addWidget(body, 1)
        lay.addWidget(self._pin)
        lay.addWidget(edit)
        lay.addWidget(forget)


class MemoryPanel(QWidget):

    toast = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MemoryPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._memory = None
        self._build()
        self._apply_style()
        QTimer.singleShot(300, self._load_memory)

    # -- construction --------------------------------------------------------
    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        header = SectionHeader("Project Memory")
        self._refresh_btn = IconButton("refresh", "Reload", size=24, icon_size=15)
        self._refresh_btn.clicked.connect(self.reload)
        self._clear_btn = IconButton("trash", "Forget everything", size=24, icon_size=15)
        self._clear_btn.clicked.connect(self._on_clear_all)
        for b in (self._refresh_btn, self._clear_btn):
            header.add_action(b)
        lay.addWidget(header)

        add_row = QWidget()
        ar = QHBoxLayout(add_row)
        ar.setContentsMargins(Spacing.lg, 0, Spacing.lg, Spacing.sm)
        ar.setSpacing(4)
        self._input = QLineEdit()
        self._input.setObjectName("MemoryInput")
        self._input.setPlaceholderText("Remember something about this project…")
        self._input.returnPressed.connect(self._on_add)
        add_btn = IconButton("plus", "Remember", size=24, icon_size=14)
        add_btn.clicked.connect(self._on_add)
        ar.addWidget(self._input, 1)
        ar.addWidget(add_btn)
        lay.addWidget(add_row)

        self._list = QListWidget()
        self._list.setObjectName("MemoryList")
        self._list.setSelectionMode(QListWidget.NoSelection)
        lay.addWidget(self._list, 1)

        self._empty = QLabel("Nothing remembered yet.")
        self._empty.setProperty("role", "muted")
        self._empty.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.lg)
        lay.addWidget(self._empty)

    # -- memory access -------------------------------------------------------
    def _load_memory(self):
        try:
            from ai.memory.project_memory import ProjectMemory
            self._memory = ProjectMemory()
        except Exception as e:
            self._memory = None
            self.toast.emit(f"Project memory unavailable: {e}", "warning")
        self.reload()

    def set_project(self, name: str, root: str):
        if self._memory is not None:
            try:
                self._memory.set_project(name, root)
            except Exception:
                pass
        self.reload()

    def reload(self):
        self._list.clear()
        if self._memory is None:
            self._empty.setText("Project memory backend is not available.")
            self._empty.setVisible(True)
            return
        facts = self._memory.get_all()
        # Pinned first, then most recent.
        facts.sort(key=lambda f: (not f.metadata.get("pinned"), f.timestamp),
                   reverse=False)
        facts.sort(key=lambda f: bool(f.metadata.get("pinned")), reverse=True)
        self._empty.setVisible(not facts)
        for fact in facts:
            row = _FactRow(fact)
            row.pin_toggled.connect(self._on_pin)
            row.edit_requested.connect(self._on_edit)
            row.forget_requested.connect(self._on_forget)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)

    # -- actions -------------------------------------------------------------
    def _on_add(self):
        text = self._input.text().strip()
        if not text or self._memory is None:
            return
        self._memory.remember(category="general", content=text, source="user")
        self._input.clear()
        self.reload()

    def _on_pin(self, fact_id: str, pinned: bool):
        if self._memory is not None:
            self._memory.set_pinned(fact_id, pinned)
            self.reload()

    def _on_edit(self, fact_id: str):
        if self._memory is None:
            return
        current = next((f.content for f in self._memory.get_all()
                        if f.fact_id == fact_id), "")
        text, ok = QInputDialog.getText(self, "Edit fact", "Content:",
                                        QLineEdit.Normal, current)
        if ok and text.strip():
            self._memory.update_content(fact_id, text.strip())
            self.reload()

    def _on_forget(self, fact_id: str):
        if self._memory is not None and self._memory.forget(fact_id):
            self.reload()

    def _on_clear_all(self):
        if self._memory is not None:
            self._memory.clear()
            self.reload()
            self.toast.emit("Cleared project memory.", "info")

    # -- style ---------------------------------------------------------------
    def _apply_style(self):
        c = get_design_system().colors
        self.setStyleSheet(f"""
            #MemoryPanel {{ background: {c.surface}; }}
            #MemoryInput {{
                background: {c.surface_inset}; color: {c.text_primary};
                border: 1px solid {c.border_subtle}; border-radius: 4px;
                padding: 4px 6px; font-size: {FontSize.small}px;
            }}
            #MemoryInput:focus {{ border: 1px solid {c.accent}; }}
            #MemoryList {{
                background: {c.surface}; border: none; outline: none;
                font-size: {FontSize.small}px;
            }}
            #MemoryList::item {{ border-bottom: 1px solid {c.border_subtle}; }}
        """)

    def refresh_theme(self):
        self._apply_style()
        for i in range(self._list.count()):
            w = self._list.itemWidget(self._list.item(i))
            if w is not None:
                from ui.widgets.controls import restyle_atoms
                restyle_atoms(w)


# ============================================================================
# SECTION: ui.panels.sidebar (ui/panels/sidebar.py)
# ============================================================================
"""
Sidebar — v2.3

The primary side panel. Holds a stack of views (Explorer plus the feature
panels: Search, GitHub / Git, Run & Debug, Tests, Tasks, Project Memory)
switched by the Activity Bar, and attaches a "Hide Sidebar (Ctrl+B)" action
button to each panel header so the user can collapse the sidebar at any time.
"""

from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QToolButton
from PySide6.QtCore import Qt, Signal

from ui.design_system import get_design_system, Spacing, FontSize
from ui.widgets.controls import SectionHeader, IconButton, restyle_atoms
from ui.panels.explorer import Explorer
from ui.panels.search_panel import SearchPanel
from ui.panels.git_panel import GitPanel
from ui.panels.run_panel import RunPanel
from ui.panels.test_panel import TestPanel
from ui.panels.tasks_panel import TasksPanel
from ui.panels.memory_panel import MemoryPanel


class PlaceholderView(QWidget):
    """A tidy placeholder for views still being wired up."""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(SectionHeader(title))
        body = QLabel(message)
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignTop)
        body.setContentsMargins(Spacing.lg, Spacing.md, Spacing.lg, Spacing.lg)
        lay.addWidget(body)
        lay.addStretch(1)


class Sidebar(QFrame):

    collapse_requested = Signal()
    view_selected = Signal(str)

    _TAB_ITEMS = (
        ("explorer", "Explorer"),
        ("search", "Search"),
        ("git", "Git"),
        ("run", "Run"),
        ("tests", "Tests"),
        ("tasks", "Tasks"),
    )

    def __init__(self, event_bus=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._event_bus = event_bus
        self._views: dict[str, QWidget] = {}
        self._tab_buttons: dict[str, QToolButton] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(1, 0, 1, 0)
        lay.setSpacing(0)

        # Top editorial navigation pill strip (Explorer | Search | GitHub | Run | Tests | Tasks | Memory)
        self._tab_bar = QFrame()
        self._tab_bar.setObjectName("SidebarTabBar")
        tb_lay = QHBoxLayout(self._tab_bar)
        tb_lay.setContentsMargins(8, 6, 8, 6)
        tb_lay.setSpacing(2)
        for vid, label in self._TAB_ITEMS:
            btn = QToolButton()
            btn.setObjectName("SidebarTabPill")
            btn.setText(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            try:
                fm_w = btn.fontMetrics().horizontalAdvance(label)
                btn.setMinimumWidth(max(36, fm_w + 18))
            except Exception:
                pass
            btn.clicked.connect(lambda _=False, v=vid: self._on_tab_pill_clicked(v))
            self._tab_buttons[vid] = btn
            tb_lay.addWidget(btn)
        tb_lay.addStretch(1)
        lay.addWidget(self._tab_bar)

        self._stack = QStackedWidget()
        lay.addWidget(self._stack, 1)

        # Bottom "Local Engine" hardware & VRAM card
        self._engine_card = QFrame()
        self._engine_card.setObjectName("LocalEngineCard")
        ec_lay = QVBoxLayout(self._engine_card)
        ec_lay.setContentsMargins(12, 10, 12, 10)
        ec_lay.setSpacing(3)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self._engine_title = QLabel("Local Engine")
        self._engine_title.setObjectName("LocalEngineTitle")
        self._engine_backend = QLabel("llama.cpp")
        self._engine_backend.setObjectName("LocalEngineBackend")
        top_row.addWidget(self._engine_title)
        top_row.addStretch(1)
        top_row.addWidget(self._engine_backend)
        ec_lay.addLayout(top_row)

        self._engine_model_lbl = QLabel("qwen2.5-coder-7b · 4.36 GB · 0.2s")
        self._engine_model_lbl.setObjectName("LocalEngineStats")
        ec_lay.addWidget(self._engine_model_lbl)

        self._engine_vram_lbl = QLabel("VRAM 5037 MB Active")
        self._engine_vram_lbl.setObjectName("LocalEngineVram")
        ec_lay.addWidget(self._engine_vram_lbl)

        card_wrap = QWidget()
        cw_lay = QVBoxLayout(card_wrap)
        cw_lay.setContentsMargins(10, 6, 10, 10)
        cw_lay.addWidget(self._engine_card)
        lay.addWidget(card_wrap)

        if self._event_bus is not None:
            self._event_bus.subscribe("ai_model_warm", self._on_engine_warm_event)
            self._event_bus.subscribe("ai_model_auto_selected", self._on_engine_model_selected)

        self.explorer = Explorer()
        self.search = SearchPanel()
        self.git = GitPanel()
        self.run = RunPanel(event_bus=event_bus)
        self.tests = TestPanel(event_bus=event_bus)
        self.tasks = TasksPanel(event_bus=event_bus)
        self.memory = MemoryPanel()

        self.add_view("explorer", self.explorer)
        self.add_view("search", self.search)
        self.add_view("git", self.git)
        self.add_view("run", self.run)
        self.add_view("tests", self.tests)
        self.add_view("tasks", self.tasks)
        self.add_view("memory", self.memory)
        self.set_view("explorer")

        self._apply_style()

    def add_view(self, view_id: str, widget: QWidget):
        self._views[view_id] = widget
        # Add a consistent "Hide Sidebar («)" button to every panel's SectionHeader
        header = widget.findChild(SectionHeader)
        if header is not None:
            hide_btn = IconButton(
                "chevron-left",
                "Hide Sidebar Panel — keep only left icon bar  (Ctrl+B)",
                size=24,
                icon_size=14,
            )
            hide_btn.clicked.connect(self.collapse_requested.emit)
            header.add_action(hide_btn)
        self._stack.addWidget(widget)

    def _on_tab_pill_clicked(self, view_id: str):
        self.set_view(view_id)
        self.view_selected.emit(view_id)

    def set_view(self, view_id: str):
        w = self._views.get(view_id)
        if w is not None:
            self._stack.setCurrentWidget(w)
        for vid, btn in self._tab_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(vid == view_id)
            btn.blockSignals(False)

    def _on_engine_model_selected(self, data: dict):
        model_id = (data or {}).get("model_id", "")
        if not model_id:
            return
        provider, sep, bare = model_id.partition(":")
        if sep:
            self._engine_backend.setText("llama.cpp" if provider == "llama_cpp" else provider)
            self._engine_model_lbl.setText(f"{bare} · local weights ready")

    def _on_engine_warm_event(self, data: dict):
        estimate = (data or {}).get("estimate") or {}
        backend = estimate.get("backend", "llama.cpp")
        size = estimate.get("model_size_gb", 4.36)
        load_s = (data or {}).get("load_seconds", 0.2)
        vram = estimate.get("vram_used_mb", 5037)
        model_name = estimate.get("model_name") or "qwen2.5-coder-7b"
        self._engine_backend.setText(str(backend))
        self._engine_model_lbl.setText(f"{model_name} · {size:.2f} GB · {load_s:.1f}s")
        if vram:
            self._engine_vram_lbl.setText(f"VRAM {vram} MB Active")

    def set_root(self, path: str):
        """Point every root-aware panel at the freshly opened workspace."""
        for panel in (self.search, self.git, self.run, self.tests):
            fn = getattr(panel, "set_root", None)
            if callable(fn):
                try:
                    fn(path)
                except Exception:
                    pass

    def _apply_style(self):
        c = get_design_system().colors
        active_pill_bg = c.text_primary if not c.is_dark else c.accent
        active_pill_fg = c.surface if not c.is_dark else c.text_on_accent
        self.setStyleSheet(f"""
            #Sidebar {{
                background-color: {c.surface};
                border-left: 1px solid {c.border};
                border-right: 1px solid {c.border};
            }}
            #SidebarTabBar {{
                background: {c.surface};
                border-bottom: 1px solid {c.border_subtle};
            }}
            #SidebarTabPill {{
                background: transparent;
                color: {c.text_secondary};
                border: none;
                border-radius: 4px;
                padding: 3px 7px;
                font-size: 11px;
                font-weight: 500;
            }}
            #SidebarTabPill:hover {{
                background: {c.surface_overlay};
                color: {c.text_primary};
            }}
            #SidebarTabPill:checked {{
                background: {active_pill_bg};
                color: {active_pill_fg};
                font-weight: 600;
            }}
            #LocalEngineCard {{
                background: {c.surface_raised};
                border: 1px solid {c.border};
                border-radius: 6px;
            }}
            #LocalEngineTitle {{
                font-weight: 700;
                font-size: 12px;
                color: {c.text_primary};
            }}
            #LocalEngineBackend {{
                font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                font-size: 11px;
                font-weight: 600;
                color: {c.accent};
            }}
            #LocalEngineStats {{
                font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                font-size: 10px;
                color: {c.text_muted};
            }}
            #LocalEngineVram {{
                font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
                font-size: 10px;
                font-weight: 600;
                color: {c.warning};
            }}
        """)

    def refresh_theme(self):
        self._apply_style()
        for panel in (self.explorer, self.search, self.git, self.run,
                      self.tests, self.tasks, self.memory):
            fn = getattr(panel, "refresh_theme", None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
        try:
            restyle_atoms(self)
        except Exception:
            pass

