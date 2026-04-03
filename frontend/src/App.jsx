import { useEffect, useMemo, useRef, useState, useCallback } from "react";

// Dev: default to localhost backend. Prod build: relative URL (same-origin, reverse-proxy friendly).
// Override either way with VITE_API_BASE in frontend/.env
const API_BASE = import.meta.env.VITE_API_BASE
  ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

function formatLiveEvent(event) {
  const p = event.payload ?? {};
  const t = p.turn != null ? `[T${p.turn}] ` : "";
  switch (event.kind) {
    case "run_started":
      return { label: "START", text: (p.task ?? "").slice(0, 120), cls: "ev-start" };
    case "provider_response":
      return {
        label: "LLM",
        text: `${t}${p.tool_calls ?? 0} call(s) · ${p.usage?.total_tokens ?? "?"}tok · ${p.finish_reason ?? ""}`,
        cls: "ev-llm",
      };
    case "tool_selected": {
      const args = Object.entries(p.arguments ?? {})
        .map(([k, v]) => `${k}=${JSON.stringify(v).slice(0, 60)}`)
        .join(", ");
      return { label: "CALL", text: `${t}${p.tool ?? "?"}(${args})`, cls: "ev-call" };
    }
    case "tool_executed": {
      const ok = p.success !== false;
      const preview = (p.content ?? "").slice(0, 120);
      return { label: ok ? "OK" : "ERR", text: `${t}${p.name ?? ""}: ${preview}`, cls: ok ? "ev-ok" : "ev-err" };
    }
    case "py_check_result":
      return {
        label: p.ok ? "PY✓" : "PY✗",
        text: `${t}${p.path ?? ""} ${p.ok ? "" : "— " + (p.detail ?? "").slice(0, 80)}`,
        cls: p.ok ? "ev-ok" : "ev-err",
      };
    case "write_verified":
      return { label: p.verified ? "WRITE✓" : "WRITE✗", text: `${t}${p.path ?? ""}`, cls: p.verified ? "ev-ok" : "ev-warn" };
    case "stop_decision":
      return { label: "STOP", text: `${t}${p.reason ?? ""} (${p.source ?? "loop"})`, cls: "ev-stop" };
    case "run_completed":
      return {
        label: "DONE",
        text: `${p.metrics?.turns ?? "?"}T · ${p.stop_reason ?? ""} · ${(p.final_text ?? "").slice(0, 80)}`,
        cls: "ev-done",
      };
    case "memory_retrieved":
      return { label: "MEM", text: `${t}${p.notes ?? 0} notes · ${p.session_messages ?? 0} msgs`, cls: "ev-meta" };
    case "routing_decision":
      return { label: "ROUTE", text: JSON.stringify(p).slice(0, 80), cls: "ev-meta" };
    case "verification_completed":
      return { label: "VERIFY", text: `${p.promoted_notes ?? 0} notes promoted`, cls: "ev-meta" };
    case "provider_error":
      return { label: "ERR", text: `${t}${p.error ?? ""}`, cls: "ev-err" };
    case "clarification_requested":
      return { label: "CLARIFY", text: p.question ?? "", cls: "ev-warn" };
    default:
      return { label: event.kind.toUpperCase().slice(0, 8), text: JSON.stringify(p).slice(0, 100), cls: "ev-meta" };
  }
}

async function api(path, init) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

