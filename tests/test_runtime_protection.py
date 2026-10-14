"""Headless incident regressions: no Tk initialization or game conversion."""
import ast
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime_log import RunLog, ExitGuard


def gui_method(name, **globals):
    tree = ast.parse((ROOT / "gui.py").read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PS5ContainerBuilderApp")
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = dict(globals)
    exec(compile(ast.Module(body=[method], type_ignores=[]), "gui.py", "exec"), ns)
    return ns[name]


class ProtectionTests(unittest.TestCase):
    def test_close_during_conversion_never_terminates_or_destroys(self):
        app = types.SimpleNamespace(is_running=True, run_log=Mock(), root=Mock(), current_process=Mock())
        gui_method("_on_close", messagebox=Mock())(app)
        app.current_process.terminate.assert_not_called()
        app.root.destroy.assert_not_called()
        app.run_log.event.assert_called_once_with("close_blocked")

    def test_idle_close_with_live_worker_is_blocked(self):
        app = types.SimpleNamespace(is_running=False, run_log=Mock(), root=Mock(), current_process=Mock())
        gui_method("_on_close", messagebox=Mock())(app)
        app.root.destroy.assert_not_called()
        app.current_process.terminate.assert_not_called()

    def test_cancel_declined_leaves_process_and_state_unchanged(self):
        app = types.SimpleNamespace(is_running=True, is_cancelled=False, current_process=Mock())
        gui_method("_on_cancel", messagebox=types.SimpleNamespace(askyesno=lambda *a: False))(app)
        self.assertFalse(app.is_cancelled)
        app.current_process.terminate.assert_not_called()

    def test_signal_handler_does_not_exit_or_touch_processes(self):
        guard = ExitGuard()
        guard.receive(signal.SIGTERM, None)
        self.assertEqual(guard.pending_signal, signal.SIGTERM)

    def test_progress_persists_before_log_close(self):
        with tempfile.TemporaryDirectory(prefix="ps5-log-test-") as tmp:
            log = RunLog(tmp)
            log.event("output", text="[####] 32% compress")
            log.event("child_exit", pid=123, returncode=-15, signal=15)
            rows = [json.loads(line) for line in log.path.read_text().splitlines()]
            self.assertEqual(rows[-1]["signal"], 15)
            self.assertIn("32%", rows[-2]["text"])
            log.close()
            self.assertEqual(json.loads(log.path.read_text().splitlines()[-1])["event"], "application_exit")

    def test_abrupt_helper_exit_retains_progress_without_false_success(self):
        with tempfile.TemporaryDirectory(prefix="ps5-log-crash-test-") as tmp:
            command = [sys.executable, "-c",
                       "import os,sys; from runtime_log import RunLog; log=RunLog(sys.argv[1]); "
                       "log.event('conversion_start'); log.event('output',text='progress'); os._exit(3)", tmp]
            result = subprocess.run(command, cwd=ROOT, check=False)
            self.assertEqual(result.returncode, 3)
            paths = list(Path(tmp).glob("*.jsonl"))
            self.assertEqual(len(paths), 1)
            events = [json.loads(line)["event"] for line in paths[0].read_text().splitlines()]
            self.assertIn("output", events)
            self.assertNotIn("conversion_end", events)
            self.assertNotIn("application_exit", events)

    def test_real_small_child_nonzero_exit_is_recorded(self):
        with tempfile.TemporaryDirectory(prefix="ps5-child-test-") as tmp:
            log = RunLog(tmp)
            app = types.SimpleNamespace(run_log=log, current_process=None)
            method = gui_method("run_command_stream", sys=sys, subprocess=subprocess,
                                read_stream_by_lines=lambda s: iter(s), traceback=__import__("traceback"))
            self.assertFalse(method(app, [sys.executable, "-c", "print('synthetic failure'); raise SystemExit(7)"]))
            rows = [json.loads(line) for line in log.path.read_text().splitlines()]
            self.assertEqual(rows[-1]["event"], "child_exit")
            self.assertEqual(rows[-1]["returncode"], 7)
            self.assertIsNone(app.current_process)
            log.close()


if __name__ == "__main__":
    unittest.main()
