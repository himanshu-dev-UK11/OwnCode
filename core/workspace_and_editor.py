"""
Consolidated Module: core.workspace_and_editor

Combines: core.workspace_manager, core.editor_manager
"""
from __future__ import annotations
import sys as _sys
import core  # ensure module alias resolver is active
for _alias in ['core.workspace_manager', 'core.editor_manager']:
    _sys.modules[_alias] = _sys.modules[__name__]


# ============================================================================
# SECTION: core.workspace_manager (core/workspace_manager.py)
# ============================================================================
"""
Workspace Manager — v3.0 (QFileSystemModel First Architecture)
Complete rewrite to prioritize explorer visibility before scanning!
Instrumented with detailed step-by-step logging for debugging.
"""
import json
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from core.logger import setup_logger

logger = setup_logger(__name__)


class _MetadataScanWorker(QObject):
    """Runs ProjectScanner.scan() in a background QThread to build metadata only."""
    scan_complete = Signal(object)  # emits ProjectContext
    scan_failed = Signal(str)       # emits error message

    def __init__(self, path: Path):
        super().__init__()
        self._path = path
        logger.info(f"[_MetadataScanWorker.__init__] Initialized for path: {path}")

    def run(self):
        logger.info(f"[_MetadataScanWorker.run] Starting metadata scan for path: {self._path}")
        try:
            logger.debug(f"[_MetadataScanWorker.run] Creating ProjectScanner instance...")
            scanner = ProjectScanner(self._path)
            logger.debug(f"[_MetadataScanWorker.run] ProjectScanner created, calling scan()...")
            context = scanner.scan()
            logger.info(f"[_MetadataScanWorker.run] Metadata scan complete, emitting scan_complete...")
            self.scan_complete.emit(context)
        except Exception as exc:
            logger.exception(f"[_MetadataScanWorker.run] Metadata scan failed with exception: {exc}")
            self.scan_failed.emit(str(exc))
        logger.info(f"[_MetadataScanWorker.run] Exiting run() method")


class Workspace:
    """Represents a single open workspace/project."""
    def __init__(self, path: Path, context=None, pinned: bool = False):
        self.path = path
        self.context = context
        self.pinned = pinned
        self.is_active = False
        self.scanning = False
        logger.debug(f"[Workspace.__init__] Created workspace for path: {path}")


