# OwnCode IDE v2.0

A fast, local-first AI-assisted code editor and development environment built with Python and PySide6.

## Project Structure

OwnCode v2.0 is organized into 6 clean top-level directories, each containing a dedicated **`knowledge.txt`** reference guide:

- **`core/`** — Core IDE runtime (`EventBus`, Qt compatibility layer, logger, `ErrorManager`, `SafeFileOps`, `StartupProfiler`, `StartupValidator`, `ConfigValidator`, `ResourceManager`, `SessionManager`, `PerformanceWatchdog`, `BackgroundInitializer`, `WorkspaceManager`, `EditorManager`, and the `LSPManager` / `JediProvider` engine).
- **`agent/`** — AI Workspace backend (`AIChatEngine`, `ConnectionManager`, `CoderAgent` / `DebuggerAgent` / `PlannerAgent`, RAG `ContextEngine`, `ProjectMemory`, `SymbolIndexer`, `ReferenceIndex`, `DependencyGraph`, `DiffGenerator` / `ChangeSet`, `TaskDecomposer`, `ExecutionEngine`, `VerificationEngine`, and AI agent tools).
  - **`agent/providers/`** — Local LLM (`llama.cpp` GGUF server loader, `Ollama`, `Qwen`) and Cloud AI provider adapters, fast port discovery, health checks, and encrypted `SecretStore`.
  - **`agent/models/`** — `ModelCatalog`, `ModelRegistry`, capability profiles, local-first `ModelRouter`, and hardware/VRAM `LLMOptimizer`.
- **`ui/`** — PySide6 user interface (`MainWindow`, `TitleBar`, `ActivityBar`, `StatusBar`, non-blocking `NotificationCenter`, tooltip-enabled controls, theme-aware `CommandPalette` & `SettingsDialog`, `CodeEditor` & syntax highlighters, left `Sidebar` panels, `BottomDock` with interactive `Terminal`, interactive `Output`, and `Smart Problem Finder`, and `AIWorkspace`).
- **`tools/`** — File Explorer & workspace scanners (`Explorer`, `ProjectScanner`, `TreeBuilder`, `FileOperations`, `FileWatcher`, `DeleteGuard`), silent terminal & subprocess engine (`HiddenProcess` with `CREATE_NO_WINDOW`), `RunManager`, Smart Program Tester (`program_tester`), Theme & Design System (13 palettes + `SettingsManager`), and `GitService` / `GitHubService`.
- **`docs & resources/`** — Architecture & local LLM documentation, Language Server Module (LSM/LSP) & model profile resources (`lsm_and_language_resources.json`), and the consolidated verification test suite (`verification_tests.py`).
- **`logs/`** — Runtime application logs (`app.log`).

## Quick Start

### Launch Directly (Desktop Application)
Double-click **`OwnCode.exe`** in the project folder to launch the OwnCode IDE directly as a native Windows GUI application (with the custom **"OC"** desktop icon and zero console window).

```bash
# Or launch from terminal:
OwnCode.exe
# (or: python main.py)

# Run the automated verification test suite (24 unit & integration tests)
python "docs & resources/verification_tests.py" -v
```
