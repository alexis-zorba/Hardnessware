import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

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
  const [task, setTask] = useState("read README.md and summarize HARDNESS baseline");
  const [replyText, setReplyText] = useState("");
  const [maxTurns, setMaxTurns] = useState(8);

  const [sessionStatus, setSessionStatus] = useState("idle");
  const [waitingQuestion, setWaitingQuestion] = useState("");
  const [waitingOptions, setWaitingOptions] = useState([]);

  const [chatLog, setChatLog] = useState([]);
  const [events, setEvents] = useState([]);
  const [files, setFiles] = useState([]);
  const [filesPath, setFilesPath] = useState(".");
  const [diffPath, setDiffPath] = useState("README.md");
  const [diffText, setDiffText] = useState("");
  const [metrics, setMetrics] = useState({});
  const [finalText, setFinalText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const hasSession = Boolean(sessionId);

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    const timer = window.setInterval(() => {
      refreshSessionStatus();
    }, 1500);
    return () => window.clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    const source = new EventSource(`${API_BASE}/session/${sessionId}/events`);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((prev) => [...prev, payload].slice(-300));
        if (payload.kind === "clarification_requested") {
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
    source.onerror = () => {
      source.close();
    };
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

  async function refreshSessionStatus() {
    if (!sessionId) return;
    try {
      const data = await api(`/session/${sessionId}`);
      setSessionStatus(data.status ?? "idle");
      setWaitingQuestion(data.waiting_question ?? "");
      setWaitingOptions(Array.isArray(data.waiting_options) ? data.waiting_options : []);
    } catch {
      // keep existing UI state if status ping fails
    }
  }

  async function createSession() {
    setError("");
    setBusy(true);
    const payload = await api("/session", {
      method: "POST",
      body: JSON.stringify({ provider: "openrouter", model: "minimax/minimax-m2.7" }),
    });
    setSessionId(payload.session_id);
    setSessionStatus("idle");
    setChatLog([]);
    setEvents([]);
    setFiles([]);
    setDiffText("");
    setFinalText("");
    setMetrics({});
    setBusy(false);
  }

  async function runTask() {
    if (!hasSession || !task.trim()) return;
    setError("");
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
      const filePayload = await api(`/session/${sessionId}/files?path=${encodeURIComponent(filesPath)}&recursive=false`);
      setFiles(filePayload.files ?? []);
      setBusy(false);
    } catch (err) {
      setSessionStatus("error");
      setError(String(err));
      setBusy(false);
    }
  }

  async function sendReplyAndResume() {
    if (!hasSession || !replyText.trim()) return;
    setError("");
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
      setBusy(false);
    } catch (err) {
      setSessionStatus("error");
      setError(String(err));
      setBusy(false);
    }
  }

  async function continueTask() {
    if (!hasSession) return;
    setError("");
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
      const filePayload = await api(`/session/${sessionId}/files?path=${encodeURIComponent(filesPath)}&recursive=false`);
      setFiles(filePayload.files ?? []);
      setBusy(false);
    } catch (err) {
      setSessionStatus("error");
      setError(String(err));
      setBusy(false);
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

  async function loadFiles() {
    if (!hasSession) return;
    setError("");
    try {
      const filePayload = await api(`/session/${sessionId}/files?path=${encodeURIComponent(filesPath)}&recursive=false`);
      setFiles(filePayload.files ?? []);
    } catch (err) {
      setError(String(err));
    }
  }

  async function loadDiff() {
    if (!hasSession || !diffPath) return;
    setError("");
    try {
      const payload = await api(`/session/${sessionId}/diffs?path=${encodeURIComponent(diffPath)}`);
      setDiffText(payload.diff || payload.note || "");
    } catch (err) {
      setError(String(err));
    }
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
          <h1>HARDNESS Workbench</h1>
          <p className="subtitle">Interactive operator cockpit · inspired by multi-step workflow discipline</p>
        </div>
        <div className="header-controls">
          <button onClick={createSession}>Create Session</button>
          <button onClick={runTask} disabled={runDisabled}>
            Run
          </button>
          <button onClick={continueTask} disabled={continueDisabled}>
            Continue
          </button>
          <button onClick={interruptRun} disabled={stopDisabled}>
            Stop
          </button>
          <span className={statusClass}>{sessionStatus}</span>
          <span className="session-pill">{sessionId || "no-session"}</span>
        </div>
      </header>

      <main className="wb-main">
        <div className="left-column">
        <section className="card command-center">
          <h2>Command Center</h2>
          <label className="field-label">Task</label>
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Describe objective, constraints, acceptance checks"
            rows={6}
          />
          <div className="inline-actions">
            <button onClick={runTask} disabled={runDisabled}>
              Run Task
            </button>
            <button onClick={continueTask} disabled={continueDisabled}>
              Continue
            </button>
            <button onClick={interruptRun} disabled={stopDisabled}>
              Interrupt
            </button>
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

          <label className="field-label">Workspace path</label>
          <div className="inline-actions">
            <input value={filesPath} onChange={(e) => setFilesPath(e.target.value)} placeholder="." />
            <button onClick={loadFiles} disabled={!hasSession || busy}>
              Refresh Files
            </button>
          </div>

          <label className="field-label">Diff target</label>
          <div className="inline-actions">
            <input value={diffPath} onChange={(e) => setDiffPath(e.target.value)} placeholder="README.md" />
            <button onClick={loadDiff} disabled={!hasSession || busy}>
              Load Diff
            </button>
          </div>

          {sessionStatus === "paused" ? (
            <div className="waiting-box paused-box">
              <h3>Lavoro in pausa — turn limit raggiunto</h3>
              <p>Il task è parzialmente completato. Premi <strong>Continue</strong> per riprendere da dove si è fermato.</p>
              <div className="inline-actions">
                <button onClick={continueTask} disabled={continueDisabled}>
                  Continue
                </button>
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
                <button onClick={sendReplyAndResume} disabled={replyDisabled}>
                  Reply & Resume
                </button>
              </div>
            </div>
          ) : null}
        </section>

        <section className="card activity-stream">
          <h2>Activity Stream</h2>
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
              <h3>Files</h3>
              <ul>
                {files.map((file) => (
                  <li key={file.path}>{file.path}</li>
                ))}
              </ul>
              {!files.length && <p>No files loaded.</p>}
            </div>
            <div className="inspector-block">
              <h3>Diff</h3>
              <pre>{diffText || "No diff loaded."}</pre>
            </div>
          </div>
        </section>
      </main>

      {error ? <footer className="error-banner">{error}</footer> : null}
      {busy ? <div className="busy-indicator">Working...</div> : null}
    </div>
  );
}