class WorkspaceManager(QObject):
    """
    Manages workspaces and projects using QFileSystemModel first for instant UI!
    """

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus = event_bus

        self.recent_file = Path("config/recent_projects.json")
        self.pinned_file = Path("config/pinned_projects.json")
        self.session_file = Path("config/workspace_session.json")

        self.workspaces: List[Workspace] = []
        self.active_workspace: Optional[Workspace] = None
        self.recent_projects: List[str] = []
        self.pinned_projects: List[str] = []

        # Keep references so GC doesn't destroy running threads
        self._scan_threads: List[QThread] = []

        logger.info("[WorkspaceManager.__init__] Loading settings...")
        self._load_settings()
        logger.info("[WorkspaceManager.__init__] Subscribing to events...")
        self._subscribe_events()
        logger.info("[WorkspaceManager.__init__] Initialization complete!")

    def _subscribe_events(self):
        logger.debug("[WorkspaceManager._subscribe_events] Subscribing to request_open_workspace...")
        self.event_bus.subscribe("request_open_workspace", self._handle_open_request)
        self.event_bus.subscribe("request_close_workspace", self._handle_close_request)
        self.event_bus.subscribe("request_refresh_workspace", self._handle_refresh_request)
        self.event_bus.subscribe("request_reopen_last_workspace", self._handle_reopen_last)
        self.event_bus.subscribe("request_pin_project", self._handle_pin_project)
        self.event_bus.subscribe("request_unpin_project", self._handle_unpin_project)
        self.event_bus.subscribe("app_closing", self.save_session)
        logger.debug("[WorkspaceManager._subscribe_events] Event subscriptions complete!")

    def _load_settings(self):
        for attr, path in [("recent_projects", self.recent_file),
                           ("pinned_projects", self.pinned_file)]:
            try:
                if path.exists():
                    logger.debug(f"[WorkspaceManager._load_settings] Loading {attr} from {path}...")
                    with open(path, "r", encoding="utf-8") as f:
                        setattr(self, attr, json.load(f))
                    logger.debug(f"[WorkspaceManager._load_settings] Loaded {len(getattr(self, attr))} entries for {attr}")
                else:
                    logger.debug(f"[WorkspaceManager._load_settings] Settings file {path} does not exist, using defaults")
            except Exception as exc:
                logger.exception(f"[WorkspaceManager._load_settings] Failed to load {attr}: {exc}")
                setattr(self, attr, [])

    def _save_settings(self):
        for attr, path in [("recent_projects", self.recent_file),
                           ("pinned_projects", self.pinned_file)]:
            try:
                logger.debug(f"[WorkspaceManager._save_settings] Saving {attr} to {path}...")
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(getattr(self, attr), f, indent=4)
                logger.debug(f"[WorkspaceManager._save_settings] Saved {len(getattr(self, attr))} entries for {attr}")
            except Exception as exc:
                logger.exception(f"[WorkspaceManager._save_settings] Failed to save {attr}: {exc}")

    def save_session(self, _event_data=None):
        logger.info("[WorkspaceManager.save_session] Saving session...")
        try:
            data = {
                "last_workspace": str(self.active_workspace.path) if self.active_workspace else None,
                "open_workspaces": [str(ws.path) for ws in self.workspaces],
            }
            logger.debug(f"[WorkspaceManager.save_session] Session data: {data}")
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            logger.info("[WorkspaceManager.save_session] Session saved successfully!")
        except Exception as exc:
            logger.exception(f"[WorkspaceManager.save_session] Failed to save session: {exc}")

    def load_session(self):
        logger.info("[WorkspaceManager.load_session] Loading session...")
        try:
            if self.session_file.exists():
                logger.debug(f"[WorkspaceManager.load_session] Session file found at {self.session_file}")
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.debug(f"[WorkspaceManager.load_session] Session data: {data}")
                last = data.get("last_workspace")
                if last and Path(last).exists():
                    logger.info(f"[WorkspaceManager.load_session] Restoring last workspace: {last}")
                    self.open_workspace(last)
                else:
                    logger.info("[WorkspaceManager.load_session] No valid last workspace found")
        except Exception as exc:
            logger.exception(f"[WorkspaceManager.load_session] Failed to load session: {exc}")

    def _add_recent(self, path: str):
        logger.debug(f"[WorkspaceManager._add_recent] Adding to recent: {path}")
        if path in self.recent_projects:
            self.recent_projects.remove(path)
        self.recent_projects.insert(0, path)
        self.recent_projects = self.recent_projects[:20]
        logger.debug(f"[WorkspaceManager._add_recent] Recent projects list now: {self.recent_projects}")
        self._save_settings()
        logger.info(f"[WorkspaceManager._add_recent] Emitting recent_projects_changed...")
        self.event_bus.publish("recent_projects_changed", {"projects": self.recent_projects})

    def pin_project(self, path: str):
        logger.info(f"[WorkspaceManager.pin_project] Pinning project: {path}")
        if path not in self.pinned_projects:
            self.pinned_projects.append(path)
            self._save_settings()
            logger.info("[WorkspaceManager.pin_project] Emitting pinned_projects_changed...")
            self.event_bus.publish("pinned_projects_changed", {"projects": self.pinned_projects})
        else:
            logger.debug(f"[WorkspaceManager.pin_project] Project already pinned: {path}")

    def unpin_project(self, path: str):
        logger.info(f"[WorkspaceManager.unpin_project] Unpinning project: {path}")
        if path in self.pinned_projects:
            self.pinned_projects.remove(path)
            self._save_settings()
            logger.info("[WorkspaceManager.unpin_project] Emitting pinned_projects_changed...")
            self.event_bus.publish("pinned_projects_changed", {"projects": self.pinned_projects})
        else:
            logger.debug(f"[WorkspaceManager.unpin_project] Project not pinned: {path}")

    def _handle_open_request(self, data):
        logger.info(f"[WorkspaceManager._handle_open_request] Received data: {data}")
        path = data.get("path")
        if path:
            logger.info(f"[WorkspaceManager._handle_open_request] Calling open_workspace with path: {path}")
            self.open_workspace(path)
        else:
            logger.warning("[WorkspaceManager._handle_open_request] No path in event data!")

    def _handle_close_request(self, data):
        logger.info(f"[WorkspaceManager._handle_close_request] Received data: {data}")
        path = data.get("path")
        if path:
            self.close_workspace(path)
        elif self.active_workspace:
            logger.info(f"[WorkspaceManager._handle_close_request] Closing active workspace: {self.active_workspace.path}")
            self.close_workspace(str(self.active_workspace.path))
        else:
            logger.debug("[WorkspaceManager._handle_close_request] No active workspace to close")

    def _handle_refresh_request(self, _data):
        logger.info("[WorkspaceManager._handle_refresh_request] Received refresh request...")
        if self.active_workspace:
            self.refresh_workspace(self.active_workspace)
        else:
            logger.debug("[WorkspaceManager._handle_refresh_request] No active workspace to refresh")

    def _handle_reopen_last(self, _data):
        logger.info("[WorkspaceManager._handle_reopen_last] Received reopen last request...")
        if self.recent_projects:
            logger.info(f"[WorkspaceManager._handle_reopen_last] Reopening: {self.recent_projects[0]}")
            self.open_workspace(self.recent_projects[0])
        else:
            logger.debug("[WorkspaceManager._handle_reopen_last] No recent projects to reopen")

    def _handle_pin_project(self, data):
        logger.info(f"[WorkspaceManager._handle_pin_project] Received data: {data}")
        path = data.get("path")
        if path:
            self.pin_project(path)

    def _handle_unpin_project(self, data):
        logger.info(f"[WorkspaceManager._handle_unpin_project] Received data: {data}")
        path = data.get("path")
        if path:
            self.unpin_project(path)

    def open_workspace(self, path_str: str):
        """
        Step-by-step:
        1. Validate path
        2. If already open, activate it and return immediately
        3. Else emit workspace_loaded IMMEDIATELY to show explorer!
        4. Then start background metadata scan!
        """
        logger.info("=" * 80)
        logger.info("[WorkspaceManager.open_workspace] STARTING WORKSPACE OPENING")
        logger.info(f"[WorkspaceManager.open_workspace] Step 1: Validating path_str = {path_str}")
        try:
            path = Path(path_str).resolve()
            logger.debug(f"[WorkspaceManager.open_workspace] Resolved path = {path}")
        except Exception as exc:
            logger.exception(f"[WorkspaceManager.open_workspace] Step 1 FAILED: Invalid path: {exc}")
            return

        if not path.exists():
            logger.error(f"[WorkspaceManager.open_workspace] Step 1 FAILED: Path does not exist: {path}")
            return
        if not path.is_dir():
            logger.error(f"[WorkspaceManager.open_workspace] Step 1 FAILED: Path is not a directory: {path}")
            return
        logger.info("[WorkspaceManager.open_workspace] Step 1 COMPLETE: Path is valid!")

        logger.info("[WorkspaceManager.open_workspace] Step 2: Checking if already open...")
        for ws in self.workspaces:
            if ws.path == path:
                logger.info(f"[WorkspaceManager.open_workspace] Step 2: Workspace already open! Activating: {ws.path}")
                self._activate(ws)
                return
        logger.info("[WorkspaceManager.open_workspace] Step 2 COMPLETE: Workspace not already open")

        logger.info("[WorkspaceManager.open_workspace] Step 3: Creating Workspace instance...")
        ws = Workspace(path, pinned=path_str in self.pinned_projects)
        ws.is_active = True

        if self.active_workspace:
            logger.debug(f"[WorkspaceManager.open_workspace] Step 3: Deactivating previous active workspace: {self.active_workspace.path}")
            self.active_workspace.is_active = False

        logger.info("[WorkspaceManager.open_workspace] Step 3: Adding to workspaces list...")
        self.workspaces.append(ws)
        self.active_workspace = ws
        logger.info(f"[WorkspaceManager.open_workspace] Step 3 COMPLETE: Active workspace is now: {ws.path}")

        logger.info("[WorkspaceManager.open_workspace] Step 4: Adding to recent projects...")
        self._add_recent(str(path))
        logger.info("[WorkspaceManager.open_workspace] Step 4 COMPLETE!")

        logger.info("[WorkspaceManager.open_workspace] Step 5: EMITTING workspace_loaded NOW!")
        self.event_bus.publish("workspace_loaded", {"path": str(path)})
        self.event_bus.publish("log_message", {"message": f"✓ Workspace open: {path.name}"})
        logger.info("[WorkspaceManager.open_workspace] Step 5 COMPLETE: workspace_loaded emitted!")

        logger.info("[WorkspaceManager.open_workspace] Step 6: Starting background metadata scan...")
        self._start_metadata_scan(ws)
        logger.info("[WorkspaceManager.open_workspace] Step 6 COMPLETE!")
        logger.info("=" * 80)

    def _start_metadata_scan(self, workspace: Workspace):
        logger.info(f"[WorkspaceManager._start_metadata_scan] Starting for workspace: {workspace.path}")
        if workspace.scanning:
            logger.info(f"[WorkspaceManager._start_metadata_scan] Already scanning, skipping duplicate scan!")
            return

        logger.debug("[WorkspaceManager._start_metadata_scan] Setting scanning = True...")
        workspace.scanning = True

        logger.debug("[WorkspaceManager._start_metadata_scan] Creating QThread instance...")
        thread = QThread()
        logger.debug("[WorkspaceManager._start_metadata_scan] Creating _MetadataScanWorker instance...")
        worker = _MetadataScanWorker(workspace.path)
        logger.debug("[WorkspaceManager._start_metadata_scan] Moving worker to thread...")
        worker.moveToThread(thread)

        logger.debug("[WorkspaceManager._start_metadata_scan] Connecting signals...")
        thread.started.connect(worker.run)
        worker.scan_complete.connect(lambda ctx: self._on_scan_complete(ctx, workspace))
        worker.scan_failed.connect(lambda msg: self._on_scan_failed(msg, workspace))
        worker.scan_complete.connect(thread.quit)
        worker.scan_failed.connect(thread.quit)
        # Connect cleanup before starting thread
        thread.finished.connect(lambda: self._on_thread_finished(thread))
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(worker.deleteLater)

        logger.debug("[WorkspaceManager._start_metadata_scan] Adding thread to _scan_threads list...")
        self._scan_threads.append(thread)
        logger.debug(f"[WorkspaceManager._start_metadata_scan] _scan_threads now has {len(self._scan_threads)} thread(s)")

        logger.info(f"[WorkspaceManager._start_metadata_scan] STARTING THREAD!")
        thread.start()
        logger.info(f"[WorkspaceManager._start_metadata_scan] COMPLETE!")

    def _on_thread_finished(self, thread: QThread):
        logger.debug(f"[WorkspaceManager._on_thread_finished] Thread finished, removing from _scan_threads...")
        if thread in self._scan_threads:
            self._scan_threads.remove(thread)
        logger.debug(f"[WorkspaceManager._on_thread_finished] _scan_threads now has {len(self._scan_threads)} thread(s)")
        # Ensure worker is also cleaned up
        # Note: worker.deleteLater() is called automatically when thread finishes

    def _on_scan_complete(self, context, workspace: Workspace):
        logger.info("=" * 80)
        logger.info(f"[WorkspaceManager._on_scan_complete] Metadata scan complete for: {workspace.path}")
        workspace.scanning = False
        workspace.context = context

        logger.info("[WorkspaceManager._on_scan_complete] Emitting workspace_metadata_updated...")
        self.event_bus.publish("workspace_metadata_updated", {
            "path": str(workspace.path),
            "project_name": getattr(context, "project_name", workspace.path.name),
            "total_files": getattr(context, "total_files", 0),
            "total_folders": getattr(context, "total_folders", 0),
            "primary_language": getattr(context, "primary_language", "Unknown"),
            "framework": getattr(context, "framework_name", "Unknown"),
            "scan_duration_ms": getattr(context, "scan_duration_ms", 0),
        })

        self.event_bus.publish("log_message", {"message": f"✓ Metadata scan complete: {workspace.path.name}"})
        logger.info(f"[WorkspaceManager._on_scan_complete] COMPLETE!")
        logger.info("=" * 80)

    def _on_scan_failed(self, msg: str, workspace: Workspace):
        logger.error("=" * 80)
        logger.error(f"[WorkspaceManager._on_scan_failed] Metadata scan FAILED for {workspace.path}: {msg}")
        workspace.scanning = False
        self.event_bus.publish("log_message", {"message": f"⚠ Metadata scan failed: {msg}"})
        logger.error("=" * 80)

    def close_workspace(self, path_str: str):
        logger.info("=" * 80)
        logger.info(f"[WorkspaceManager.close_workspace] Closing workspace: {path_str}")
        path = Path(path_str).resolve()
        for idx, ws in enumerate(self.workspaces):
            if ws.path == path:
                logger.debug(f"[WorkspaceManager.close_workspace] Found workspace at index {idx}, removing...")
                self.workspaces.pop(idx)
                if ws == self.active_workspace:
                    if self.workspaces:
                        logger.debug(f"[WorkspaceManager.close_workspace] Activating next workspace: {self.workspaces[0].path}")
                        self._activate(self.workspaces[0])
                    else:
                        logger.info("[WorkspaceManager.close_workspace] No workspaces left, setting active to None")
                        self.active_workspace = None
                        self.event_bus.publish("workspace_closed", {})
                logger.info("[WorkspaceManager.close_workspace] Emitting log_message...")
                self.event_bus.publish("log_message", {"message": f"Workspace closed: {path.name}"})
                logger.info("[WorkspaceManager.close_workspace] COMPLETE!")
                logger.info("=" * 80)
                return
        logger.warning(f"[WorkspaceManager.close_workspace] Workspace not found: {path}")

    def refresh_workspace(self, workspace: Workspace):
        logger.info(f"[WorkspaceManager.refresh_workspace] Refreshing metadata for: {workspace.path}")
        self.event_bus.publish("log_message", {"message": f"Refreshing metadata: {workspace.path.name}…"})
        self._start_metadata_scan(workspace)

    def _activate(self, ws: Workspace):
        logger.info(f"[WorkspaceManager._activate] Activating workspace: {ws.path}")
        if self.active_workspace and self.active_workspace != ws:
            logger.debug(f"[WorkspaceManager._activate] Deactivating: {self.active_workspace.path}")
            self.active_workspace.is_active = False
        ws.is_active = True
        self.active_workspace = ws

        logger.info("[WorkspaceManager._activate] Emitting workspace_loaded...")
        self.event_bus.publish("workspace_loaded", {"path": str(ws.path)})

        self.event_bus.publish("workspace_activated", {"path": str(ws.path)})
        logger.info(f"[WorkspaceManager._activate] COMPLETE: Active workspace is {ws.path}")


