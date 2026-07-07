import { useState, useEffect, useRef } from "react";

export type AgentName = "Planner" | "Search" | "Validator" | "Extractor" | "Synthesizer";

export interface AgentState {
  name: AgentName;
  status: "waiting" | "running" | "done";
  message: string;
}

const AGENT_NAMES: AgentName[] = [
  "Planner",
  "Search",
  "Validator",
  "Extractor",
  "Synthesizer",
];

/** Back-end agent IDs to display names */
const AGENT_ID_MAP: Record<string, AgentName> = {
  planner:     "Planner",
  search:      "Search",
  validator:   "Validator",
  extractor:   "Extractor",
  synthesizer: "Synthesizer",
};

const initialAgents = (): AgentState[] =>
  AGENT_NAMES.map((name) => ({ name, status: "waiting", message: "" }));

export function useJobStream(jobId: string) {
  const [agents, setAgents]   = useState<AgentState[]>(initialAgents);
  const [report, setReport]   = useState<string | null>(null);
  const [error, setError]     = useState<string | null>(null);
  const [isDone, setIsDone]   = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  // Tracks whether we've already reached a terminal state (done or error).
  // Using a ref (not state) so the error handler always reads the latest
  // value, even inside a closure created on mount.
  const completedRef = useRef(false);

  useEffect(() => {
    // Reset state whenever jobId changes
    setAgents(initialAgents());
    setReport(null);
    setError(null);
    setIsDone(false);
    completedRef.current = false;

    // The SSE endpoint lives at /api/research/:id/stream.
    // Vite proxy forwards this to http://localhost:8000/api/research/:id/stream
    const BASE = import.meta.env.VITE_API_URL ?? '/api';
    const sse = new EventSource(`${BASE}/research/${jobId}/stream`);
    sseRef.current = sse;


    // NOTE: the backend (see app.py's `_sse` helper) sends every event as
    // a plain `data: {...}\n\n` frame with no `event:` field, so per the
    // SSE spec these ALL arrive as the generic 'message' event type.
    // The named listeners below (agent_start/agent_done/done) are kept
    // for forward-compatibility in case the backend adds named events
    // later, but today only the 'message' listener actually fires.
    sse.addEventListener("message", (e) => {
      try {
        const data = JSON.parse(e.data);
        handleEvent(data);
      } catch { /* ignore */ }
    });

    sse.addEventListener("agent_start", (e) => {
      try { handleEvent({ ...JSON.parse((e as MessageEvent).data), type: "agent_start" }); }
      catch { /* ignore */ }
    });

    sse.addEventListener("agent_done", (e) => {
      try { handleEvent({ ...JSON.parse((e as MessageEvent).data), type: "agent_done" }); }
      catch { /* ignore */ }
    });

    sse.addEventListener("done", (e) => {
      try { handleEvent({ ...JSON.parse((e as MessageEvent).data), type: "done" }); }
      catch { /* ignore */ }
    });

    sse.addEventListener("error", (e) => {
      // If we already reached a terminal state (done or error), this
      // 'error' event is just the browser reacting to the server closing
      // the connection normally after replaying/finishing events. That is
      // expected behavior, not a real failure -- ignore it.
      if (completedRef.current) {
        sse.close();
        return;
      }

      if (e instanceof MessageEvent) {
        try {
          const data = JSON.parse(e.data);
          if (data?.message) {
            handleEvent({ type: "error", message: data.message });
            return;
          }
        } catch { /* ignore */ }
      }
      // Genuine network-level error (connection dropped before completion)
      setError("Connection to server lost. Please refresh.");
      setIsDone(true);
      completedRef.current = true;
      sse.close();
    });

    return () => {
      sse.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  /** Central dispatch for all incoming SSE events */
  function handleEvent(data: Record<string, unknown>) {
    switch (data.type) {
      case "agent_start": {
        const agentName = AGENT_ID_MAP[String(data.agent ?? "").toLowerCase()];
        if (!agentName) break;
        setAgents((prev) =>
          prev.map((a) =>
            a.name === agentName
              ? { ...a, status: "running", message: String(data.message ?? "Processing…") }
              : a
          )
        );
        break;
      }

      case "agent_done": {
        const agentName = AGENT_ID_MAP[String(data.agent ?? "").toLowerCase()];
        if (!agentName) break;
        setAgents((prev) =>
          prev.map((a) =>
            a.name === agentName
              ? { ...a, status: "done", message: String(data.message ?? "Complete") }
              : a
          )
        );
        break;
      }

      case "done": {
        setReport(String(data.report ?? ""));
        // Mark all agents as done (catches any that didn't fire agent_done)
        setAgents((prev) => prev.map((a) => ({ ...a, status: "done" })));
        setIsDone(true);
        completedRef.current = true;
        sseRef.current?.close();
        break;
      }

      case "error": {
        setError(String(data.message ?? "An unknown error occurred."));
        setIsDone(true);
        completedRef.current = true;
        sseRef.current?.close();
        break;
      }

      default:
        break;
    }
  }

  return { agents, report, error, isDone };
}