"""
Application entry point for OwnCode — v2.0

Initializes core systems with optimized startup for fast UI interactivity.
Heavy systems initialize in background after window is shown.
"""

import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import core  # Activate consolidated module alias resolver
from tools.terminal_engine import install_hidden_subprocess_hooks

# Install hidden-console hooks immediately so no subprocess ever flashes a window
install_hidden_subprocess_hooks()

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, QObject, Signal, Qt

from core.event_and_compat import setup_logger, EventBus
from core.system_managers import (
    get_error_manager,
    get_resource_manager,
    get_config_validator,
    get_performance_watchdog,
    get_startup_profiler,
    ProfilePhase,
)
from ui.main_window import MainWindow
from tools.theme_and_settings import ThemeManager, get_settings_manager

logger = setup_logger(__name__)
profiler = get_startup_profiler()

# Configuration: Enable optimized startup by default
OPTIMIZED_STARTUP = os.environ.get('OPTIMIZED_STARTUP', 'true').lower() != 'false'


class _UiInvoker(QObject):
    """Marshals callables onto the Qt GUI (main) thread."""

    _run = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run.connect(self._exec, Qt.QueuedConnection)

    def _exec(self, fn):
        try:
            fn()
        except Exception as e:
            logger.error(f"UI-thread callback failed: {e}")

    def post(self, fn):
        """Queue `fn` to run on the main thread (safe to call from any thread)."""
        self._run.emit(fn)


def validate_startup() -> bool:
    """Validate startup environment and create missing directories/files."""
    with ProfilePhase("validate_startup"):
        logger.info("Validating startup environment...")
        
        with ProfilePhase("create_directories"):
            required_dirs = ["config", "config/providers", "config/models", "logs", "temp"]
            for dir_name in required_dirs:
                try:
                    Path(dir_name).mkdir(parents=True, exist_ok=True)
                    logger.debug(f"Ensured directory: {dir_name}")
                except Exception as e:
                    logger.error(f"Failed to create directory {dir_name}: {e}")
                    return False
        
        # Fast startup: defer full multi-file JSON schema validation to background thread
        # so QApplication and MainWindow appear on screen with zero disk-read delay.
        
        logger.info("Startup validation complete")
        return True


