from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import anyio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.workbench import WorkbenchService
from hardness.providers import MockProviderAdapter
from hardness.state_store import StateStore


def _make_service(root: Path) -> WorkbenchService:
    return WorkbenchService(
        workspace_root=root,
        storage_base=root / ".storage",
        api_file=root / "api.txt",
    )


def _write_run(state, run_id: str, events: list[dict]) -> None:
    runs_dir = state.storage_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / f"{run_id}.json").write_text(
        json.dumps({"events": events}), encoding="utf-8"
    )
    state.run_ids.append(run_id)


class CollectEventsTests(unittest.TestCase):
    """Global index must be monotonically increasing across multiple runs."""

    def test_global_index_sequential_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            _write_run(state, "run-A", [
                {"kind": "run_started", "payload": {}, "timestamp": "2026-01-01T00:00:00"},
                {"kind": "tool_selected", "payload": {}, "timestamp": "2026-01-01T00:00:01"},
            ])
            _write_run(state, "run-B", [
                {"kind": "run_started", "payload": {}, "timestamp": "2026-01-01T00:01:00"},
                {"kind": "run_completed", "payload": {}, "timestamp": "2026-01-01T00:01:01"},
            ])
            events = svc.collect_events(state.session_id)
            indices = [e["index"] for e in events]
            self.assertEqual(indices, [0, 1, 2, 3])
            # run order preserved: A before B
            self.assertEqual(events[0]["run_id"], "run-A")
            self.assertEqual(events[2]["run_id"], "run-B")

    def test_event_zero_not_skipped_with_after_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            _write_run(state, "run-A", [
                {"kind": "run_started", "payload": {}, "timestamp": "2026-01-01T00:00:00"},
            ])
            events = svc.collect_events(state.session_id, after=0)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["index"], 0)

    def test_cursor_after_first_run_does_not_drop_second_run_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            _write_run(state, "run-A", [
                {"kind": "run_started", "payload": {}, "timestamp": "2026-01-01T00:00:00"},
                {"kind": "run_completed", "payload": {}, "timestamp": "2026-01-01T00:00:01"},
            ])
            # cursor sits at 2 (= 2 events consumed)
            empty = svc.collect_events(state.session_id, after=2)
            self.assertEqual(empty, [])

            _write_run(state, "run-B", [
                {"kind": "run_started", "payload": {}, "timestamp": "2026-01-01T00:01:00"},
            ])
            new_events = svc.collect_events(state.session_id, after=2)
            self.assertEqual(len(new_events), 1)
            self.assertEqual(new_events[0]["index"], 2)
            self.assertEqual(new_events[0]["run_id"], "run-B")

    def test_no_local_key_leaks_into_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            _write_run(state, "run-A", [
                {"kind": "run_started", "payload": {}, "timestamp": "2026-01-01T00:00:00"},
            ])
            events = svc.collect_events(state.session_id)
            self.assertNotIn("_local", events[0])


class ImportSessionTests(unittest.TestCase):
    """export_session / import_session must faithfully round-trip all state."""

    def test_import_restores_paused_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            state.status = "paused"
            state.pending_task = "build something"
            state.pending_max_turns = 12
            state.messages = [{"role": "user", "content": "hello", "timestamp": "t"}]

            exported = svc.export_session(state.session_id)
            imported = svc.import_session(exported)

            self.assertEqual(imported.status, "paused")
            self.assertEqual(imported.pending_task, "build something")
            self.assertEqual(imported.pending_max_turns, 12)
            self.assertEqual(len(imported.messages), 1)

    def test_import_restores_waiting_for_input_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            state.status = "waiting_for_input"
            state.pending_task = "needs answer"
            state.waiting_question = "What color?"
            state.waiting_options = ["red", "blue"]

            exported = svc.export_session(state.session_id)
            imported = svc.import_session(exported)

            self.assertEqual(imported.status, "waiting_for_input")
            self.assertEqual(imported.waiting_question, "What color?")
            self.assertEqual(imported.waiting_options, ["red", "blue"])

    def test_import_includes_final_text_and_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            state.latest_result = {"final_text": "Done!", "metrics": {"turns": 3}}

            exported = svc.export_session(state.session_id)
            self.assertEqual(exported["final_text"], "Done!")
            self.assertEqual(exported["metrics"], {"turns": 3})

    def test_import_rejects_workspace_outside_service_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            with self.assertRaises(ValueError):
                svc.import_session({"workspace": "/", "messages": []})

    def test_import_rejects_too_many_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            with self.assertRaises(ValueError):
                svc.import_session({
                    "workspace": str(root),
                    "messages": [{"role": "user", "content": "x"}] * 501,
                })

    def test_import_rejects_non_dict_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svc = _make_service(root)
            with self.assertRaises((ValueError, AttributeError)):
                svc.import_session("not a dict")  # type: ignore[arg-type]


