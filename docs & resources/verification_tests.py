"""
OwnCode Consolidated Verification Test Suite

Combines RunManagerTests, TestProgramTester, TestTerminalSelfTestAndProcessUtils,
TestIntelligenceIndexers, LlamaCppLoaderTests, LlamaCppProviderTests, and ModelSelectionTests.
Run with: python "docs & resources/verification_tests.py"
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import core

import os
import sys
import tempfile
import unittest
from pathlib import Path

from core.qt_compat import QCoreApplication, QTimer

from core.event_bus import EventBus
from core.run_manager import RunManager, python_command


class RunManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_windows_python_runs_without_console_window(self):
        command = python_command(Path.cwd())
        if os.name == "nt" and not getattr(sys, "frozen", False):
            self.assertTrue(command.lower().endswith("pythonw.exe"))

    def test_python_file_runs_once_and_reports_output(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "hello.py"
            script.write_text('print("run-once")\n', encoding="utf-8")
            bus = EventBus()
            manager = RunManager(bus)
            output = []
            finished = []
            bus.subscribe(
                "process_output",
                lambda data: output.append(data.get("output", "")),
            )
            bus.subscribe(
                "process_finished",
                lambda data: (
                    finished.append(data.get("exit_code")),
                    QTimer.singleShot(0, self.app.quit),
                ),
            )

            manager.run_file(script)
            QTimer.singleShot(5000, self.app.quit)
            self.app.exec()

            self.assertEqual([0], finished)
            self.assertEqual(1, sum("run-once" in chunk for chunk in output))




"""
Comprehensive unit and integration tests for:
1. Smart Program & Algorithm Tester (`core/program_tester.py`)
2. Terminal Self-Test & Hidden Subprocess Suppression (`core/process_utils.py`)
3. RunManager Test & Terminal Test EventBus Integration (`core/run_manager.py`)
4. Code Intelligence Indexing Fixes (`ai/intelligence/symbol_indexer.py`, `reference_index.py`, `dependency_graph.py`)
"""



import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from core.event_bus import EventBus
from core.process_utils import (
    hidden_subprocess_kwargs,
    install_hidden_subprocess_hooks,
    run_hidden_command,
    run_terminal_self_test,
)
from core.program_tester import (
    GeneratedTestCase,
    ProgramInputProfile,
    ProgramTestResult,
    analyze_program,
    diagnose_error,
    generate_test_inputs,
    run_program_test,
)
from core.run_manager import RunManager


STACK_MENU_PROGRAM_PY = """
stack = []
while True:
    print("\\n--- STACK OPERATIONS MENU ---")
    print("1. Push")
    print("2. Pop")
    print("3. Peek")
    print("4. Display")
    print("5. Exit")
    choice = int(input("Enter your choice: "))
    if choice == 1:
        val = int(input("Enter value to push: "))
        stack.append(val)
        print(f"Pushed {val}")
    elif choice == 2:
        if stack:
            print(f"Popped {stack.pop()}")
        else:
            print("Stack Underflow")
    elif choice == 3:
        if stack:
            print(f"Top element is {stack[-1]}")
        else:
            print("Stack is empty")
    elif choice == 4:
        print(f"Stack contents: {stack}")
    elif choice == 5:
        print("Exiting stack program...")
        break
    else:
        print("Invalid choice")
"""

STUDENT_RECORDS_PROGRAM_PY = """
n = int(input("Enter number of students: "))
students = []
for i in range(n):
    name = input("Enter student name: ")
    age = int(input("Enter student age: "))
    marks = float(input("Enter student marks: "))
    students.append((name, age, marks))

print(f"Recorded {len(students)} students:")
for s in students:
    print(f"Student: {s[0]}, Age: {s[1]}, Marks: {s[2]:.1f}")
"""

ARRAY_PROGRAM_PY = """
n = int(input("Enter number of elements: "))
arr = []
for i in range(n):
    arr.append(int(input(f"Enter element {i+1}: ")))
print(f"Count={len(arr)}, Sum={sum(arr)}, Max={max(arr)}, Min={min(arr)}")
"""

BINARY_SEARCH_PROGRAM_PY = """
n = int(input("Enter size of array: "))
arr = []
for _ in range(n):
    arr.append(int(input("Enter element: ")))
key = int(input("Enter element to search (binary search): "))
low, high = 0, len(arr) - 1
found = -1
while low <= high:
    mid = (low + high) // 2
    if arr[mid] == key:
        found = mid
        break
    elif arr[mid] < key:
        low = mid + 1
    else:
        high = mid - 1