def initialize_background_systems(event_bus, window, error_manager):
    """
    Initialize heavy systems in background after UI is shown.
    Qt QObject managers (WorkspaceManager, EditorManager, RunManager, LSPManager,
    PerformanceWatchdog) are created on the main GUI thread first so their
    QTimers and QFileSystemWatchers always have a valid QApplication event loop.
    """
    if not OPTIMIZED_STARTUP:
        return None
    
    from core.background_initializer import BackgroundInitializer
    from core.workspace_manager import WorkspaceManager
    from core.editor_manager import EditorManager
    from core.run_manager import RunManager
    from core.lsp.lsp_manager import LSPManager

    # Create QObject-based managers directly on the main GUI thread!
    watchdog = get_performance_watchdog()
    watchdog.set_event_bus(event_bus)
    watchdog.start()

    workspace_manager = WorkspaceManager(event_bus)
    editor_manager = EditorManager(event_bus)
    run_manager = RunManager(event_bus)
    lsp_manager = LSPManager(event_bus)
    project_analyzer = None

    window.set_lsp_manager(lsp_manager)
    window.set_workspace_manager(workspace_manager)
    window.run_manager = run_manager
    window.editor_manager = editor_manager

    def _restore_sessions_fast():
        try:
            editor_manager.load_session()
            workspace_manager.load_session()
        except Exception as e:
            logger.error(f"Fast session restore failed: {e}")

    # Restore open files and workspace tree immediately (~10ms) without waiting on AI provider init
    QTimer.singleShot(10, _restore_sessions_fast)

    def _on_workspace_loaded_for_analyzer(data):
        path = data.get("path")
        pa = getattr(window, "project_analyzer", None)
        if path and pa is not None:
            pa.analyze(path)

    def _on_file_close(data):
        path = data.get("path", "")
        if path:
            try:
                window.center.editor_tabs.force_close_tab(path)
            except Exception as e:
                error_manager.handle_exception(type(e), e, e.__traceback__, "editor")

    def _on_workspace_opened(data):
        path = data.get("path", "")
        if path:
            try:
                lsp_manager.set_workspace(Path(path))
            except Exception as e:
                error_manager.handle_exception(type(e), e, e.__traceback__, "lsp")

    event_bus.subscribe("workspace_loaded", _on_workspace_loaded_for_analyzer)
    event_bus.subscribe("file_force_closed", _on_file_close)
    event_bus.subscribe("workspace_opened", _on_workspace_opened)

    initializer = BackgroundInitializer()
    ui_invoker = _UiInvoker(window)

    def init_heavy_ai_and_provider_systems():
        """Initialize AI providers, models, and workflow systems in background."""
        try:
            from ai.providers.provider_registry import ProviderRegistry
            from ai.providers.provider_manager import ProviderManager
            from ai.providers.provider_factory import register_standard_providers
            from ai.providers.provider_discovery import ProviderDiscovery
            
            register_standard_providers()
            provider_registry = ProviderRegistry(config_dir="config/providers")
            loaded_providers = provider_registry.load_all_providers()
            logger.info(f"Loaded {len(loaded_providers)} providers from config")

            provider_manager = ProviderManager(provider_registry, event_bus)
            provider_manager.monitor_health()

            ui_invoker.post(lambda: window.ai_workspace.set_providers(
                provider_registry, provider_manager))

            preferred_provider = "llama_cpp"
            try:
                default_model_cfg = get_settings_manager().get_default_model() or ""
                if ":" in default_model_cfg:
                    preferred_provider = default_model_cfg.split(":", 1)[0].strip()
            except Exception:
                pass
            
            def connect_provider(provider_name):
                try:
                    provider = provider_registry.get_provider(provider_name)
                    if not (provider and provider.config.enabled):
                        return
                    # Fast path for llama_cpp: discover GGUF models on disk (<2ms) without
                    # blocking IDE startup on spawning llama-server.exe (starts on demand).
                    if provider_name == "llama_cpp":
                        try:
                            connected = provider.connect(lazy_startup=True)
                        except TypeError:
                            connected = provider.connect()
                        if connected:
                            logger.info("[OK] Registered llama_cpp GGUF models (lazy on-demand startup)")
                        return

                    # Fast path for local socket servers: probe port with 150ms timeout first
                    if provider_name in ("ollama", "qwen"):
                        is_up = getattr(provider, "is_server_up", None)
                        if callable(is_up) and not is_up(timeout=0.15, cache_seconds=0):
                            return

                    # Fast path for cloud providers: skip network round-trip at boot if no API key
                    auth_type = getattr(getattr(provider, "config", None), "auth_type", None)
                    auth_val = str(getattr(auth_type, "value", auth_type) or "").lower()
                    if auth_val not in ("", "none") and not getattr(provider.config, "api_key", ""):
                        return

                    if provider.connect():
                        logger.info(f"[OK] Connected to {provider_name}")
                        fetched_models = provider.refresh_models()
                        if fetched_models:
                            provider._set_models(fetched_models)
                except Exception as e:
                    logger.error(f"Provider {provider_name} connection failed: {e}")

            with ThreadPoolExecutor(max_workers=max(1, min(6, len(loaded_providers))),
                                    thread_name_prefix="provider-init") as executor:
                futures = [executor.submit(connect_provider, name)
                           for name in loaded_providers]
                for future in as_completed(futures):
                    future.result()
            
            # Model Systems
            from ai.models.model_registry import ModelRegistry
            from ai.models.model_catalog import ModelState
            from ai.models.router import ModelRouter
            from ai.connection import initialize_connection_manager
            from ai.models.model_center import initialize_model_center
            
            model_registry = ModelRegistry(provider_registry)
            
            for provider_name in loaded_providers:
                provider = provider_registry.get_provider(provider_name)
                if provider:
                    catalog_entries = model_registry.catalog.get_entries_by_provider(provider_name)
                    for entry in catalog_entries:
                        model_name = entry.profile.name
                        if provider.is_connected():
                            model_registry.update_model_state(model_name, ModelState.READY)
                        else:
                            model_registry.update_model_state(model_name, ModelState.API_REQUIRED)
            
            for provider_name in loaded_providers:
                provider = provider_registry.get_provider(provider_name)
                if provider and provider.is_connected():
                    models = provider.get_models()
                    for model_id, model_info in models.items():
                        model_registry.register_model_from_provider(provider_name, model_info)
            
            model_router = ModelRouter(model_registry, provider_manager)
            connection_manager = initialize_connection_manager()
            model_center = initialize_model_center(provider_registry, provider_manager, model_registry)
            
            for provider_name in loaded_providers:
                provider = provider_registry.get_provider(provider_name)
                if provider and provider.is_connected():
                    models = provider.get_models()
                    for model_id, model_info in models.items():
                        full_model_id = f"{provider_name}:{model_id}"
                        try:
                            from ai.models.model_center import ModelInfo, ModelCapabilities
                            model_center_info = ModelInfo(
                                model_id=full_model_id,
                                provider=provider_name,
                                display_name=model_info.get("name", model_id),
                                context_window=model_info.get("context_window", 4096),
                                max_output_tokens=model_info.get("max_output_tokens", 4096),
                                model_type=model_info.get("type", "local"),
                                capabilities=ModelCapabilities.from_config({
                                    "provider": provider_name,
                                    "type": model_info.get("type", "local"),
                                    "context_window": model_info.get("context_window", 4096),
                                    "supports_streaming": model_info.get("supports_streaming", True),
                                    "supports_vision": model_info.get("supports_vision", False),
                                    "supports_tool_calling": model_info.get("supports_tool_calling", False),
                                    "supports_function_calling": model_info.get("supports_function_calling", False),
                                }),
                                status="connected",
                                availability=1.0,
                                tags=model_info.get("strengths", []),
                            )
                            model_center._models[full_model_id] = model_center_info
                        except Exception as e:
                            logger.error(f"Failed to add {full_model_id} to Model Center: {e}")
            
            from ai.integration.ai_ide_integration import initialize_ai_ide_integration
            ai_integration = initialize_ai_ide_integration(event_bus, window)
            initial_ws = getattr(window, "_workspace_root", None)
            ai_integration.initialize_tools(initial_ws)
            
            from ai.performance.llm_optimizer import initialize_llm_optimizer
            local_provider = provider_registry.get_provider(preferred_provider)
            if local_provider is None:
                local_provider = provider_registry.get_provider("llama_cpp") or provider_registry.get_provider("ollama")
            llm_optimizer = initialize_llm_optimizer(event_bus, local_provider,
                                                     provider_registry)
            
            from ai.chat.ai_chat_engine import initialize_ai_chat_engine
            chat_engine = initialize_ai_chat_engine(event_bus, provider_registry, provider_manager, 
                                                    model_center, model_registry)
            
            if initial_ws and hasattr(chat_engine, "set_workspace_root"):
                chat_engine.set_workspace_root(initial_ws)
            ai_integration.set_chat_engine(chat_engine)
            chat_engine.set_optimizer(llm_optimizer)
            
            ui_invoker.post(lambda: window.set_chat_engine(chat_engine))
            ui_invoker.post(lambda: window.set_provider_manager(provider_manager))
            ui_invoker.post(lambda: setattr(window, 'provider_registry', provider_registry))
            ui_invoker.post(lambda: window.ai_workspace.set_providers(provider_registry, provider_manager))
            ui_invoker.post(lambda: window.set_ai_integration(ai_integration))
            ui_invoker.post(lambda: window.set_llm_optimizer(llm_optimizer))
            
            from ai.intelligence.project_analyzer import ProjectAnalyzer
            project_analyzer = ProjectAnalyzer(event_bus)
            ui_invoker.post(lambda: window.set_project_analyzer(project_analyzer))
            from ai.engine.engineering_workflow_coordinator import EngineeringWorkflowCoordinator
            from ai.execution.execution_engine import ExecutionEngine, ExecutionEngineConfig
            from ai.execution.task_executor import TaskExecutor
            from ai.editing.change_applier import ChangeApplier
            from ai.verification.verification_engine import VerificationEngine
            
            execution_engine = ExecutionEngine(event_bus, ExecutionEngineConfig(config_dir="config"))
            project_root_str = str(Path(".").resolve())
            change_applier = ChangeApplier(event_bus, project_root_str)
            verification_engine = VerificationEngine(event_bus, project_root_str)
            execution_engine.attach_change_applier(change_applier)
            execution_engine.attach_verification_engine(verification_engine)
            TaskExecutor.set_chat_engine(chat_engine)

            def _on_edit_confirmation_required(data):
                request_id = data.get("request_id", "")
                reason = data.get("reason", "Destructive file changes require confirmation.")
                files = data.get("files", [])
                file_preview = "\n".join(f"• {path}" for path in files[:10]) or "• (no files listed)"
                if len(files) > 10:
                    file_preview += f"\n• …and {len(files) - 10} more"

                def _ask():
                    reply = QMessageBox.question(
                        window,
                        "Confirm AI File Changes",
                        f"{reason}\n\nFiles:\n{file_preview}\n\nProceed with these changes?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )
                    if reply == QMessageBox.Yes and request_id:
                        try:
                            change_applier.confirm_pending(request_id)
                        except Exception as e:
                            logger.warning(f"Failed to apply confirmed destructive change {request_id}: {e}")

                ui_invoker.post(_ask)

            event_bus.subscribe("edit_confirmation_required", _on_edit_confirmation_required)
            
            context_engine = None
            try:
                from ai.context.context_engine import ContextEngine
                context_engine = ContextEngine(event_bus, project_root_str)
                execution_engine.attach_context_engine(context_engine)
            except Exception as e:
                logger.warning(f"ContextEngine init failed: {e}")
            
            def _on_workspace_loaded_for_context(data):
                path = data.get("path", "")
                if path:
                    try:
                        from ai.context.context_engine import ContextEngine
                        new_ctx = ContextEngine(event_bus, path)
                        execution_engine.attach_context_engine(new_ctx)
                        if hasattr(window, 'workflow_coordinator'):
                            window.workflow_coordinator.context_engine = new_ctx
                    except Exception as e:
                        logger.warning(f"Failed to create ContextEngine for {path}: {e}")
            
            event_bus.subscribe("workspace_loaded", _on_workspace_loaded_for_context)
            
            workflow_coordinator = EngineeringWorkflowCoordinator(
                event_bus=event_bus,
                project_analyzer=project_analyzer,
                context_engine=context_engine,
                model_router=model_router,
                chat_engine=chat_engine,
                patch_engine=change_applier,
                verification_engine=verification_engine,
                execution_engine=execution_engine,
            )
            
            def _on_file_saved(data):
                path = data.get("path", "")
                if hasattr(window, 'workflow_coordinator') and window.workflow_coordinator.context_engine:
                    try:
                        window.workflow_coordinator.context_engine.notify_file_changed(path)
                    except Exception:
                        pass
            
            event_bus.subscribe("editor_saved", _on_file_saved)
            event_bus.subscribe("file_saved", _on_file_saved)
            
            def wire_agents():
                try:
                    from ai.agents.coder import CoderAgent
                    from ai.agents.debugger import DebuggerAgent
                    window.coder_agent = CoderAgent(event_bus, chat_engine)
                    window.debugger_agent = DebuggerAgent(event_bus, chat_engine)
                except Exception as ae:
                    logger.warning(f"Agent init failed: {ae}")
            
            ui_invoker.post(wire_agents)
            
            def wire_memory():
                try:
                    def _on_workspace_loaded_for_memory(data):
                        path = data.get("path", "")
                        name = Path(path).name if path else "unknown"
                        if path and hasattr(window, 'workflow_coordinator'):
                            window.workflow_coordinator.project_memory.set_project(name, path)
                    event_bus.subscribe("workspace_loaded", _on_workspace_loaded_for_memory)
                except Exception as me:
                    logger.warning(f"Memory wiring failed: {me}")
            
            ui_invoker.post(wire_memory)

            ui_invoker.post(lambda: setattr(window, 'workflow_coordinator', workflow_coordinator))
            ui_invoker.post(lambda: setattr(window, 'connection_manager', connection_manager))
            

            
            logger.info("Background initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Background initialization failed: {e}")
            return False
        finally:
            try:
                profiler.end("total_startup")
                profiler.save_report("logs/startup_timing_optimized.json")
            except Exception as pe:
                logger.warning(f"Profiler report failed (non-fatal): {pe}")
            logger.info("=" * 60)
            logger.info("OwnCode v2.0 ready!")
            logger.info("=" * 60)
    
    initializer.add_task("heavy_systems", init_heavy_ai_and_provider_systems, priority=100)
    
    def on_progress(completed, total):
        try:
            if completed < total:
                window.status_bar.showMessage("Initializing systems...")
            else:
                window.status_bar.showMessage("Ready", 2000)
        except Exception:
            pass
    
    initializer.progress_updated.connect(on_progress)
    return initializer


def main():
    """Main execution function — optimized for fast startup using BackgroundInitializer."""
    profiler.start("total_startup")
    
    logger.info("=" * 60)
    logger.info("Initializing OwnCode v2.0 (Fast Startup)...")
    logger.info("=" * 60)

    if not validate_startup():
        logger.error("Startup validation failed, attempting to continue...")

    # Ensure working directory and safe streams when launched via OwnCode.exe (pythonw.exe)
    app_root = Path(__file__).resolve().parent
    try:
        os.chdir(app_root)
    except Exception:
        pass
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    # Set Windows Taskbar AppUserModelID so Windows 10/11 displays the custom "OC" icon
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OwnCode.IDE.Desktop.v2")
        except Exception:
            pass

    # ── Create QApplication FIRST so QTimers and QFileSystemWatchers have an event dispatcher ──
    with ProfilePhase("qapplication_init"):
        app = QApplication.instance() or QApplication(sys.argv)
        app.setApplicationName("OwnCode")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("OwnCode")
        try:
            from PySide6.QtGui import QIcon
            ico_file = app_root / "docs & resources" / "owncode_logo.ico"
            png_file = app_root / "docs & resources" / "owncode_logo.png"
            app_icon = QIcon()
            if ico_file.exists():
                app_icon.addFile(str(ico_file))
            if png_file.exists():
                app_icon.addFile(str(png_file))
            if not app_icon.isNull():
                app.setWindowIcon(app_icon)
        except Exception:
            pass

    # ── Minimal Core Systems ─────────────────────────────────────────────
    with ProfilePhase("minimal_core_init"):
        event_bus = EventBus()
        error_manager = get_error_manager()
        error_manager.set_event_bus(event_bus)
        resource_manager = get_resource_manager()
        resource_manager.set_event_bus(event_bus)

    # ── Design System & Theme ────────────────────────────────────────────
    with ProfilePhase("design_system_init"):
        from ui.design_system import get_design_system, PALETTES
        design_system = get_design_system()
        app.setStyleSheet(design_system.get_stylesheet("global"))
        theme_manager = ThemeManager(app)
        saved_theme = get_settings_manager().get("general", "theme", "paper_ink")
        theme_manager.apply_theme(saved_theme if saved_theme in PALETTES
                                  else "paper_ink")

    # ── Create & Show Main Window FIRST! ─────────────────────────────────
    with ProfilePhase("mainwindow_creation"):
        window = MainWindow(event_bus)
        try:
            if not app.windowIcon().isNull():
                window.setWindowIcon(app.windowIcon())
        except Exception:
            pass
        window.set_theme_manager(theme_manager)
    
    with ProfilePhase("window_show"):
        window.show()
        window.showMaximized()

    # ── Initialize managers & heavy AI systems ───────────────────────────
    background_initializer = initialize_background_systems(event_bus, window, error_manager)
    if background_initializer:
        QTimer.singleShot(5, background_initializer.start)
    
    # ── Shutdown handler ─────────────────────────────────────────────────
    def _unload_local_llms():
        registry = getattr(window, 'provider_registry', None)
        if registry is None:
            return
        try:
            ollama = registry.get_provider("ollama")
            if ollama is not None and hasattr(ollama, 'unload_models'):
                count = ollama.unload_models()
                if count:
                    logger.info(f"Ollama: evicted {count} model(s) from VRAM on exit")
        except Exception as e:
            logger.warning(f"Ollama model eviction on exit failed: {e}")

        try:
            llama_cpp = registry.get_provider("llama_cpp")
            if llama_cpp is not None:
                llama_cpp.disconnect()
                logger.info("llama-server: process stopped on exit")
        except Exception as e:
            logger.warning(f"llama-server shutdown on exit failed: {e}")

    def on_shutdown():
        logger.info("Shutting down...")
        try:
            optimizer = getattr(window, 'llm_optimizer', None)
            if optimizer is not None and hasattr(optimizer, 'stop'):
                optimizer.stop()
        except Exception:
            pass
        try:
            _unload_local_llms()
        except Exception:
            pass
        try:
            watchdog = get_performance_watchdog()
            watchdog.stop()
        except Exception:
            pass
        try:
            resource_manager.cleanup_all()
        except Exception:
            pass
        try:
            error_manager.save_history()
        except Exception:
            pass
        event_bus.publish("app_closing", {})
        logger.info("Shutdown complete")
    
    app.aboutToQuit.connect(on_shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
