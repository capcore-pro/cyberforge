import { useMemo, useRef, useState } from "react";
import type { CustomAgentUpsert } from "@/lib/custom-agents-api";
import { streamCustomAgentChat, type CustomAgentChatDone } from "@/lib/custom-agents-api";

type ChatMsg = { role: "user" | "assistant"; content: string };

export function Step3Test({
  agentId,
  value,
  disabled,
}: {
  agentId: string | null;
  value: CustomAgentUpsert;
  disabled: boolean;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastStats, setLastStats] = useState<CustomAgentChatDone | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const canTest = Boolean(agentId) && value.system_prompt.trim().length >= 10;

  const history = useMemo(
    () => messages.map((m) => ({ role: m.role, content: m.content })),
    [messages],
  );

  async function send() {
    if (!agentId) {
      setError("Sauvegardez l’agent avant de tester (identifiant manquant).");
      return;
    }
    const msg = input.trim();
    if (!msg) return;

    setInput("");
    setError(null);
    setLastStats(null);
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;

    setMessages((prev) => [...prev, { role: "user", content: msg }, { role: "assistant", content: "" }]);

    await streamCustomAgentChat(
      agentId,
      msg,
      history,
      {
        onChunk: (delta) => {
          setMessages((prev) => {
            const next = prev.slice();
            const last = next[next.length - 1];
            if (last && last.role === "assistant") {
              next[next.length - 1] = { ...last, content: last.content + delta };
            }
            return next;
          });
        },
        onDone: (payload) => {
          setLastStats(payload);
        },
        onError: (message) => setError(message),
      },
      controller.signal,
    );

    setBusy(false);
  }

  return (
    <section className="space-y-3">
      <p className="text-sm text-cf-muted">
        Testez l’agent en conditions réelles (réponse streamée).
      </p>

      {!canTest ? (
        <p className="rounded-card border border-orange-500/30 bg-orange-950/20 px-4 py-3 text-sm text-orange-200">
          Sauvegardez l’agent et renseignez un system prompt pour activer le test.
        </p>
      ) : null}

      <div className="rounded-card border border-white/10 bg-black/30 p-4">
        <div className="h-64 overflow-y-auto space-y-3 pr-1">
          {messages.length === 0 ? (
            <p className="text-sm text-cf-muted">Aucun message. Envoyez un test.</p>
          ) : null}
          {messages.map((m, idx) => (
            <div key={idx} className={m.role === "user" ? "text-right" : "text-left"}>
              <div
                className={[
                  "inline-block max-w-[85%] rounded-card border px-3 py-2 text-sm",
                  m.role === "user"
                    ? "border-cf-gold/30 bg-cf-gold/10 text-cf-text"
                    : "border-white/10 bg-white/5 text-cf-text",
                ].join(" ")}
              >
                <pre className="whitespace-pre-wrap font-sans">{m.content}</pre>
              </div>
            </div>
          ))}
        </div>

        {lastStats ? (
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-cf-muted">
            <span>
              Tokens:{" "}
              <strong className="text-cf-text">{lastStats.total_tokens}</strong>
            </span>
            <span>
              Coût estimé:{" "}
              <strong className="text-cf-text">{lastStats.cost_usd} $</strong>
            </span>
            <span>
              Modèle:{" "}
              <strong className="text-cf-text">
                {lastStats.provider}/{lastStats.model}
              </strong>
            </span>
          </div>
        ) : null}

        {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}

        <div className="mt-4 flex gap-2">
          <input
            value={input}
            disabled={disabled || busy || !canTest}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            placeholder="Écrivez un message de test…"
            className="flex-1 rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
          />
          <button
            type="button"
            disabled={disabled || busy || !canTest}
            onClick={() => void send()}
            className="rounded-control border border-cf-gold/40 bg-cf-gold/20 px-4 py-2 text-sm font-semibold text-cf-gold hover:bg-cf-gold/25 disabled:opacity-60"
          >
            Envoyer
          </button>
        </div>
      </div>
    </section>
  );
}