print(f"Found index: {found}")
"""


class TestProgramTester(unittest.TestCase):
    """Verify smart input detection, randomness, multi-language support, and concise error fixes."""

    def test_stack_menu_generates_random_multi_step_operations_never_just_exit(self):
        profile = analyze_program(STACK_MENU_PROGRAM_PY, Path("stack_demo.py"))
        self.assertEqual(profile.mode, "menu_loop")
        self.assertEqual(profile.exit_choice, "5")
        roles = {opt.choice: opt.role for opt in profile.menu_options}
        self.assertEqual(roles.get("1"), "push")
        self.assertEqual(roles.get("2"), "pop")
        self.assertEqual(roles.get("3"), "peek")
        self.assertEqual(roles.get("4"), "display")
        self.assertEqual(roles.get("5"), "exit")

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "stack_demo.py"
            script.write_text(STACK_MENU_PROGRAM_PY, encoding="utf-8")

            generated_sets = set()
            for _ in range(6):
                result = run_program_test(file_path=script)
                self.assertTrue(result.success, f"Stack test failed: {result.stderr}")
                self.assertEqual(result.exit_code, 0)
                lines = [ln.strip() for ln in result.stdin_text.splitlines() if ln.strip()]
                # Must never just pass "5" to exit immediately
                self.assertNotEqual(lines, ["5"])
                self.assertGreater(len(lines), 6)
                self.assertEqual(lines[-1], "5")
                self.assertIn("Pushed ", result.stdout)
                self.assertIn("Exiting stack program...", result.stdout)
                generated_sets.add(tuple(lines))

            # Across 6 runs, random generation must produce distinct sequences
            self.assertGreaterEqual(
                len(generated_sets), 5,
                "Expected randomized stack test sequences on each run, not static inputs",
            )

    def test_student_entity_records_auto_and_custom(self):
        profile = analyze_program(STUDENT_RECORDS_PROGRAM_PY, Path("students.py"))
        self.assertEqual(profile.mode, "entity_records")
        self.assertIn("name", profile.entity_fields)
        self.assertIn("age", profile.entity_fields)
        self.assertIn("marks", profile.entity_fields)

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "students.py"
            script.write_text(STUDENT_RECORDS_PROGRAM_PY, encoding="utf-8")

            # Auto mode
            res_auto = run_program_test(file_path=script)
            self.assertTrue(res_auto.success, res_auto.stderr)
            self.assertIn("Recorded ", res_auto.stdout)

            # Custom mode with 6 students from Left Sidebar Tests panel config
            cfg = {
                "mode": "entity_records",
                "count": 6,
                "has_count_prefix": True,
                "entity_fields": ["name", "age", "marks"],
            }
            res_custom = run_program_test(file_path=script, custom_config=cfg)
            self.assertTrue(res_custom.success, res_custom.stderr)
            self.assertIn("Recorded 6 students:", res_custom.stdout)

    def test_array_n_elements_and_binary_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            arr_script = Path(tmp) / "array_sum.py"
            arr_script.write_text(ARRAY_PROGRAM_PY, encoding="utf-8")

            cfg = {
                "mode": "array_elements",
                "count": 10,
                "has_count_prefix": True,
                "element_type": "int",
                "min_val": 10,
                "max_val": 99,
            }
            res = run_program_test(file_path=arr_script, custom_config=cfg)
            self.assertTrue(res.success, res.stderr)
            self.assertIn("Count=10,", res.stdout)

            bs_script = Path(tmp) / "binary_search.py"
            bs_script.write_text(BINARY_SEARCH_PROGRAM_PY, encoding="utf-8")
            bs_res = run_program_test(file_path=bs_script)
            self.assertTrue(bs_res.success, bs_res.stderr)
            self.assertIn("Found index:", bs_res.stdout)
            self.assertNotIn("Found index: -1", bs_res.stdout)

    def test_multi_language_c_and_cpp_stack_and_array(self):
        c_stack_code = """
        #include <stdio.h>
        int main() {
            int stack[100], top = -1, choice, val;
            while (1) {
                printf("1. Push\\n2. Pop\\n3. Peek\\n4. Display\\n5. Exit\\n");
                if (scanf("%d", &choice) != 1) break;
                if (choice == 1) {
                    scanf("%d", &val);
                    stack[++top] = val;
                    printf("Pushed %d\\n", val);
                } else if (choice == 2) {
                    if (top >= 0) printf("Popped %d\\n", stack[top--]);
                    else printf("Underflow\\n");
                } else if (choice == 3) {
                    if (top >= 0) printf("Top %d\\n", stack[top]);
                    else printf("Empty\\n");
                } else if (choice == 4) {
                    printf("Size %d\\n", top + 1);
                } else if (choice == 5) {
                    printf("Done\\n");
                    break;
                }
            }
            return 0;
        }
        """
        profile = analyze_program(c_stack_code, Path("stack.c"))
        self.assertEqual(profile.mode, "menu_loop")
        self.assertEqual(profile.exit_choice, "5")

        if shutil.which("gcc"):
            with tempfile.TemporaryDirectory() as tmp:
                c_file = Path(tmp) / "stack.c"
                c_file.write_text(c_stack_code, encoding="utf-8")
                res = run_program_test(file_path=c_file)
                self.assertTrue(res.success, res.stderr)
                self.assertIn("Pushed ", res.stdout)
                self.assertIn("Done", res.stdout)

    def test_calculator_menu_avoids_false_zero_print_and_tests_all_options(self):
        calc_code = """
def calculator():
    while True:
        print("\\nBasic Calculator Menu:")
        print("1. Add")
        print("2. Subtract")
        print("3. Multiply")
        print("4. Divide")
        print("5. Quit")
        choice = input("Enter your choice (1-5): ")
        if choice == '1':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            print(f"Result: {num1 + num2}")
        elif choice == '2':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            print(f"Result: {num1 - num2}")
        elif choice == '3':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            print(f"Result: {num1 * num2}")
        elif choice == '4':
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
            if num2 != 0:
                print(f"Result: {num1 / num2}")
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")
if __name__ == "__main__":
    calculator()
