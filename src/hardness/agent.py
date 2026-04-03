from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Callable
from typing import Any

from hardness.config import HardnessConfig
from hardness.memory import MemoryManager, iter_verified_facts
from hardness.policy import PolicyEngine, PolicyError
from hardness.prompting import build_followup_user_message, build_messages
from hardness.providers import ProviderError, build_provider_adapter
from hardness.router import ModelRouter
from hardness.state_store import StateStore
from hardness.tools import ListTool, PythonCheckTool, ReadTool, SearchTool, ToolRegistry, WriteTool
from hardness.types import AgentTraceEvent, Message, RunMetrics, ToolResult


class AgentLoop:
    def __init__(self, config: HardnessConfig) -> None:
        self.config = config
        self.store = StateStore(config.storage_root)
        self.memory = MemoryManager(self.store, config.memory)
        self.policy = PolicyEngine(config.policy)
        self.router = ModelRouter(config)
        self.tools = ToolRegistry([
            ReadTool(self.policy),
            WriteTool(self.policy),
            SearchTool(self.policy),
            PythonCheckTool(self.policy),
            ListTool(self.policy),
        ])
        self.provider = build_provider_adapter(config.provider)

    def run(
        self,
        task: str,
        session_messages: list[Message] | None = None,
        should_interrupt: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        run_id = self.store.create_run(task)
        metrics = RunMetrics()
        self._event(run_id, "run_started", {"task": task})
        if session_messages:
            for message in session_messages:
                self.memory.append_session(message)
        self.memory.append_session(Message(role="user", content=task))
        provider_config, routing = self.router.route(task, opportunistic=self.config.enable_opportunistic_qwen)
        self.provider = build_provider_adapter(provider_config)
        self._event(run_id, "routing_decision", asdict(routing))
        consecutive_tool_failures = 0
        repeated_actions = 0
        no_progress_turns = 0
        last_action_signature: tuple[str, tuple[tuple[str, Any], ...]] | None = None
        last_success_signature: tuple[str, tuple[tuple[str, Any], ...], str] | None = None
        recent_success = False
        final_after_success = 0
        redundant_reads = 0
        success_signal = False
        success_turn: int | None = None
        post_success_extra_actions = 0
        success_recognized = False
        explicit_completion = False
        weak_final = False
        finalization_delay_turns = 0
        reflection_turn_used = False
        final_repair_used = False
        tool_results: list[ToolResult] = []
        stop_reason = "completed"
        final_text = ""

        for turn in range(1, self.config.runtime.max_turns + 1):
            if should_interrupt and should_interrupt():
                stop_reason = "user_interrupted"
                final_text = "Run interrupted by user request."
                self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason, "source": "interrupt_flag"})
                break

            metrics.turns += 1
            snapshot = self.memory.retrieve(task)
            self._event(run_id, "memory_retrieved", {"turn": turn, "notes": len(snapshot.indexed_notes), "session_messages": len(snapshot.session_messages)})

            messages = build_messages(task, snapshot, self.tools.schema())
            if recent_success and tool_results:
                messages.append(
                    build_followup_user_message(
                        task,
                        recent_tool_summary=f"{tool_results[-1].name}: {tool_results[-1].content[:500]}",
                        require_final=True,
                    )
                )
            self._event(run_id, "prompt_built", {"turn": turn, "message_count": len(messages), "tool_count": len(self.tools.schema())})

            try:
                metrics.provider_calls += 1
                response = self.provider.generate(messages, self.tools.schema())
            except ProviderError as exc:
                metrics.parse_failures += 1
                self._event(run_id, "provider_error", {"turn": turn, "error": str(exc)})
                return {"run_id": run_id, "status": "error", "error": str(exc), "metrics": asdict(metrics)}

            self._event(run_id, "provider_response", {"turn": turn, "finish_reason": response.finish_reason, "stop_reason": response.stop_reason, "tool_calls": len(response.tool_calls), "usage": response.usage})

            if response.tool_calls:
                progress_this_turn = False
                for tool_call in response.tool_calls:
                    if should_interrupt and should_interrupt():
                        stop_reason = "user_interrupted"
                        final_text = "Run interrupted by user request."
                        self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason, "source": "interrupt_flag"})
                        break

                    metrics.tool_calls += 1
                    if tool_call.name in {"final", "stop", "needs_clarification"}:
                        stop_reason = tool_call.name
                        final_text = response.text or f"Stopped with control decision: {tool_call.name}."
                        clarification: dict[str, Any] | None = None
                        if tool_call.name == "needs_clarification":
                            question = str(tool_call.arguments.get("question", "Need additional user clarification."))
                            options_value = tool_call.arguments.get("options")
                            options = options_value if isinstance(options_value, list) else []
                            clarification = {
                                "question": question,
                                "options": [str(option) for option in options],
                            }
                            if not final_text.strip():
                                final_text = question
                        if success_signal and tool_call.name in {"final", "stop"}:
                            success_recognized = True
                            explicit_completion = bool(final_text.strip())
                            if success_turn is not None:
                                finalization_delay_turns = max(0, turn - success_turn)
                        self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason, "source": "control_tool_call"})
                        if clarification is not None:
                            self._event(run_id, "clarification_requested", {"turn": turn, **clarification})
                        break
                    signature = (tool_call.name, tuple(sorted(tool_call.arguments.items())))
                    if signature == last_action_signature:
                        repeated_actions += 1
                        metrics.repeated_actions += 1
                    else:
                        repeated_actions = 0
                    last_action_signature = signature
                    self._event(run_id, "tool_selected", {"turn": turn, "tool": tool_call.name, "arguments": tool_call.arguments, "repeated_actions": repeated_actions})

                    if success_signal and success_turn is not None and turn > success_turn:
                        redundant_post_success = bool(last_success_signature and signature == last_success_signature[:2])
                        if redundant_post_success:
                            post_success_extra_actions += 1
                            if not reflection_turn_used:
                                reflection_turn_used = True
                                self.memory.append_session(
                                    Message(
                                        role="user",
                                        content=(
                                            "The goal appears achieved. Reflection-only turn allowed now: do not call tools again unless strictly necessary. "
                                            "Provide a clean final answer with explicit completion."
                                        ),
                                    )
                                )
                                self._event(
                                    run_id,
                                    "post_success_gate",
                                    {"turn": turn, "mode": "soft_reflection", "blocked_tool": tool_call.name},
                                )
                                break
                            stop_reason = "post_success_extra_action_limit"
                            final_text = response.text or "Stopped after repeated redundant post-success tool attempts."
                            weak_final = True
                            finalization_delay_turns = max(0, turn - success_turn)
                            self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason, "source": "post_success_gate_hard"})
                            break

                    if tool_call.name == "read" and last_success_signature and signature == last_success_signature[:2]:
                        redundant_reads += 1
                        stop_reason = "redundant_read_suppressed"
                        self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason})
                        final_text = "Stopped because the same read was requested again without new justification."
                        break

                    if repeated_actions >= self.config.runtime.max_repeated_identical_actions:
                        stop_reason = "repeated_action_limit"
                        self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason})
                        final_text = "Stopped because the model repeated the same tool action without progress."
                        break

                    try:
                        result = self.tools.execute(tool_call.name, tool_call.arguments)
                    except (KeyError, FileNotFoundError, PolicyError, OSError, ValueError) as exc:
                        consecutive_tool_failures += 1
                        metrics.tool_failures += 1
                        result = ToolResult(name=tool_call.name, success=False, content=str(exc), metadata={"arguments": tool_call.arguments})
                    else:
                        consecutive_tool_failures = 0
                        progress_this_turn = True
                        recent_success = True
                        success_signal = True
                        if success_turn is None:
                            success_turn = turn
                        last_success_signature = (tool_call.name, tuple(sorted(tool_call.arguments.items())), result.content)
                    tool_results.append(result)
                    self.memory.store_artifact(run_id, result)
                    self._event(run_id, "tool_executed", {"turn": turn, **asdict(result)})
                    self.memory.append_session(Message(role="tool", content=f"{result.name}: {result.content}"))

                    if result.success and result.name == "write":
                        verified = self._verify_write_result(result)
                        if verified:
                            metrics.verified_writes += 1
                        self._event(run_id, "write_verified", {"turn": turn, "verified": verified, "path": result.metadata.get("path")})

                        # Auto py_check: run immediately after writing any .py file
                        written_path = str(result.metadata.get("path", ""))
                        if written_path.endswith(".py"):
                            try:
                                check = self.tools.execute("py_check", {"path": written_path})
                                self._event(run_id, "py_check_result", {"turn": turn, "path": written_path, "ok": check.success, "detail": check.content})
                                if not check.success:
                                    self.memory.append_session(Message(
                                        role="user",
                                        content=(
                                            f"AUTOMATIC py_check FAILED for {written_path}:\n{check.content}\n"
                                            "Fix the syntax error in the next tool call before proceeding."
                                        ),
                                    ))
                            except Exception as _exc:
                                self._event(run_id, "py_check_error", {"turn": turn, "path": written_path, "error": str(_exc)})

                        if verified and task.lower().startswith("write "):
                            stop_reason = "write_completed"
                            final_text = f"Write completed and verified at {result.metadata.get('path')}."
                            success_signal = True
                            success_recognized = True
                            explicit_completion = True
                            if success_turn is None:
                                success_turn = turn
                            finalization_delay_turns = max(0, turn - success_turn)
                            self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason, "source": "write_gate"})
                            break

                    if consecutive_tool_failures >= self.config.runtime.max_consecutive_tool_failures:
                        stop_reason = "tool_failure_limit"
                        self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason})
                        final_text = "Stopped because tool failures exceeded the configured limit."
                        break

                if stop_reason != "completed":
                    break
                if progress_this_turn:
                    no_progress_turns = 0
                else:
                    no_progress_turns += 1
            else:
                final_text = response.text
                stop_reason = response.stop_reason or "completed"
                if recent_success:
                    final_after_success += 1
                if success_signal:
                    if stop_reason in {"stop", "completed", "write_completed"}:
                        success_recognized = True
                    explicit_completion = self._is_explicit_completion(final_text) and success_recognized
                    if success_turn is not None:
                        finalization_delay_turns = max(0, turn - success_turn)
                    if not explicit_completion and not final_repair_used:
                        final_repair_used = True
                        self.memory.append_session(Message(role="assistant", content=final_text or ""))
                        self.memory.append_session(
                            Message(
                                role="user",
                                content=(
                                    "Rephrase the final answer to explicitly confirm task completion. "
                                    "Do not add new actions or new tool calls."
                                ),
                            )
                        )
                        self._event(run_id, "final_repair_requested", {"turn": turn, "reason": "missing_explicit_completion"})
                        stop_reason = "completed"
                        continue
                self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason})
                break

            if no_progress_turns >= self.config.runtime.max_no_progress_turns:
                stop_reason = "no_progress_limit"
                final_text = "Stopped because repeated turns produced no measurable progress."
                metrics.no_progress_stop_count += 1
                self._event(run_id, "stop_decision", {"turn": turn, "reason": stop_reason})
                break
        else:
            stop_reason = "max_turns_reached"
            final_text = "Stopped because max turns was reached."
            self._event(run_id, "stop_decision", {"turn": self.config.runtime.max_turns, "reason": stop_reason})

        verified_count = 0
        for title, content in iter_verified_facts(tool_results):
            self.memory.promote_verified_note(title=title, content=content, source=run_id)
            verified_count += 1
        self._event(run_id, "verification_completed", {"promoted_notes": verified_count})

        if metrics.tool_calls:
            metrics.duplicate_action_rate = metrics.repeated_actions / metrics.tool_calls
            metrics.redundant_read_rate = redundant_reads / metrics.tool_calls
            metrics.post_success_extra_action_rate = post_success_extra_actions / metrics.tool_calls
        if metrics.turns:
            metrics.mean_turns_to_completion = float(metrics.turns)
        if tool_results:
            metrics.final_after_success_rate = final_after_success / max(1, len([result for result in tool_results if result.success]))
        if success_signal:
            stable_stop = stop_reason in {"stop", "completed", "write_completed"}
            if stable_stop and not success_recognized:
                success_recognized = True
            if success_turn is not None and finalization_delay_turns == 0:
                finalization_delay_turns = max(0, metrics.turns - success_turn)
            weak_final = weak_final or (not stable_stop) or (not final_text.strip())
            metrics.success_recognized_rate = 1.0 if success_recognized else 0.0
            metrics.explicit_completion_rate = 1.0 if explicit_completion else 0.0
            metrics.weak_final_rate = 1.0 if weak_final else 0.0
            metrics.finalization_delay_rate = finalization_delay_turns / max(1, metrics.turns)
            metrics.finalization_correctness_rate = 1.0 if (stable_stop and success_recognized) else 0.0
            metrics.finalization_quality_rate = 1.0 if (explicit_completion and not weak_final) else 0.0

        if tool_results and not final_text:
            final_text = "\n".join(f"[{result.name}] {result.content}" for result in tool_results)
        self.memory.append_session(Message(role="assistant", content=final_text))
        self._event(run_id, "run_completed", {"final_text": final_text, "stop_reason": stop_reason, "metrics": asdict(metrics)})

        return {
            "run_id": run_id,
            "status": "ok",
            "final_text": final_text,
            "tool_results": [asdict(result) for result in tool_results],
            "metrics": asdict(metrics),
            "stop_reason": stop_reason,
            "awaiting_user_input": stop_reason == "needs_clarification",
            "completed_at": datetime.now(UTC).isoformat(),
        }

    def _verify_write_result(self, result: ToolResult) -> bool:
        path_value = result.metadata.get("verify_path")
        if not path_value:
            return False
        try:
            path = self.policy.authorize_path(path_value)
            return path.exists()
        except PolicyError:
            return False

    def _event(self, run_id: str, kind: str, payload: dict[str, Any]) -> None:
        event = AgentTraceEvent(kind=kind, payload=payload)
        self.store.append_event(run_id, {"kind": event.kind, "payload": event.payload, "timestamp": datetime.now(UTC).isoformat()})

    @staticmethod
    def _is_explicit_completion(text: str) -> bool:
        normalized = (text or "").strip().lower()
        if not normalized:
            return False
        completion_tokens = (
            "completed",
            "completion",
            "done",
            "final",
            "result",
            "written",
            "verified",
            "task is complete",
            "task completed",
        )
        return any(token in normalized for token in completion_tokens)