class WorkspaceConfinementTests(unittest.TestCase):
    """Session workspace must be within the service root."""

    def test_workspace_within_root_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sub = root / "projects" / "myapp"
            sub.mkdir(parents=True)
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(sub))
            self.assertTrue(state.workspace_root.is_relative_to(root))

    def test_workspace_outside_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = (Path(tmp) / "service").resolve()
            root.mkdir()
            svc = _make_service(root)
            with self.assertRaises(ValueError):
                svc.create_session("mock", "mock", workspace=str(Path(tmp).resolve()))

    def test_workspace_equal_to_root_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))
            self.assertEqual(state.workspace_root, root)


class SseStreamIntegrationTest(unittest.TestCase):
    """Integration: stream_events delivers events in real time as they land on disk."""

    def test_stream_yields_events_added_between_poll_cycles(self) -> None:
        """Write one event, start the async stream, add a second event after one poll
        cycle (~0.8s), verify both events arrive via stream_events."""

        async def _run() -> list[dict]:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                svc = _make_service(root)
                state = svc.create_session("mock", "mock", workspace=str(root))

                store = StateStore(state.storage_root)
                run_id = StateStore.new_run_id()
                state.run_ids.append(run_id)
                store.create_run("live-test", run_id=run_id)
                store.append_event(run_id, {
                    "kind": "run_started",
                    "payload": {"task": "live-test"},
                    "timestamp": "2026-01-01T00:00:00",
                })

                received: list[dict] = []

                async def add_second_event() -> None:
                    await anyio.sleep(1.1)  # wait > one poll cycle (0.8 s)
                    store.append_event(run_id, {
                        "kind": "tool_selected",
                        "payload": {"tool": "read"},
                        "timestamp": "2026-01-01T00:00:01",
                    })

                async with anyio.create_task_group() as tg:
                    tg.start_soon(add_second_event)
                    with anyio.move_on_after(5):
                        async for chunk in svc.stream_events(state.session_id):
                            if chunk.startswith("data: "):
                                received.append(json.loads(chunk[6:].strip()))
                            if len(received) >= 2:
                                break

                return received

        received = anyio.run(_run, backend="asyncio")
        self.assertGreaterEqual(len(received), 2, "Expected ≥2 events from stream")
        self.assertEqual(received[0]["kind"], "run_started")
        self.assertEqual(received[1]["kind"], "tool_selected")

    def test_collect_events_finds_run_started_while_run_in_progress(self) -> None:
        """With run_id pre-registered, collect_events must return run_started before
        the run finishes.  MockProviderAdapter.generate is patched to sleep briefly
        so there is a window to poll during execution."""

        original_generate = MockProviderAdapter.generate

        def slow_generate(self, messages, tools):  # noqa: ANN001
            time.sleep(0.4)           # pause before returning — gives poll thread a window
            return original_generate(self, messages, tools)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            svc = _make_service(root)
            state = svc.create_session("mock", "mock", workspace=str(root))

            events_mid_run: list[dict] = []
            run_done = threading.Event()

            def do_run() -> None:
                try:
                    svc.run_task(session_id=state.session_id, task="hello harness", max_turns=1)
                except Exception:
                    pass
                finally:
                    run_done.set()

            with patch.object(MockProviderAdapter, "generate", slow_generate):
                threading.Thread(target=do_run, daemon=True).start()

                deadline = time.monotonic() + 5.0
                while not run_done.is_set() and time.monotonic() < deadline:
                    batch = svc.collect_events(state.session_id)
                    if batch:
                        events_mid_run.extend(batch)
                        break
                    time.sleep(0.05)

            run_done.wait(timeout=10)

        self.assertTrue(
            len(events_mid_run) > 0,
            "collect_events returned nothing during the run — "
            "run_id was likely not pre-registered before AgentLoop.run()",
        )
        kinds = {e["kind"] for e in events_mid_run}
        self.assertIn("run_started", kinds)


if __name__ == "__main__":
    unittest.main()