export function App() {
  const [sessionId, setSessionId] = useState("");
  const [workspacePath, setWorkspacePath] = useState(".");
  const [task, setTask] = useState("read README.md and summarize Hardnessware baseline");
  const [replyText, setReplyText] = useState("");
  const [maxTurns, setMaxTurns] = useState(8);

  const [sessionStatus, setSessionStatus] = useState("idle");
  const [waitingQuestion, setWaitingQuestion] = useState("");
  const [waitingOptions, setWaitingOptions] = useState([]);

  const [chatLog, setChatLog] = useState([]);
  const [events, setEvents] = useState([]);
  const [files, setFiles] = useState([]);
  const [diffPath, setDiffPath] = useState("");
  const [diffText, setDiffText] = useState("");
  const [metrics, setMetrics] = useState({});
  const [finalText, setFinalText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Prevents SSE/polling from overriding status during an active run
  const activeRunRef = useRef(false);
  const loadInputRef = useRef(null);
  const liveScrollRef = useRef(null);

  const hasSession = Boolean(sessionId);

  useEffect(() => {
    if (!sessionId) return;
    const timer = window.setInterval(() => {
      refreshSessionStatus();
    }, 1500);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    const source = new EventSource(`${API_BASE}/session/${sessionId}/events`);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((prev) => [...prev, payload].slice(-300));
        if (payload.kind === "clarification_requested" && !activeRunRef.current) {
          const question = payload.payload?.question || "Agent requested clarification.";
          const options = Array.isArray(payload.payload?.options) ? payload.payload.options : [];
          setWaitingQuestion(question);
          setWaitingOptions(options);
          setSessionStatus("waiting_for_input");
        }
      } catch {
        // ignore malformed event
      }
    };
    source.onerror = () => source.close();
    return () => source.close();
  }, [sessionId]);

  const eventLines = useMemo(() => {
    return events.map((event) => {
      const kind = event.kind ?? "event";
      const ts = event.timestamp ?? "";
      const run = event.run_id ? ` (${event.run_id})` : "";
      return `${ts} | ${kind}${run}`;
    });
  }, [events]);

  // Live events: last 40 of the most recent run_id, newest first
  const liveEvents = useMemo(() => {
    if (!events.length) return [];
    const lastRunId = events[events.length - 1].run_id;
    const filtered = lastRunId
      ? events.filter((e) => e.run_id === lastRunId)
      : events;
    return filtered.slice(-40).reverse();
  }, [events]);

  async function refreshSessionStatus() {
    if (!sessionId || activeRunRef.current) return;
    try {
      const data = await api(`/session/${sessionId}`);
      if (!activeRunRef.current) {
        setSessionStatus(data.status ?? "idle");
        setWaitingQuestion(data.waiting_question ?? "");
        setWaitingOptions(Array.isArray(data.waiting_options) ? data.waiting_options : []);
      }
    } catch {
      // keep existing UI state if status ping fails
    }
  }

  function refreshFilesAsync(sid) {
    const target = sid ?? sessionId;
    if (!target) return;
    api(`/session/${target}/files?path=.&recursive=false`)
      .then((fp) => setFiles(fp.files ?? []))
      .catch(() => {});
  }

  async function createSession() {
    setError("");
    setBusy(true);
    try {
      const payload = await api("/session", {
        method: "POST",
        body: JSON.stringify({
          provider: "openrouter",
          model: "minimax/minimax-m2.7",
          workspace: workspacePath.trim() || ".",
        }),
      });
      setSessionId(payload.session_id);
      setSessionStatus("idle");
      setChatLog([]);
      setEvents([]);
      setFiles([]);
      setDiffText("");
      setDiffPath("");
      setFinalText("");
      setMetrics({});
      refreshFilesAsync(payload.session_id);
    } catch (err) {
      setError(String(err));
    }
    setBusy(false);
  }

  async function runTask() {
    if (!hasSession || !task.trim()) return;
    setError("");
    activeRunRef.current = true;
    setBusy(true);
    setSessionStatus("running");
    try {
      setChatLog((prev) => [...prev, { role: "user", text: task.trim(), kind: "task" }]);
      const result = await api(`/session/${sessionId}/run`, {
        method: "POST",
        body: JSON.stringify({ task: task.trim(), max_turns: maxTurns }),
      });
      setFinalText(result.final_text ?? "");
      setMetrics(result.metrics ?? {});
      const nextStatus = result.session_status ?? "completed";
      setSessionStatus(nextStatus);
      setWaitingQuestion(result.waiting_question ?? "");
      setWaitingOptions(Array.isArray(result.waiting_options) ? result.waiting_options : []);
      setChatLog((prev) => [...prev, { role: "assistant", text: result.final_text ?? "", kind: nextStatus }]);
    } catch (err) {
      setSessionStatus("error");
      setError(String(err));
    } finally {
      activeRunRef.current = false;
      setBusy(false);
      refreshFilesAsync();
    }
  }

  async function sendReplyAndResume() {
    if (!hasSession || !replyText.trim()) return;
    setError("");
    activeRunRef.current = true;
    setBusy(true);
    try {
      setChatLog((prev) => [...prev, { role: "user", text: replyText.trim(), kind: "reply" }]);
      await api(`/session/${sessionId}/reply`, {
        method: "POST",
        body: JSON.stringify({ content: replyText.trim() }),
      });
      setSessionStatus("running");
      const resumed = await api(`/session/${sessionId}/resume`, { method: "POST" });
      setFinalText(resumed.final_text ?? "");
      setMetrics(resumed.metrics ?? {});
      const nextStatus = resumed.session_status ?? "completed";
      setSessionStatus(nextStatus);
      setWaitingQuestion(resumed.waiting_question ?? "");
      setWaitingOptions(Array.isArray(resumed.waiting_options) ? resumed.waiting_options : []);
      setChatLog((prev) => [...prev, { role: "assistant", text: resumed.final_text ?? "", kind: nextStatus }]);
      setReplyText("");
    } catch (err) {
      setSessionStatus("error");
      setError(String(err));
    } finally {
      activeRunRef.current = false;
      setBusy(false);
      refreshFilesAsync();
    }
  }

  async function continueTask() {
    if (!hasSession) return;
    setError("");
    activeRunRef.current = true;
    setBusy(true);
    setSessionStatus("running");
    try {
      const result = await api(`/session/${sessionId}/continue`, {
        method: "POST",
        body: JSON.stringify({ max_turns: maxTurns }),
      });
      setFinalText(result.final_text ?? "");
      setMetrics(result.metrics ?? {});
      const nextStatus = result.session_status ?? "completed";
      setSessionStatus(nextStatus);
      setWaitingQuestion(result.waiting_question ?? "");
      setWaitingOptions(Array.isArray(result.waiting_options) ? result.waiting_options : []);
      setChatLog((prev) => [...prev, { role: "assistant", text: result.final_text ?? "", kind: nextStatus }]);
    } catch (err) {
      setSessionStatus("error");
      setError(String(err));
    } finally {
      activeRunRef.current = false;
      setBusy(false);
      refreshFilesAsync();
    }
  }

  async function interruptRun() {
    if (!hasSession || sessionStatus !== "running") return;
    setError("");
    try {
      await api(`/session/${sessionId}/interrupt`, { method: "POST" });
      setSessionStatus("interrupt_requested");
    } catch (err) {
      setError(String(err));
    }
  }

  async function refreshFiles() {
    if (!hasSession) return;
    setError("");
    try {
      const fp = await api(`/session/${sessionId}/files?path=.&recursive=false`);
      setFiles(fp.files ?? []);
    } catch (err) {
      setError(String(err));
    }
  }

  async function loadDiff(path) {
    if (!hasSession || !path) return;
    setError("");
    setDiffPath(path);
    try {
      const payload = await api(`/session/${sessionId}/diffs?path=${encodeURIComponent(path)}`);
      setDiffText(payload.diff || payload.note || "");
    } catch (err) {
      setError(String(err));
    }
  }

  async function saveSession() {
    if (!hasSession) return;
    setError("");
    try {
      const data = await api(`/session/${sessionId}/export`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hardnessware-${sessionId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(String(err));
    }
  }

  async function loadSession(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      const parsed = JSON.parse(await file.text());
      const payload = await api("/session/import", {
        method: "POST",
        body: JSON.stringify({ data: parsed }),
      });
      setSessionId(payload.session_id);
      setWorkspacePath(parsed.workspace ?? ".");
      setSessionStatus(payload.status ?? "idle");
      setEvents([]);
      setDiffText("");
      setDiffPath("");
      // Restore output and metrics from export
      setFinalText(parsed.final_text ?? "");
      setMetrics(parsed.metrics ?? {});
      // Restore conversation log
      const msgs = Array.isArray(parsed.messages) ? parsed.messages : [];
      setChatLog(
        msgs
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role, text: m.content ?? "", kind: "restored" }))
      );
      // Restore waiting state if applicable
      if (payload.status === "waiting_for_input") {
        setWaitingQuestion(parsed.waiting_question ?? "");
        setWaitingOptions(Array.isArray(parsed.waiting_options) ? parsed.waiting_options : []);
      } else {
        setWaitingQuestion("");
        setWaitingOptions([]);
      }
      // Pre-fill task with pending task (paused or waiting)
      if (parsed.pending_task) {
        setTask(parsed.pending_task);
      }
      refreshFilesAsync(payload.session_id);
    } catch (err) {
      setError(String(err));
    }
    setBusy(false);
    // Reset so same file can be re-loaded
    e.target.value = "";
  }

  const statusClass = `status-pill status-${sessionStatus}`;

  const runDisabled = !hasSession || busy || sessionStatus === "running";
  const replyDisabled = !hasSession || busy || !replyText.trim();
  const stopDisabled = !hasSession || busy || sessionStatus !== "running";
  const continueDisabled = !hasSession || busy || sessionStatus !== "paused";

  return (
    <div className="wb-app">
      <header className="wb-header">
        <div>
          <h1>Hardnessware Cockpit</h1>
          <p className="subtitle">Provider-agnostic agent harness ecosystem</p>
        </div>
        <div className="header-controls">
          <button onClick={createSession} disabled={busy}>New Session</button>
          <button onClick={runTask} disabled={runDisabled}>Run</button>
          <button onClick={continueTask} disabled={continueDisabled}>Continue</button>
          <button onClick={interruptRun} disabled={stopDisabled}>Stop</button>
          <button onClick={saveSession} disabled={!hasSession || busy} title="Download session to file">Save</button>
          <label className="btn-load" title="Restore session from file">
            Load
            <input
              ref={loadInputRef}
              type="file"
              accept=".json"
              onChange={loadSession}
              style={{ display: "none" }}
            />
          </label>
          <span className={statusClass}>{sessionStatus}</span>
          <span className="session-pill">{sessionId || "no-session"}</span>
        </div>
      </header>

      <main className="wb-main">
        <div className="left-column">
          <section className="card command-center">
            <h2>Command Center</h2>

            <label className="field-label">Agent workspace</label>
            {hasSession ? (
              <div className="workspace-locked">{workspacePath}</div>
            ) : (
              <div className="inline-actions">
                <input
                  value={workspacePath}
                  onChange={(e) => setWorkspacePath(e.target.value)}
                  placeholder="."
                />
              </div>
            )}

            <label className="field-label">Task</label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe objective, constraints, acceptance checks"
              rows={6}
            />
            <div className="inline-actions">
              <button onClick={runTask} disabled={runDisabled}>Run Task</button>
              <button onClick={continueTask} disabled={continueDisabled}>Continue</button>
              <button onClick={interruptRun} disabled={stopDisabled}>Interrupt</button>
            </div>

            <label className="field-label">Max turns</label>
            <div className="inline-actions">
              <input
                type="number"
                min={1}
                max={50}
                value={maxTurns}
                onChange={(e) => setMaxTurns(Math.max(1, Math.min(50, Number(e.target.value))))}
                style={{ width: "72px" }}
              />
            </div>

            {sessionStatus === "paused" ? (
              <div className="waiting-box paused-box">
                <h3>Lavoro in pausa — turn limit raggiunto</h3>
                <p>Il task è parzialmente completato. Premi <strong>Continue</strong> per riprendere da dove si è fermato.</p>
                <div className="inline-actions">
                  <button onClick={continueTask} disabled={continueDisabled}>Continue</button>
                </div>
              </div>
            ) : null}

            {sessionStatus === "waiting_for_input" ? (
              <div className="waiting-box">
                <h3>Waiting for input</h3>
                <p>{waitingQuestion || "Agent requested additional clarification."}</p>
                {waitingOptions.length ? (
                  <ul>
                    {waitingOptions.map((opt) => (
                      <li key={opt}>{opt}</li>
                    ))}
                  </ul>
                ) : null}
                <div className="inline-actions">
                  <input
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="Your reply"
                  />
                  <button onClick={sendReplyAndResume} disabled={replyDisabled}>Reply & Resume</button>
                </div>
              </div>
            ) : null}
          </section>

          <section className="card live-stream">
            <div className="live-header">
              <h2>Live Stream</h2>
              {sessionStatus === "running" && <span className="live-dot" />}
            </div>
            <div className="live-events">
              {liveEvents.length ? (
                liveEvents.map((event, idx) => {
                  const { label, text, cls } = formatLiveEvent(event);
                  return (
                    <div key={idx} className={`live-event ${cls}`}>
                      <span className="live-label">{label}</span>
                      <span className="live-text">{text}</span>
                    </div>
                  );
                })
              ) : (
                <span className="live-idle">Waiting for events…</span>
              )}
            </div>
          </section>

          <section className="card activity-log">
            <h2>Activity Log</h2>
            <pre>{eventLines.join("\n") || "No events yet."}</pre>
          </section>
        </div>

        <section className="card right-column">
          <div className="subcard chat-log">
            <h2>Conversation</h2>
            <div className="chat-items">
              {chatLog.length ? (
                chatLog.map((entry, idx) => (
                  <div key={`${idx}-${entry.kind}`} className={`chat-item role-${entry.role}`}>
                    <div className="chat-meta">
                      <span>{entry.role}</span>
                      <span>{entry.kind}</span>
                    </div>
                    <pre>{entry.text || "(empty)"}</pre>
                  </div>
                ))
              ) : (
                <p>No conversation yet.</p>
              )}
            </div>
          </div>

          <div className="subcard inspector">
            <h2>Inspector</h2>
            <div className="inspector-block">
              <h3>Latest final output</h3>
              <pre>{finalText || "No final output yet."}</pre>
            </div>
            <div className="inspector-block">
              <h3>Metrics</h3>
              <pre>{JSON.stringify(metrics, null, 2)}</pre>
            </div>
            <div className="inspector-block">
              <div className="inspector-block-header">
                <h3>Files</h3>
                <button className="btn-small" onClick={refreshFiles} disabled={!hasSession || busy}>Refresh</button>
              </div>
              <ul className="file-list">
                {files.map((file) => (
                  <li key={file.path}>
                    {file.is_dir ? (
                      <span className="file-dir">{file.path}/</span>
                    ) : (
                      <button
                        className="file-link"
                        onClick={() => loadDiff(file.path)}
                        title="Click to view diff"
                      >
                        {file.path}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              {!files.length && <p>No files loaded.</p>}
            </div>
            <div className="inspector-block">
              <h3>Diff{diffPath ? ` — ${diffPath}` : ""}</h3>
              <pre>{diffText || (diffPath ? "No changes since baseline." : "Click a file above to load its diff.")}</pre>
            </div>
          </div>
        </section>
      </main>

      {error ? <footer className="error-banner">{error}</footer> : null}
      {busy ? <div className="busy-indicator">Working...</div> : null}
    </div>
  );
}