"""
        profile = analyze_program(calc_code)
        choices = [o.choice for o in profile.menu_options]
        self.assertEqual(choices, ["1", "2", "3", "4", "5"])
        res = run_program_test(code=calc_code)
        self.assertTrue(res.success)
        self.assertNotIn("0:print", res.formatted_output)
        self.assertNotIn("Test Pattern", res.formatted_output)
        self.assertNotIn("Invalid choice", res.stdout)
        self.assertEqual(res.formatted_output.count("Basic Calculator Menu:"), 1)

    def test_concise_error_diagnosis_and_quick_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 1. ZeroDivisionError
            zdiv = Path(tmp) / "zdiv.py"
            zdiv.write_text("x = 10 / 0\n", encoding="utf-8")
            res1 = run_program_test(file_path=zdiv)
            self.assertFalse(res1.success)
            self.assertTrue(res1.issue_summary)
            self.assertTrue(res1.quick_fix)
            self.assertLessEqual(len(res1.issue_summary.splitlines()), 2)
            self.assertLessEqual(len(res1.quick_fix.splitlines()), 2)
            self.assertTrue("division by zero" in res1.issue_summary.lower() or "zerodivisionerror" in res1.issue_summary.lower())

            # 2. SyntaxError
            syn = Path(tmp) / "syn.py"
            syn.write_text("def broken(\n    print('hi')\n", encoding="utf-8")
            res2 = run_program_test(file_path=syn)
            self.assertFalse(res2.success)
            self.assertLessEqual(len(res2.issue_summary.splitlines()), 2)
            self.assertLessEqual(len(res2.quick_fix.splitlines()), 2)

            # 3. Infinite loop timeout
            inf = Path(tmp) / "inf.py"
            inf.write_text("while True:\n    pass\n", encoding="utf-8")
            res3 = run_program_test(file_path=inf, timeout=0.8)
            self.assertFalse(res3.success)
            self.assertIn("timed out", res3.issue_summary.lower())
            self.assertLessEqual(len(res3.quick_fix.splitlines()), 2)
            self.assertIn("Issue    :", res1.formatted_output)
            self.assertIn("Quick Fix:", res1.formatted_output)


class TestTerminalSelfTestAndProcessUtils(unittest.TestCase):
    """Verify terminal self-test diagnostics and hidden subprocess hooks."""

    def test_terminal_self_test_passes_all_checks(self):
        install_hidden_subprocess_hooks()
        diag = run_terminal_self_test()
        self.assertTrue(diag["passed"], diag["formatted_report"])
        self.assertIn("OWNCODE TERMINAL DIAGNOSTICS & SELF-TEST", diag["formatted_report"])
        self.assertIn("Terminal tested successfully", diag["formatted_report"])

    def test_run_hidden_command_captures_stdout_and_stderr(self):
        rc, out, err, elapsed_ms, timed_out = run_hidden_command(
            ["python3", "-c", "import sys; print('ok'); sys.stderr.write('warn\\n')"]
        )
        self.assertEqual(rc, 0)
        self.assertFalse(timed_out)
        self.assertGreaterEqual(elapsed_ms, 0.0)
        self.assertEqual(out.strip(), "ok")
        self.assertEqual(err.strip(), "warn")

    def test_run_manager_event_bus_integration(self):
        bus = EventBus()
        rm = RunManager(bus)
        results = []
        term_results = []
        bus.subscribe("test_finished", lambda d: results.append(d))
        bus.subscribe("terminal_test_finished", lambda d: term_results.append(d))

        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "stack.py"
            script.write_text(STACK_MENU_PROGRAM_PY, encoding="utf-8")
            bus.publish("test_requested", {"file_path": str(script)})
            deadline = time.time() + 5.0
            while not results and time.time() < deadline:
                time.sleep(0.05)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])

        bus.publish("terminal_test_requested", {"cwd": os.getcwd()})
        deadline = time.time() + 5.0
        while not term_results and time.time() < deadline:
            time.sleep(0.05)
        self.assertEqual(len(term_results), 1)
        self.assertTrue(term_results[0]["passed"])


class TestIntelligenceIndexers(unittest.TestCase):
    """Verify SymbolIndexer, ReferenceIndex, and DependencyGraph skip restricted dirs and index cleanly."""

    def test_symbol_and_reference_and_dependency_indexers(self):
        from ai.intelligence.symbol_indexer import SymbolIndexer, SymbolType
        from ai.intelligence.reference_index import ReferenceIndex
        from ai.intelligence.dependency_graph import DependencyGraph

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Create a fake directory named like a .js file inside node_modules to test regression
            bad_dir = root / "node_modules" / "hls.js"
            bad_dir.mkdir(parents=True)
            src = root / "app.py"
            helper = root / "helper.py"
            helper.write_text("def compute_value(x):\n    return x * 2\n", encoding="utf-8")
            src.write_text("import helper\n\ndef main():\n    return helper.compute_value(21)\n", encoding="utf-8")

            indexer = SymbolIndexer()
            symbols = indexer.index_project(root)
            self.assertGreaterEqual(len(symbols), 2)
            self.assertTrue(indexer.get_symbols_by_name("compute_value"))
            funcs = indexer.get_symbols_by_type(SymbolType.FUNCTION)
            self.assertTrue(all(hasattr(f, "name") for f in funcs))

            ref_idx = ReferenceIndex()
            refs = ref_idx.build_index(root, symbols)
            self.assertIn("compute_value", refs)

            dep_graph = DependencyGraph()
            dep_graph.build(root)
            self.assertIn("helper.py", dep_graph.get_dependencies("app.py"))


    def test_windows_flags_strip_detached_process_and_hidden_process_works(self):
        import sys
        from core.process_utils import (
            _sanitize_windows_flags,
            CREATE_NO_WINDOW,
            DETACHED_PROCESS,
            CREATE_NEW_CONSOLE,
            HiddenProcess,
        )
        # Verify DETACHED_PROCESS and CREATE_NEW_CONSOLE are stripped so Windows never ignores CREATE_NO_WINDOW
        flags = _sanitize_windows_flags(DETACHED_PROCESS | CREATE_NEW_CONSOLE | CREATE_NO_WINDOW)
        self.assertTrue(flags & CREATE_NO_WINDOW)
        self.assertFalse(flags & DETACHED_PROCESS)
        self.assertFalse(flags & CREATE_NEW_CONSOLE)

        # Verify HiddenProcess captures stdout cleanly
        proc = HiddenProcess()
        proc.start(sys.executable, ["-c", "print(6 * 7)"])
        self.assertTrue(proc.waitForFinished(3000))
        out = bytes(proc.readAllStandardOutput()).decode("utf-8").strip()
        self.assertEqual(out, "42")




import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from ai.providers.base_provider import AuthenticationType, ProviderConfig, ProviderStatus
from ai.providers.llama_cpp_loader import LlamaCppLoader, LlamaCppLoaderError
from ai.providers.llama_cpp_provider import LlamaCppProvider
from ai.models.router import ModelRouter


class _Response:
    def __init__(self, lines=(), payload=None):
        self._lines = [line.encode("utf-8") for line in lines]
        self._payload = json.dumps(payload or {}).encode("utf-8")

    def __iter__(self):
        return iter(self._lines)

    def read(self):
        return self._payload

    def close(self):
        pass


class LlamaCppLoaderTests(unittest.TestCase):
    def test_provider_options_round_trip(self):
        config = ProviderConfig(
            provider_name="llama_cpp",
            endpoint="http://127.0.0.1:8080/v1",
            auth_type=AuthenticationType.NONE,
            options={"model_directory": r"D:\llama_models", "port": 8080},
        )
        restored = ProviderConfig.from_dict(config.to_dict())
        self.assertEqual(config.options, restored.options)

    def test_discovers_only_gguf_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Code Model.GGUF").write_bytes(b"gguf")
            (root / "ignore.txt").write_text("no", encoding="utf-8")
            (root / "nested").mkdir()
            (root / "nested" / "hidden.gguf").write_bytes(b"gguf")

            models = LlamaCppLoader({"model_directory": directory}).discover_models()

            self.assertEqual(["Code Model"], [model["id"] for model in models])
            self.assertEqual("local", models[0]["type"])

    def test_missing_executable_has_actionable_error(self):
        loader = LlamaCppLoader({"server_executable": "Z:/missing/llama-server.exe"})
        with patch("ai.providers.llama_cpp_loader.shutil.which", return_value=None):
            with self.assertRaisesRegex(LlamaCppLoaderError, "executable not found"):
                loader.resolve_executable()

    def test_updated_model_directory_is_used_without_recreating_loader(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            Path(second, "new-model.gguf").write_bytes(b"gguf")
            loader = LlamaCppLoader({"model_directory": first})
            loader.update_options({"model_directory": second})
            self.assertEqual(["new-model"], [m["id"] for m in loader.discover_models()])

    def test_uses_an_available_port_when_preferred_is_busy(self):
        loader = LlamaCppLoader({})
        with patch("ai.providers.llama_cpp_loader.socket.socket") as socket_type:
            busy = MagicMock()
            busy.__enter__.return_value = busy
            busy.bind.side_effect = OSError("busy")
            free = MagicMock()
            free.__enter__.return_value = free
            free.getsockname.return_value = ("127.0.0.1", 32123)
            socket_type.side_effect = [busy, free]
            self.assertEqual(32123, loader._available_port(8080))

    def test_rejects_non_loopback_endpoint_before_network_access(self):
        loader = LlamaCppLoader({})
        with patch("ai.providers.llama_cpp_loader.urllib.request.build_opener") as opener:
            with self.assertRaisesRegex(LlamaCppLoaderError, "127.0.0.1"):
                loader._api_models("https://example.com/v1")
        opener.assert_not_called()


class LlamaCppProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = ProviderConfig(
            provider_name="llama_cpp",
            endpoint="http://127.0.0.1:8080/v1",
            auth_type=AuthenticationType.NONE,
            default_model="code-model",
            supports_streaming=True,
            options={"model_directory": r"D:\llama_models"},
        )

    def test_connection_activates_selected_local_model(self):
        provider = LlamaCppProvider(self.config)
        provider.loader.discover_models = MagicMock(return_value=[{"id": "code-model"}])
        provider.loader.ensure_server = MagicMock(return_value="http://127.0.0.1:32123/v1")

        self.assertTrue(provider.connect())
        self.assertEqual(ProviderStatus.CONNECTED, provider.get_status())
        self.assertEqual("http://127.0.0.1:32123/v1", provider._active_endpoint)
        self.assertEqual("http://127.0.0.1:8080/v1", provider.config.endpoint)
        provider.loader.ensure_server.assert_called_once_with("code-model")

    def test_streams_openai_compatible_chat_chunks(self):
        provider = LlamaCppProvider(self.config)
        provider.loader.ensure_server = MagicMock(return_value="http://127.0.0.1:32123/v1")
        provider.loader._api_model_id = "served-model"
        response = _Response(lines=[
            'data: {"choices":[{"delta":{"content":"hello "}}]}\n',
            'data: {"choices":[{"delta":{"content":"world"}}]}\n',
            "data: [DONE]\n",
        ])
        opener = MagicMock()
        opener.open.return_value = response
        chunks = []

        with patch("ai.providers.llama_cpp_provider.urllib.request.build_opener", return_value=opener):
            result = provider.stream_response("prompt", "code-model", on_chunk=chunks.append)

        self.assertEqual("hello world", result)
        self.assertEqual(["hello ", "world"], chunks)
        request = opener.open.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual("served-model", payload["model"])
        self.assertEqual("prompt", payload["messages"][0]["content"])

    def test_cancellation_closes_active_response(self):
        provider = LlamaCppProvider(self.config)
        response = MagicMock()
        provider._response = response
        provider.cancel_generation()
        self.assertTrue(provider._cancel.is_set())
        response.close.assert_called_once()

    def test_connection_failure_sets_error_status(self):
        provider = LlamaCppProvider(self.config)
        provider.loader.discover_models = MagicMock(return_value=[{"id": "code-model"}])
        provider.loader.ensure_server = MagicMock(side_effect=LlamaCppLoaderError("startup failed"))
        self.assertFalse(provider.connect())
        self.assertEqual(ProviderStatus.ERROR, provider.get_status())


class ModelSelectionTests(unittest.TestCase):
    def test_local_only_router_prefers_llama_cpp_and_excludes_cloud(self):
        local = MagicMock()
        local.profile.name = "llama_cpp:code-model"
        local.profile.provider = "llama_cpp"
        local.profile.is_local = True
        local.profile.context_window = 8192
        local.profile.strengths = ["coding"]
        local.profile.supports_streaming = True
        local.profile.supports_tool_calling = False
        local.profile.supports_function_calling = False
        local.profile.coding_ability = 5
        local.profile.reasoning_ability = 5
        local.profile.cost_per_1k_tokens = 0.0
        cloud = MagicMock()
        cloud.profile = MagicMock(name="cloud-profile")
        cloud.profile.name = "openai:gpt-test"
        cloud.profile.provider = "openai"
        cloud.profile.is_local = False

        model_registry = MagicMock()
        model_registry.catalog.get_all_entries.return_value = [cloud, local]
        model_registry._health = {}
        provider_manager = MagicMock()
        local_provider = MagicMock()
        local_provider.config.enabled = True
        local_provider.is_available.return_value = True
        local_provider.is_connected.return_value = True
        cloud_provider = MagicMock()
        cloud_provider.config.enabled = True
        cloud_provider.is_available.return_value = True
        cloud_provider.is_connected.return_value = True
        provider_manager.registry.get_provider.side_effect = lambda name: {
            "llama_cpp": local_provider, "openai": cloud_provider
        }.get(name)
        provider_manager._health.get_metrics.return_value = None

        with patch("ai.models.router.get_settings_manager") as settings:
            settings.return_value.get.return_value = "local_only"
            selected = ModelRouter(model_registry, provider_manager).select_best_model()

        self.assertEqual("llama_cpp:code-model", selected)




# ============================================================================
# SECTION: Phase 1–4 Architecture, Fast Startup & Paper Ink Theme Suite
# ============================================================================
class Phase1To4AndPaperInkThemeTests(unittest.TestCase):
    """Comprehensive verification for Phase 1–4 upgrades, Fast Startup, and Paper Ink UI/UX Theme System."""

    def test_phase1_intent_classifier_and_routing(self):
        from agent.models.model_catalog_and_router import IntentClassifier, RoutingTier
        decision_fim = IntentClassifier.classify("Complete line", mode="fim")
        self.assertEqual(decision_fim.tier, RoutingTier.TIER_0_FIM)

        decision_arch = IntentClassifier.classify(
            "Architect a 3-phase system design and refactor entire database schema across all files"
        )
        self.assertIn(decision_arch.tier, (RoutingTier.TIER_3_MULTI_FILE_AGENT, RoutingTier.TIER_4_DEEP_ARCHITECTURE))

    def test_phase1_vfs_path_sandboxing_and_patch_engine(self):
        from agent.workspace_tools import WorkspaceVFS, WorkspaceSecurityError
        from agent.code_editing import SmartPatchEngine

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "app.py"
            target.write_text("def greet():\n    return 'hello'\n", encoding="utf-8")

            vfs = WorkspaceVFS(str(root))
            resolved = vfs.resolve_path("app.py")
            self.assertEqual(resolved, target.resolve())
            with self.assertRaises(WorkspaceSecurityError):
                vfs.resolve_path("../../etc/passwd")

            engine = SmartPatchEngine()
            patch_res = engine.apply_patch(
                target.read_text(encoding="utf-8"),
                "def greet():\n    return 'hello'",
                "def greet():\n    return 'hello world'",
            )
            self.assertTrue(patch_res.success)
            self.assertIn("hello world", patch_res.new_content)

    def test_phase2_repo_map_and_self_healing_orchestrator(self):
        from agent.context_and_memory import RepoMapBuilder
        from agent.chat_and_agents import AgentOrchestrator

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "service.py"
            sample.write_text(
                "class AuthService:\n    def login(self, user: str) -> bool:\n        return True\n",
                encoding="utf-8",
            )
            rmap = RepoMapBuilder(root).build_map(query="AuthService login", max_tokens=512)
            self.assertIn("service.py", rmap)
            self.assertIn("class AuthService", rmap)

            orch = AgentOrchestrator(root)
            dag = orch.build_task_dag("Add logout method", target_files=["service.py"])
            res = orch.execute_dag(dag, modified_files=[sample])
            self.assertTrue(res["all_verified"])
            self.assertEqual(res["completed_count"], 3)

    def test_phase3_shadow_sandbox_and_fim_engine(self):
        from agent.code_editing import ShadowWorkspaceSandbox, FIMCompletionEngine
        from agent.context_and_memory import EpisodicMemoryStore

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "calc.py"
            f.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

            with ShadowWorkspaceSandbox(str(root)) as sandbox:
                shadow_calc = sandbox.shadow_root / "calc.py"
                shadow_calc.write_text("def add(a, b):\n    return a + b + 0\n", encoding="utf-8")
                cs = sandbox.compute_change_set()
                self.assertEqual(len(cs.operations), 1)
                apply_res = sandbox.promote_to_workspace()
                self.assertTrue(apply_res.success)
            self.assertIn("a + b + 0", f.read_text(encoding="utf-8"))

            prompt_str = FIMCompletionEngine.build_fim_prompt("def mul(a, b):\n    ", "\n", model_id="qwen2.5-coder:7b")
            self.assertIn("<|fim_prefix|>", prompt_str)

            # Verify lazy initialization of EpisodicMemoryStore (no DB file created until first write/search)
            db_file = root / "lazy_mem.db"
            store = EpisodicMemoryStore(db_file)
            self.assertFalse(db_file.exists())
            store.record_episode("bugfix", "Fixed startup lag", "Used lazy_startup=True on llama_cpp", tags=["startup"])
            self.assertTrue(db_file.exists())
            hits = store.search_memories("startup lag")
            self.assertEqual(len(hits), 1)

    def test_fast_lazy_startup_llama_cpp(self):
        """Verify LlamaCppProvider.connect(lazy_startup=True) registers GGUF models in <10ms without spawning llama-server."""
        from ai.providers.base_provider import ProviderConfig, AuthenticationType
        from ai.providers.llama_cpp_provider import LlamaCppProvider

        with tempfile.TemporaryDirectory() as tmp:
            model_dir = Path(tmp)
            (model_dir / "qwen2.5-coder-7b.gguf").write_bytes(b"GGUF" + b"\x00" * 64)
            cfg = ProviderConfig(
                provider_name="llama_cpp",
                endpoint="http://127.0.0.1:8080/v1",
                auth_type=AuthenticationType.NONE,
                default_model="qwen2.5-coder-7b",
                supports_streaming=True,
                options={"model_directory": str(model_dir)},
            )
            provider = LlamaCppProvider(cfg)
            with unittest.mock.patch.object(provider, "activate_model") as activate_mock:
                t0 = time.perf_counter()
                ok = provider.connect(lazy_startup=True)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                self.assertTrue(ok)
                self.assertLess(elapsed_ms, 50.0)
                activate_mock.assert_not_called()
                self.assertEqual(provider.config.default_model, "qwen2.5-coder-7b")
                self.assertIn("qwen2.5-coder-7b", provider.get_models())

    def test_phase4_agent_patch_extraction_and_intelligence_cache(self):
        """Verify Autonomous Agent Mode SEARCH/REPLACE extraction and ProjectAnalyzer disk cache."""
        from agent.code_editing import SmartPatchEngine
        from core.event_bus import EventBus
        from ai.intelligence.project_analyzer import ProjectAnalyzer

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "router.py").write_text("def route():\n    return 'v1'\n", encoding="utf-8")
            llm_reply = (
                "Here is the surgical patch:\n"
                "FILE: router.py\n"
                "<<<<<<< SEARCH\n"
                "def route():\n"
                "    return 'v1'\n"
                "=======\n"
                "def route():\n"
                "    return 'v4_autonomous'\n"
                ">>>>>>> REPLACE\n"
            )
            ops = SmartPatchEngine.extract_operations_from_llm_response(llm_reply, workspace_root=str(root))
            self.assertEqual(len(ops), 1)
            self.assertEqual(ops[0].source_path, "router.py")

            cache_dir = root / ".owncode"
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / "intelligence_cache.json").write_text(
                '{"project_path": "' + str(root) + '", "summary": {"files": 12}}',
                encoding="utf-8",
            )
            analyzer = ProjectAnalyzer(EventBus())
            cached = analyzer.get_intelligence(root)
            self.assertIsNotNone(cached)

    def test_paper_ink_and_editorial_themes_and_wakeword_removed(self):
        """Verify wake-word module is removed and Paper Ink + editorial themes are registered and render QSS."""
        from ui.design_system import PALETTES, THEME_META, get_design_system, set_design_system_theme

        # 1. Verify wake-word module is completely removed
        project_root = Path(__file__).resolve().parent.parent
        self.assertFalse((project_root / "agent" / "voice_and_wakeword.py").exists())

        # 2. Verify Paper Ink and companion editorial themes are registered
        for theme_key in ("paper_ink", "parchment", "sage_paper", "ink_dark"):
            self.assertIn(theme_key, PALETTES)
            self.assertIn(theme_key, THEME_META)

        paper_ink = PALETTES["paper_ink"]
        self.assertFalse(paper_ink.is_dark)
        self.assertEqual(paper_ink.surface.lower(), "#faf8f5")
        self.assertEqual(paper_ink.text_primary.lower(), "#181816")
        self.assertEqual(paper_ink.accent.lower(), "#1b5e3a")
        self.assertEqual(paper_ink.warning.lower(), "#c85a32")
        self.assertEqual(THEME_META["paper_ink"].label, "Paper Ink")

        # 3. Verify switching to Paper Ink generates valid global QSS
        ds = set_design_system_theme("paper_ink")
        self.assertEqual(ds.theme, "paper_ink")
        qss = ds.get_stylesheet("global")
        self.assertIn("#1b5e3a", qss.lower())
        self.assertIn("#faf8f5", qss.lower())



    def test_mainwindow_and_sidebar_instantiation_and_theme_switching(self):
        """Verify MainWindow, Sidebar, Dashboard, TitleBar, and AIWorkspace instantiate cleanly and switch themes."""
        from PySide6.QtWidgets import QApplication
        from core.event_and_compat import EventBus
        from tools.theme_and_settings import ThemeManager, PALETTES
        from ui.main_window import MainWindow

        app = QApplication.instance() or QApplication([])
        bus = EventBus()
        tm = ThemeManager(app)
        tm.apply_theme("paper_ink")

        window = MainWindow(bus)
        window.set_theme_manager(tm)
        self.assertIsNotNone(window.sidebar)
        self.assertIsNotNone(window.center.dashboard)
        self.assertIsNotNone(window.ai_workspace)
        self.assertIsNotNone(window.titlebar)

        for theme_key in ("paper_ink", "parchment", "sage_paper", "ink_dark", "graphite", "paper"):
            self.assertIn(theme_key, PALETTES)
            window._on_theme_selected(theme_key)
            self.assertEqual(tm.get_current_theme(), theme_key)


    def test_autonomous_agent_creates_file_and_opens_editor_from_qwen_output(self):
        '''Verify exact screenshot scenario: Agent mode creates linked_list.py in workspace and opens editor tab.'''
        import tempfile
        from core.event_bus import EventBus
        from agent.code_editing import SmartPatchEngine
        from agent.chat_and_agents import AIChatEngine
        from ai.providers.provider_registry import ProviderRegistry
        from ai.providers.provider_manager import ProviderManager
        from ai.models.model_registry import ModelRegistry
        from ai.models.model_center import ModelCenter

        bus = EventBus()
        opened_files = []
        applied_events = []
        bus.subscribe("file_opened", lambda d: opened_files.append(d))
        bus.subscribe("ai_agent_operations_applied", lambda d: applied_events.append(d))

        reg = ProviderRegistry(config_dir="config/providers")
        pm = ProviderManager(reg, bus)
        mr = ModelRegistry(reg)
        mc = ModelCenter(reg, pm, mr)
        engine = AIChatEngine(bus, reg, pm, mc, mr)

        with tempfile.TemporaryDirectory() as tmp_ws:
            bus.publish("workspace_loaded", {"path": tmp_ws})
            self.assertEqual(Path(engine.workspace_root).resolve(), Path(tmp_ws).resolve())

            qwen_response = (
                "Sure, I can help you create a new file and add a linked list function. "
                "Let\x27s create a Python file named linked_list.py and add a simple linked list implementation.\n\n"
                "Here\x27s the code:\n\n"
                "```python\n"
                "# linked_list.py\n\n"
                "class Node:\n"
                "    def __init__(self, data):\n"
                "        self.data = data\n"
                "        self.next = None\n\n"
                "class LinkedList:\n"
                "    def __init__(self):\n"
                "        self.head = None\n"
                "```\n"
            )
            user_prompt = "create a file and add a linked list funiton on it"
            ops = SmartPatchEngine.extract_operations_from_llm_response(
                qwen_response,
                workspace_root=tmp_ws,
                user_prompt=user_prompt,
            )
            self.assertEqual(len(ops), 1)
            self.assertEqual(ops[0].source_path, "linked_list.py")

            applied = engine.apply_agent_operations(ops, workspace_root=tmp_ws, user_prompt=user_prompt)
            self.assertEqual(len(applied), 1)
            created_path = Path(tmp_ws) / "linked_list.py"
            self.assertTrue(created_path.is_file())
            self.assertIn("class LinkedList:", created_path.read_text(encoding="utf-8"))
            self.assertTrue(any(Path(f.get("path", "")).name == "linked_list.py" for f in opened_files))
            self.assertEqual(len(applied_events), 1)

    def test_one_click_apply_code_block_event_writes_to_workspace(self):
        '''Verify clicking Apply to File on a code block writes the file to the workspace and opens it.'''
        import tempfile
        from core.event_bus import EventBus
        from agent.chat_and_agents import AIChatEngine
        from ai.providers.provider_registry import ProviderRegistry
        from ai.providers.provider_manager import ProviderManager
        from ai.models.model_registry import ModelRegistry
        from ai.models.model_center import ModelCenter

        bus = EventBus()
        opened_files = []
        bus.subscribe("file_opened", lambda d: opened_files.append(d))

        reg = ProviderRegistry(config_dir="config/providers")
        pm = ProviderManager(reg, bus)
        mr = ModelRegistry(reg)
        mc = ModelCenter(reg, pm, mr)
        engine = AIChatEngine(bus, reg, pm, mc, mr)

        with tempfile.TemporaryDirectory() as tmp_ws:
            engine.set_workspace_root(tmp_ws)
            bus.publish("ai_apply_code_block", {
                "code": "# bst_tree.py\ndef insert_node(root, val):\n    return val\n",
                "lang": "python",
            })
            target = Path(tmp_ws) / "bst_tree.py"
            self.assertTrue(target.is_file())
            self.assertTrue(any(Path(f.get("path", "")).name == "bst_tree.py" for f in opened_files))


    def test_v45_agent_powers_prefetch_multifile_undo_and_verification(self):
        """Verify all 5 v4.5 Autonomous Agent Powers."""
        import tempfile
        from core.event_bus import EventBus
        from agent.code_editing import SmartPatchEngine
        from agent.chat_and_agents import AIChatEngine, SelfHealingVerifier
        from ai.providers.provider_registry import ProviderRegistry
        from ai.providers.provider_manager import ProviderManager
        from ai.models.model_registry import ModelRegistry
        from ai.models.model_center import ModelCenter

        bus = EventBus()
        reg = ProviderRegistry(config_dir="config/providers")
        pm = ProviderManager(reg, bus)
        mr = ModelRegistry(reg)
        mc = ModelCenter(reg, pm, mr)
        engine = AIChatEngine(bus, reg, pm, mc, mr)

        with tempfile.TemporaryDirectory() as tmp_ws:
            ws_path = Path(tmp_ws)
            engine.set_workspace_root(tmp_ws)

            # Seed an existing file to test fuzzy context pre-fetching & modification
            existing_c = ws_path / "linked_list.c"
            existing_c.write_text("#include <stdio.h>\nint main() { return 0; }\n", encoding="utf-8")

            # Power 1: Context pre-fetching (fuzzy stem match + runtime error injection)
            engine.last_executed_file = str(existing_c)
            engine.last_execution_error = "Segmentation fault at node->next"
            prefetched = engine._prefetch_workspace_context_for_prompt(
                "fix the crash in linked list", ws_path
            )
            self.assertIn("linked_list.c", prefetched)
            self.assertIn("Segmentation fault at node->next", prefetched)

            # Power 2: ReAct inspection directives (READ: and SEARCH:)
            obs = engine._execute_agent_inspection_directives(
                "READ: linked_list.c\nSEARCH: stdio.h", ws_path
            )
            self.assertEqual(len(obs), 2)
            self.assertIn("#include <stdio.h>", obs[0])
            self.assertIn("linked_list.c:1:", obs[1])

            # Power 2 & 4: Multi-file CREATE + MODIFY + Rollback Checkpoint Undo
            llm_multi_response = (
                "FILE: math_utils.py\n"
                "```python\n"
                "# math_utils.py\n"
                "def square(x):\n"
                "    return x * x\n\n"
                "if __name__ == '__main__':\n"
                "    print('SQUARE_5=', square(5))\n"
                "```\n\n"
                "FILE: linked_list.c\n"
                "<<<<<<< SEARCH\n"
                "int main() { return 0; }\n"
                "=======\n"
                "int main() { printf(\"OK\\n\"); return 0; }\n"
                ">>>>>>> REPLACE\n"
            )
            ops = SmartPatchEngine.extract_operations_from_llm_response(
                llm_multi_response, workspace_root=tmp_ws
            )
            self.assertEqual(len(ops), 2)
            applied = engine.apply_agent_operations(ops, workspace_root=tmp_ws, user_prompt="create math_utils and update linked_list.c")
            self.assertEqual(len(applied), 2)
            self.assertTrue((ws_path / "math_utils.py").is_file())
            self.assertIn('printf("OK\\n")', existing_c.read_text(encoding="utf-8"))
            self.assertTrue(all(item.get("verified") for item in applied))

            # Power 4: Autonomous safe execution of created file
            run_res = engine.run_and_verify_file(str(ws_path / "math_utils.py"))
            self.assertTrue(run_res.get("success"))
            self.assertIn("SQUARE_5= 25", run_res.get("stdout", ""))

            # Power 4: 1-Click Checkpoint Undo restores linked_list.c and removes math_utils.py
            undo_res = engine.undo_last_agent_action()
            self.assertTrue(undo_res.get("success"))
            self.assertFalse((ws_path / "math_utils.py").exists())
            self.assertNotIn('printf("OK\\n")', existing_c.read_text(encoding="utf-8"))

            # Power 3: Multi-language verifier detects Python & C syntax errors
            verifier = SelfHealingVerifier(ws_path)
            broken_py = ws_path / "broken.py"
            broken_py.write_text("def foo(\n    return 1\n", encoding="utf-8")
            vres = verifier.verify_file(broken_py)
            self.assertFalse(vres.get("passed"))
            self.assertEqual(vres.get("stage"), "ast_syntax")


    def test_v46_live_agent_process_feed_and_no_ask_gemini_label(self):
        """Verify live Agent process status detection, clean summary card without raw code dump, clean path stripping, and Run Agent / Send button label."""
        import tempfile
        from PySide6.QtWidgets import QApplication
        from core.event_bus import EventBus
        from agent.code_editing import SmartPatchEngine
        from agent.chat_and_agents import AIChatEngine
        from ui.ai_workspace import AIWorkspace

        app = QApplication.instance() or QApplication([])
        bus = EventBus()
        aw = AIWorkspace(event_bus=bus)
        # Button must never say 'Ask Gemini'
        self.assertNotEqual(aw._send_btn.text(), "Ask Gemini")
        self.assertIn(aw._send_btn.text(), ("Run Agent", "Send"))

        # Accidental internal folder prefix 'tools/stack.py' is stripped to 'stack.py'
        self.assertEqual(SmartPatchEngine._clean_candidate_path("tools/stack.py"), "stack.py")

        # Live process state detection shows real process headline + symbols + line count
        in_flight = "FILE: stack.py\n```python\nclass Stack:\n    def push(self, x):\n        pass\n    def pop(self):\n        pass\n"
        state = AIChatEngine._detect_live_agent_process_state(in_flight, "create a python file and write stack function in it")
        self.assertEqual(state["phase"], "coding")
        self.assertIn("stack.py", state["headline"])
        self.assertIn("Stack", state["detail"])
        self.assertIn("push", state["detail"])

        # Clean summary markdown shows process steps without dumping the raw 30-line code block
        with tempfile.TemporaryDirectory() as tmp_ws:
            f_stack = Path(tmp_ws) / "stack.py"
            f_stack.write_text("class Stack:\n    def push(self, x):\n        pass\n    def pop(self):\n        pass\n", encoding="utf-8")
            summary = AIChatEngine._build_clean_agent_summary_markdown(
                [{"action": "Created", "rel_path": "stack.py", "full_path": str(f_stack), "verified": True, "stage": "ast_syntax"}],
                in_flight + "```\nThis code defines a simple stack data structure...",
                Path(tmp_ws),
            )
            self.assertIn("**Created `stack.py`**", summary)
            self.assertIn("Symbols: `Stack, push, pop`", summary)
            self.assertIn("Verified", summary)
            self.assertNotIn("This code defines a simple stack data structure", summary)


if __name__ == "__main__":
    unittest.main()