# ============================================================================
# SECTION: core.editor_manager (core/editor_manager.py)
# ============================================================================
"""
Editor Manager — v2.0

Manages all file I/O for the editor:
- Multi-encoding file loading (UTF-8, UTF-16, Latin-1 fallback)
- Read-only file detection
- Session persistence (open tabs)
- Save / Save-As
- External file-change detection with user notification
- EventBus integration
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog

from core.logger import setup_logger

logger = setup_logger(__name__)

# Maximum file size we will load without a warning (10 MB)
_MAX_FILE_SIZE = 10 * 1024 * 1024

# Drive-letter ("C:\..." / "C:/...") or UNC ("\\server\share") absolute paths.
_WINDOWS_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]|^\\\\")


def _looks_like_windows_path(path_str: str) -> bool:
    """True if the string is a Windows absolute path (invalid on POSIX)."""
    return bool(_WINDOWS_PATH_RE.match(path_str or ""))


class EditorManager(QObject):
    """
    Central file I/O manager for the editor.
    Wired to EditorTabs (UI) through the EventBus.
    """

    def __init__(self, event_bus):
        super().__init__()
        self.event_bus   = event_bus
        self.session_file = Path("config/editor_session.json")

        # path_str → True/False (True = currently open)
        self.open_files: Dict[str, bool] = {}
        self.session_data: dict = {
            "open_tabs": [],
            "active_tab": None,
            "tabs": {},
            "splits": [],
            "search": None,
        }
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(150)
        self._save_timer.timeout.connect(self.save_session)

        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self._on_file_changed_externally)

        self._subscribe()

    # ------------------------------------------------------------------ #
    #  EventBus wiring                                                     #
    # ------------------------------------------------------------------ #

    def _subscribe(self):
        logger.info("[EditorManager._subscribe] Subscribing to events")
        self.event_bus.subscribe("file_selected",        self._handle_file_selected)
        self.event_bus.subscribe("file_open_requested",  self._handle_file_open_requested)
        self.event_bus.subscribe("request_save_current", self._handle_save_current)
        self.event_bus.subscribe("request_save_file",    self._handle_save_file)
        self.event_bus.subscribe("request_close_file",   self._handle_close_file)
        self.event_bus.subscribe("editor_saved",         self._handle_editor_saved)
        self.event_bus.subscribe("editor_session_updated", self._handle_session_updated)
        self.event_bus.subscribe("app_closing",          self.save_session)

    # ------------------------------------------------------------------ #
    #  Session                                                             #
    # ------------------------------------------------------------------ #

    def load_session(self):
        """Reopen files from the last session."""
        try:
            if self.session_file.exists():
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.session_data = data or self.session_data
                self.event_bus.publish("editor_session_loaded", self.session_data)
                for path_str in data.get("open_tabs", []):
                    self.open_file(path_str)
        except Exception as exc:
            logger.error(f"Failed to load editor session: {exc}")

    def save_session(self, _event_data=None):
        """Persist open files list."""
        try:
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, "w", encoding="utf-8") as f:
                if not self.session_data.get("open_tabs"):
                    self.session_data["open_tabs"] = list(self.open_files.keys())
                json.dump(self.session_data, f, indent=4)
        except Exception as exc:
            logger.error(f"Failed to save editor session: {exc}")

    def _schedule_session_save(self):
        self._save_timer.start()

    # ------------------------------------------------------------------ #
    #  EventBus handlers                                                   #
    # ------------------------------------------------------------------ #

    def _handle_file_selected(self, data: dict):
        """Explorer double-click → open file."""
        logger.info(f"[EditorManager._handle_file_selected] Received data: {data}")
        path_str = data.get("path", "")
        if path_str:
            logger.info(f"[EditorManager._handle_file_selected] Calling open_file with: {path_str}")
            self.open_file(path_str)
        else:
            logger.warning("[EditorManager._handle_file_selected] No path in event data")

    def _handle_file_open_requested(self, data: dict):
        """File → Open File menu → open file."""
        logger.info(f"[EditorManager._handle_file_open_requested] Received data: {data}")
        path_str = data.get("path", "")
        if path_str:
            logger.info(f"[EditorManager._handle_file_open_requested] Calling open_file with: {path_str}")
            self.open_file(path_str)
        else:
            logger.warning("[EditorManager._handle_file_open_requested] No path in event data")

    def _handle_save_current(self, data: dict):
        """Ctrl+S from menu / toolbar — forward to active editor via event."""
        logger.info("[EditorManager._handle_save_current] Publishing editor_save_current_requested")
        self.event_bus.publish("editor_save_current_requested", {})

    def _handle_save_file(self, data: dict):
        """
        Save a specific editor widget.
        Payload must include {'editor': <CodeEditor>, 'path': optional str}.
        """
        logger.info(f"[EditorManager._handle_save_file] Received data: {data}")
        editor = data.get("editor")
        if not editor:
            logger.warning("[EditorManager._handle_save_file] No editor in data")
            return
        path_str = getattr(editor, "file_path", None) or data.get("path")
        if not path_str:
            logger.warning("[EditorManager._handle_save_file] No path in data or editor")
            return
        logger.info(f"[EditorManager._handle_save_file] Calling _write_file for: {path_str}")
        self._write_file(editor, Path(path_str))

    def _handle_close_file(self, data: dict):
        """Remove file from tracked list and watcher."""
        logger.info(f"[EditorManager._handle_close_file] Received data: {data}")
        path_str = data.get("path", "")
        if path_str and path_str in self.open_files:
            del self.open_files[path_str]
            if path_str in self.watcher.files():
                self.watcher.removePath(path_str)
            self._schedule_session_save()
            self.event_bus.publish("file_closed", {"path": path_str})
        else:
            logger.warning(f"[EditorManager._handle_close_file] Path not open: {path_str}")

    def _handle_editor_saved(self, data: dict):
        """Re-add watcher path after a save (was removed to avoid feedback loop)."""
        logger.info(f"[EditorManager._handle_editor_saved] Received data: {data}")
        path_str = data.get("path", "")
        if path_str and path_str not in self.watcher.files():
            self.watcher.addPath(path_str)

    def _handle_session_updated(self, data: dict):
        """Store the latest editor session state and save it shortly after."""
        if isinstance(data, dict):
            self.session_data = data
            self._schedule_session_save()

    # ------------------------------------------------------------------ #
    #  Core: open                                                          #
    # ------------------------------------------------------------------ #

    def open_file(self, path_str: str):
        """
        Read file from disk and publish 'file_opened' event.

        Handles:
        - UTF-8, UTF-16, Latin-1 encoding fallback
        - Binary / undecodable files (skipped with log)
        - Read-only files (content loaded, read-only flag set)
        - Very large files (warned, then still loaded)
        - Symlinks (resolved before opening)
        - Missing files (error logged and published)
        """
        logger.info(f"[EditorManager.open_file] Starting with path_str: {path_str}")

        # Guard against foreign (Windows) absolute paths on POSIX. A string like
        # "C:\\Projects\\...\\a.py" is a *relative* path to pathlib on Linux, so
        # .resolve() silently joins it onto the CWD (e.g.
        # "/mnt/d/.../C:\\Projects\\...") and then fails a misleading existence
        # check. These come from session files written on another OS; skip them
        # quietly rather than emitting a scary "File not found".
        if os.name != "nt" and _looks_like_windows_path(path_str):
            logger.debug(f"[EditorManager.open_file] Skipping foreign path: {path_str}")
            return

        try:
            path = Path(path_str).resolve()
        except Exception as exc:
            logger.error(f"Invalid path: {path_str}: {exc}")
            return

        if not path.exists():
            self._err(f"File not found: {path}")
            return

        if not path.is_file():
            logger.info(f"[EditorManager.open_file] Path is not file, ignoring: {path}")
            return

        path_str_resolved = str(path)
        if path_str_resolved in self.open_files:
            logger.info(f"[EditorManager.open_file] Path already open, reusing existing tab: {path_str_resolved}")
            self.event_bus.publish("file_reveal_requested", {
                "path": path,
                "path_str": path_str_resolved,
                "content": "",
                "encoding": None,
                "read_only": False,
                "already_open": True,
            })
            return

        # Large file warning
        try:
            size = path.stat().st_size
            if size > _MAX_FILE_SIZE:
                logger.warning(f"Large file ({size // 1024} KB): {path}")
                self.event_bus.publish("log_message", {
                    "message": f"⚠ Large file ({size // 1024} KB): {path.name}"
                })
        except OSError:
            pass

        # Detect read-only
        is_read_only = not path.stat().st_mode & 0o200 if path.exists() else False

        # Read content — try multiple encodings
        logger.info(f"[EditorManager.open_file] Reading file: {path}")
        content, encoding = self._read_with_encoding(path)
        if content is None:
            self._err(f"Cannot decode file (binary?): {path.name}")
            return

        # Track & watch
        self.open_files[path_str_resolved] = True
        if path_str_resolved not in self.watcher.files():
            self.watcher.addPath(path_str_resolved)
        self._schedule_session_save()

        # Publish so EditorTabs can open the tab
        logger.info(f"[EditorManager.open_file] Publishing file_opened event for: {path_str_resolved}")
        self.event_bus.publish("file_opened", {
            "path":        path,          # Path object
            "path_str":    path_str_resolved,
            "content":     content,
            "encoding":    encoding,
            "read_only":   is_read_only,
            "already_open": False,
        })
        self.event_bus.publish("log_message", {"message": f"Opened: {path.name}"})

    @staticmethod
    def _read_with_encoding(path: Path):
        """Try UTF-8, then UTF-16, then Latin-1. Returns (content, encoding) or (None, None)."""
        logger.debug(f"[EditorManager._read_with_encoding] Reading: {path}")
        for enc in ("utf-8", "utf-16", "latin-1"):
            try:
                content = path.read_text(encoding=enc)
                logger.debug(f"[EditorManager._read_with_encoding] Success with encoding: {enc}")
                return content, enc
            except UnicodeDecodeError:
                logger.debug(f"[EditorManager._read_with_encoding] Decode error with {enc}, trying next")
                continue
            except OSError as exc:
                logger.error(f"OS error reading {path}: {exc}")
                return None, None
        logger.warning(f"[EditorManager._read_with_encoding] All encodings failed for {path}")
        return None, None

    # ------------------------------------------------------------------ #
    #  Core: write                                                         #
    # ------------------------------------------------------------------ #

    def _write_file(self, editor, path: Path):
        """Write editor content to disk using safe file operations."""
        logger.info(f"[EditorManager._write_file] Starting for path: {path}")
        from core.safe_file_ops import safe_write_text

        try:
            # Remove from watcher to avoid feedback loop
            path_str = str(path)
            if path_str in self.watcher.files():
                self.watcher.removePath(path_str)

            content = editor.toPlainText()
            logger.debug(f"[EditorManager._write_file] Writing {len(content)} chars")
            success = safe_write_text(path, content, encoding="utf-8")

            if success:
                editor.document().setModified(False)
                # A Save As target was never opened through `open_file`, so
                # register it here or the session would forget the tab.
                self.open_files[str(Path(path_str).resolve())] = True
                self.event_bus.publish("editor_saved", {"path": path_str})
                self.event_bus.publish("log_message", {"message": f"Saved: {path.name}"})
                logger.info(f"File saved: {path}")
            else:
                self._err(f"Failed to save file: {path.name}")

        except Exception as exc:
            self._err(f"Error saving {path.name}: {exc}")

    # ------------------------------------------------------------------ #
    #  External file change detection                                      #
    # ------------------------------------------------------------------ #

    def _on_file_changed_externally(self, path_str: str):
        """QFileSystemWatcher fires when a watched file changes on disk."""
        logger.info(f"[EditorManager._on_file_changed_externally] File changed: {path_str}")
        path = Path(path_str)

        # Re-add to watcher if it was removed (some editors replace the file)
        if path.exists() and path_str not in self.watcher.files():
            self.watcher.addPath(path_str)

        # Publish so EditorTabs can show a "reload?" prompt
        self.event_bus.publish("file_changed_externally", {
            "path":   path_str,
            "exists": path.exists(),
        })

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _err(self, msg: str):
        logger.error(msg)
        self.event_bus.publish("log_message",    {"message": f"⚠ {msg}"})
        self.event_bus.publish("editor_error",   {"error": msg})


from tools.explorer_and_files import ProjectScanner  # noqa: E402
