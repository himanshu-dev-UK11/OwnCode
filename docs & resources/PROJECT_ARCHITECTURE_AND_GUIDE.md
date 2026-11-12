# OwnCode IDE v2.0 — Architecture & Developer Guide

## 1. Consolidated Folder Structure
OwnCode is organized into 6 clean top-level directories:
- **`core/`**: Core IDE runtime, event bus, Qt compatibility layer, system/resource/session/error managers, workspace & editor buffer management, and the Language Server Protocol (LSP / Jedi) engine.
- **`agent/`**: AI Workspace backend, chat engine, autonomous agents (`Coder`, `Debugger`, `Planner`), code intelligence indexers, context & memory stores, code diff/patch editing engine, planning/execution/verification pipeline, and agent tools.
  - **`agent/providers/`**: Local LLM servers (`llama.cpp` GGUF server loader, `Ollama`, `Qwen`) and cloud AI provider adapters, health checks, port discovery, and encrypted API secret store.
  - **`agent/models/`**: Model catalog, capability profiles, smart local-first router, and hardware/VRAM optimizer.
- **`ui/`**: PySide6 graphical interface (`MainWindow`, `TitleBar`, `ActivityBar`, `StatusBar`, `CommandPalette`, `SettingsDialog`, `CodeEditor`, `Sidebar` panels, `BottomDock` with interactive `Terminal`, `Output`, and `Smart Problem Finder`, and `AIWorkspace`).
- **`tools/`**: Terminal & hidden subprocess engine (`HiddenProcess`, `CREATE_NO_WINDOW` enforcement), `RunManager`, Smart Program & Algorithm Tester (`program_tester`), Theme & Design System (`13` themes + `SettingsManager`), and `Git` / `GitHub` CLI integrations.
- **`docs & resources/`**: Architecture documentation, local LLM guides, Language Server Module (LSM/LSP) & model profile specs, and the consolidated verification test suite.
- **`logs/`**: Application runtime logs (`owncode.log`).

Every folder includes a dedicated **`knowledge.txt`** file explaining all libraries, modules, classes, and functions inside that folder.
