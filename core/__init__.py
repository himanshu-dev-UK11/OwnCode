"""
Core IDE Package & Consolidated Module Alias Resolver — v2.0

Maps both the reorganized module hierarchy (`core.*`, `agent.*`, `ui.*`, `tools.*`)
and legacy submodule paths (`ai.*`, `core.lsp.*`, `ui.panels.*`, `ui.widgets.*`,
`ui.shell.*`, `ui.dialogs.*`) to their consolidated modules seamlessly.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
import types
from typing import Dict, List, Optional

ALIAS_MAP: Dict[str, str] = {
    # core/
    "core.qt_compat": "core.event_and_compat",
    "core.logger": "core.event_and_compat",
    "core.exceptions": "core.event_and_compat",
    "core.event_bus": "core.event_and_compat",
    "core.error_manager": "core.system_managers",
    "core.startup_profiler": "core.system_managers",
    "core.startup_validator": "core.system_managers",
    "core.config_validator": "core.system_managers",
    "core.resource_manager": "core.system_managers",
    "core.session_manager": "core.system_managers",
    "core.performance_watchdog": "core.system_managers",
    "core.background_initializer": "core.system_managers",
    "safety.delete_guard": "tools.explorer_and_files",
    "core.file_operations": "tools.explorer_and_files",
    "core.safe_file_ops": "core.system_managers",
    "core.file_watcher": "tools.explorer_and_files",
    "core.workspace_manager": "core.workspace_and_editor",
    "core.editor_manager": "core.workspace_and_editor",
    "core.lsp.language_server_config": "core.lsp_engine",
    "core.lsp.jedi_provider": "core.lsp_engine",
    "core.lsp.lsp_client": "core.lsp_engine",
    "core.lsp.lsp_manager": "core.lsp_engine",

    # tools/
    "core.process_utils": "tools.terminal_engine",
    "ai.terminal.terminal_history_storage": "tools.terminal_engine",
    "ai.terminal.terminal_output_analyzer": "tools.terminal_engine",
    "ai.terminal.terminal_approval_panel": "tools.terminal_engine",
    "ai.terminal.ai_terminal_manager": "tools.terminal_engine",
    "ai.terminal.ai_terminal_execution": "tools.terminal_engine",
    "core.run_manager": "tools.runner_and_tester",
    "core.program_tester": "tools.runner_and_tester",
    "ui.settings_manager": "tools.theme_and_settings",
    "ui.design_system": "tools.theme_and_settings",
    "ui.theme": "tools.theme_and_settings",
    "core.git_service": "tools.git_and_github",
    "core.github_service": "tools.git_and_github",

    # agent/providers/
    "ai.providers.base_provider": "agent.providers.provider_core",
    "ai.providers.secret_store": "agent.providers.provider_core",
    "ai.providers.api_token_manager": "agent.providers.provider_core",
    "ai.providers.provider_discovery": "agent.providers.provider_core",
    "ai.providers.provider_health": "agent.providers.provider_core",
    "ai.providers.provider_factory": "agent.providers.provider_core",
    "ai.providers.provider_registry": "agent.providers.provider_core",
    "ai.providers.provider_router": "agent.providers.provider_core",
    "ai.providers.provider_manager": "agent.providers.provider_core",
    "ai.providers.llama_cpp_loader": "agent.providers.local_providers",
    "ai.providers.llama_cpp_provider": "agent.providers.local_providers",
    "ai.providers.ollama_provider": "agent.providers.local_providers",
    "ai.providers.qwen_provider": "agent.providers.local_providers",
    "ai.providers.openai_provider": "agent.providers.cloud_providers",
    "ai.providers.anthropic_provider": "agent.providers.cloud_providers",
    "ai.providers.gemini_provider": "agent.providers.cloud_providers",
    "ai.providers.groq_provider": "agent.providers.cloud_providers",
    "ai.providers.cerebras_provider": "agent.providers.cloud_providers",
    "ai.providers.deepinfra_provider": "agent.providers.cloud_providers",
    "ai.providers.fireworks_provider": "agent.providers.cloud_providers",
    "ai.providers.together_provider": "agent.providers.cloud_providers",
    "ai.providers.custom_provider": "agent.providers.cloud_providers",

    # agent/models/
    "ai.models.base_model": "agent.models.model_catalog_and_router",
    "ai.models.model_capabilities": "agent.models.model_catalog_and_router",
    "ai.models.model_profile": "agent.models.model_catalog_and_router",
    "ai.models.model_context": "agent.models.model_catalog_and_router",
    "ai.models.model_catalog": "agent.models.model_catalog_and_router",
    "ai.models.model_health": "agent.models.model_catalog_and_router",
    "ai.models.model_registry": "agent.models.model_catalog_and_router",
    "ai.models.model_selector": "agent.models.model_catalog_and_router",
    "ai.models.model_manager": "agent.models.model_catalog_and_router",
    "ai.models.router": "agent.models.model_catalog_and_router",
    "ai.models.model_catalog_and_router": "agent.models.model_catalog_and_router",
    "ai.performance.llm_optimizer": "agent.models.model_catalog_and_router",
    "ai.models.qwen": "agent.models.model_center_and_adapters",
    "ai.models.gemini": "agent.models.model_center_and_adapters",
    "ai.models.deepseek": "agent.models.model_center_and_adapters",
    "ai.models.model_center": "agent.models.model_center_and_adapters",

    # agent/
    "ai.agents.base_agent": "agent.chat_and_agents",
    "ai.agents.coder": "agent.chat_and_agents",
    "ai.agents.debugger": "agent.chat_and_agents",
    "ai.agents.planner": "agent.chat_and_agents",
    "ai.connection.connection_manager": "agent.chat_and_agents",
    "ai.chat.ai_chat_engine": "agent.chat_and_agents",
    "ai.integration.ai_ide_integration": "agent.chat_and_agents",
    "ai.agents.orchestrator": "agent.chat_and_agents",
    "ai.memory.project_memory": "agent.context_and_memory",
    "ai.memory.decision_memory": "agent.context_and_memory",
    "ai.memory.project_context": "agent.context_and_memory",
    "ai.context.token_estimator": "agent.context_and_memory",
    "ai.context.symbol_index": "agent.context_and_memory",
    "ai.context.file_import_graph": "agent.context_and_memory",
    "ai.context.dependency_resolver": "agent.context_and_memory",
    "ai.context.context_cache": "agent.context_and_memory",
    "ai.context.context_selector": "agent.context_and_memory",
    "ai.context.context_ranker": "agent.context_and_memory",
    "ai.context.context_builder": "agent.context_and_memory",
    "ai.context.ai_context_store": "agent.context_and_memory",
    "ai.context.context_engine": "agent.context_and_memory",
    "ai.context.repo_map": "agent.context_and_memory",
    "ai.context.ast_slicer": "agent.context_and_memory",
    "ai.memory.episodic_memory": "agent.context_and_memory",
    "ai.intelligence.symbol_indexer": "agent.code_intelligence",
    "ai.intelligence.reference_index": "agent.code_intelligence",
    "ai.intelligence.dependency_graph": "agent.code_intelligence",
    "ai.intelligence.language_statistics": "agent.code_intelligence",
    "ai.intelligence.entry_point_detector": "agent.code_intelligence",
    "ai.intelligence.architecture_detector": "agent.code_intelligence",
    "ai.intelligence.documentation_indexer": "agent.code_intelligence",
    "ai.intelligence.impact_analyzer": "agent.code_intelligence",
    "ai.intelligence.project_health": "agent.code_intelligence",
    "ai.intelligence.project_analyzer": "agent.code_intelligence",
    "ai.editing.change_request": "agent.code_editing",
    "ai.editing.change_set": "agent.code_editing",
    "ai.editing.diff_generator": "agent.code_editing",
    "ai.editing.patch_builder": "agent.code_editing",
    "ai.editing.patch_validator": "agent.code_editing",
    "ai.editing.file_lock_manager": "agent.code_editing",
    "ai.editing.edit_history": "agent.code_editing",
    "ai.editing.rollback_manager": "agent.code_editing",
    "ai.editing.change_preview": "agent.code_editing",
    "ai.editing.change_applier": "agent.code_editing",
    "ai.editing.review_model": "agent.code_editing",
    "ai.editing.smart_patch_engine": "agent.code_editing",
    "ai.editing.shadow_sandbox": "agent.code_editing",
    "ai.editing.fim_and_next_edit": "agent.code_editing",
    "ai.engine.task": "agent.planning_engine",
    "ai.engine.engineering_task": "agent.planning_engine",
    "ai.engine.task_analyzer": "agent.planning_engine",
    "ai.planning.plan_step": "agent.planning_engine",
    "ai.planning.plan": "agent.planning_engine",
    "ai.planning.dependency_graph": "agent.planning_engine",
    "ai.planning.complexity_analyzer": "agent.planning_engine",
    "ai.planning.risk_analyzer": "agent.planning_engine",
    "ai.planning.plan_validator": "agent.planning_engine",
    "ai.planning.task_decomposer": "agent.planning_engine",
    "ai.planning.roadmap_builder": "agent.planning_engine",
    "ai.execution.execution_task": "agent.planning_engine",
    "ai.execution.task_state": "agent.planning_engine",
    "ai.execution.execution_events": "agent.execution_and_verification",
    "ai.execution.execution_metrics": "agent.execution_and_verification",
    "ai.execution.execution_report": "agent.execution_and_verification",
    "ai.execution.execution_queue": "agent.execution_and_verification",
    "ai.execution.execution_monitor": "agent.execution_and_verification",
    "ai.execution.task_scheduler": "agent.execution_and_verification",
    "ai.execution.task_executor": "agent.execution_and_verification",
    "ai.verification.verification_task": "agent.execution_and_verification",
    "ai.verification.verification_report": "agent.execution_and_verification",
    "ai.verification.error_classifier": "agent.execution_and_verification",
    "ai.verification.success_validator": "agent.execution_and_verification",
    "ai.verification.retry_manager": "agent.execution_and_verification",
    "ai.verification.build_runner": "agent.execution_and_verification",
    "ai.verification.test_runner": "agent.execution_and_verification",
    "ai.verification.linter_runner": "agent.execution_and_verification",
    "ai.verification.formatter_runner": "agent.execution_and_verification",
    "ai.verification.verification_engine": "agent.execution_and_verification",
    "ai.execution.execution_engine": "agent.execution_and_verification",
    "ai.engine.engineering_workflow_coordinator": "agent.execution_and_verification",
    "ai.tools.tool_base": "agent.tool_engine",
    "ai.tools.tool_permission": "agent.tool_engine",
    "ai.tools.tool_history": "agent.tool_engine",
    "ai.tools.tool_registry": "agent.tool_engine",
    "ai.tools.tool_scheduler": "agent.tool_engine",
    "ai.tools.terminal_tool": "agent.tool_engine",
    "ai.tools.git_tool": "agent.tool_engine",
    "ai.tools.tool_manager": "agent.tool_engine",
    "ai.tools.base_tool": "agent.workspace_tools",
    "ai.tools.tool_context": "agent.workspace_tools",
    "ai.tools.file_tool": "agent.workspace_tools",
    "ai.tools.editor_tool": "agent.workspace_tools",
    "ai.tools.search_tool": "agent.workspace_tools",
    "ai.tools.execution_tool": "agent.workspace_tools",
    "ai.tools.tree_builder": "tools.explorer_and_files",
    "ai.tools.language_detector": "tools.explorer_and_files",
    "ai.tools.framework_detector": "tools.explorer_and_files",
    "ai.tools.dependency_analyzer": "tools.explorer_and_files",
    "ai.tools.project_scanner": "tools.explorer_and_files",
    "ai.tools.project_tool": "agent.workspace_tools",
    "ai.tools.browser_tool": "agent.workspace_tools",
    "ai.tools.tool_coordinator": "agent.workspace_tools",
    "ai.tools.workspace_vfs": "agent.workspace_tools",
    "core.vfs": "agent.workspace_tools",
    "ai.tools.lsp_tool": "agent.workspace_tools",
    "ai.tools.tool_parser": "agent.workspace_tools",

    # ui/
    "ui.widgets.icons": "ui.widgets_and_icons",
    "ui.widgets.controls": "ui.widgets_and_icons",
    "ui.widgets.diff_view": "ui.widgets_and_icons",
    "ui.widgets.native_dialogs": "ui.widgets_and_icons",
    "ui.shell.titlebar": "ui.shell_and_chrome",
    "ui.shell.activity_bar": "ui.shell_and_chrome",
    "ui.shell.status_bar": "ui.shell_and_chrome",
    "ui.shell.toolbar": "ui.shell_and_chrome",
    "ui.panels.notifications": "ui.shell_and_chrome",
    "ui.panels.command_palette": "ui.dialogs_and_palette",
    "ui.dialogs.settings_schema": "ui.dialogs_and_palette",
    "ui.dialogs.settings_fields": "ui.dialogs_and_palette",
    "ui.dialogs.theme_gallery": "ui.dialogs_and_palette",
    "ui.dialogs.settings_dialog": "ui.dialogs_and_palette",
    "ui.dialogs.change_review_dialog": "ui.dialogs_and_palette",
    "ui.dialogs.tool_confirmation_dialog": "ui.dialogs_and_palette",
    "ui.panels.editor.language_support": "ui.code_editor_suite",
    "ui.panels.editor.bracket_matcher": "ui.code_editor_suite",
    "ui.panels.editor.syntax_highlighter": "ui.code_editor_suite",
    "ui.panels.editor.tree_sitter_highlighter": "ui.code_editor_suite",
    "ui.panels.editor.completion_popup": "ui.code_editor_suite",
    "ui.panels.editor.symbol_outline": "ui.code_editor_suite",
    "ui.panels.editor.breadcrumb": "ui.code_editor_suite",
    "ui.panels.editor.code_editor": "ui.code_editor_suite",
    "ui.panels.editor.editor_tabs": "ui.code_editor_suite",
    "ui.panels.dashboard": "ui.code_editor_suite",
    "ui.panels.center": "ui.code_editor_suite",
    "ui.panels.explorer": "tools.explorer_and_files",
    "ui.panels.search_panel": "ui.sidebar_panels",
    "ui.panels.git_panel": "ui.sidebar_panels",
    "ui.panels.run_panel": "ui.sidebar_panels",
    "ui.panels.test_panel": "ui.sidebar_panels",
    "ui.panels.tasks_panel": "ui.sidebar_panels",
    "ui.panels.memory_panel": "ui.sidebar_panels",
    "ui.panels.sidebar": "ui.sidebar_panels",
    "ui.panels.bottom_dock": "ui.bottom_dock",
    "ui.panels.ai_workspace": "ui.ai_workspace",
    "ui.inline_ai": "ui.main_window",
}

VIRTUAL_PACKAGES: Dict[str, List[str]] = {
    "ai": ["agent"],
    "ai.providers": ["agent.providers.provider_core", "agent.providers.local_providers", "agent.providers.cloud_providers"],
    "ai.models": ["agent.models.model_catalog_and_router", "agent.models.model_center_and_adapters"],
    "ai.agents": ["agent.chat_and_agents"],
    "ai.chat": ["agent.chat_and_agents"],
    "ai.connection": ["agent.chat_and_agents"],
    "ai.integration": ["agent.chat_and_agents"],
    "ai.memory": ["agent.context_and_memory"],
    "ai.context": ["agent.context_and_memory"],
    "ai.intelligence": ["agent.code_intelligence"],
    "ai.editing": ["agent.code_editing"],
    "ai.engine": ["agent.planning_engine", "agent.execution_and_verification"],
    "ai.planning": ["agent.planning_engine"],
    "ai.execution": ["agent.planning_engine", "agent.execution_and_verification"],
    "ai.verification": ["agent.execution_and_verification"],
    "ai.terminal": ["tools.terminal_engine"],
    "ai.tools": ["agent.tool_engine", "agent.workspace_tools", "tools.explorer_and_files"],
    "ai.performance": ["agent.models.model_catalog_and_router"],
    "core.lsp": ["core.lsp_engine"],
    "safety": ["tools.explorer_and_files"],
    "ui.widgets": ["ui.widgets_and_icons"],
    "ui.shell": ["ui.shell_and_chrome"],
    "ui.dialogs": ["ui.dialogs_and_palette"],
    "ui.panels": ["tools.explorer_and_files", "ui.sidebar_panels", "ui.code_editor_suite", "ui.bottom_dock", "ui.ai_workspace", "ui.shell_and_chrome", "ui.dialogs_and_palette"],
    "ui.panels.editor": ["ui.code_editor_suite"],
}


class _VirtualPackage(types.ModuleType):
    def __init__(self, name: str, backing_targets: List[str]):
        super().__init__(name)
        self.__path__ = []
        self.__package__ = name
        self._backing_targets = backing_targets

    def __getattr__(self, item: str):
        if item.startswith("__") and item.endswith("__"):
            raise AttributeError(item)
        # Check if `name.item` is a known submodule alias
        sub_full = f"{self.__name__}.{item}"
        if sub_full in ALIAS_MAP or sub_full in VIRTUAL_PACKAGES:
            return importlib.import_module(sub_full)
        for target in self._backing_targets:
            mod = importlib.import_module(target)
            if hasattr(mod, item):
                return getattr(mod, item)
        raise AttributeError(f"module {self.__name__!r} has no attribute {item!r}")


class _ConsolidatedLoader(importlib.abc.Loader):
    def __init__(self, fullname: str, target_mod: Optional[str] = None, is_pkg: bool = False):
        self.fullname = fullname
        self.target_mod = target_mod
        self.is_pkg = is_pkg

    def create_module(self, spec):
        if self.fullname in sys.modules:
            return sys.modules[self.fullname]
        if self.is_pkg:
            pkg = _VirtualPackage(self.fullname, VIRTUAL_PACKAGES.get(self.fullname, []))
            sys.modules[self.fullname] = pkg
            return pkg
        mod = importlib.import_module(self.target_mod)
        sys.modules[self.fullname] = mod
        return mod

    def exec_module(self, module):
        pass


class _ConsolidatedFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path=None, target=None):
        if fullname in ALIAS_MAP:
            target_mod = ALIAS_MAP[fullname]
            return importlib.machinery.ModuleSpec(
                fullname,
                _ConsolidatedLoader(fullname, target_mod=target_mod, is_pkg=False),
                is_package=False,
            )
        if fullname in VIRTUAL_PACKAGES:
            return importlib.machinery.ModuleSpec(
                fullname,
                _ConsolidatedLoader(fullname, is_pkg=True),
                is_package=True,
            )
        return None


def install_import_aliases():
    if not any(isinstance(f, _ConsolidatedFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _ConsolidatedFinder())


install_import_aliases()

import core.event_and_compat  # activate qt_compat, logger, exceptions, and EventBus
