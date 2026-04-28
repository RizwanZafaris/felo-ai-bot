import { useCallback, useState } from "react";
import { sendChat, type CoachResponse } from "../api/coach";

export type Msg = {
  role: "user" | "ai";
  text: string;
  sources?: { label: string; value: string }[];
  refusal?: boolean;
};

export function useChat(sessionId: string | null, userId: string, provider: string, model: string) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (text: string) => {
      if (!sessionId) return;
      setMessages((m) => [...m, { role: "user", text }]);
      setLoading(true);
      setError(null);
      try {
        const r: CoachResponse = await sendChat({
          message: text, session_id: sessionId, user_id: userId, provider, model,
        });
        setMessages((m) => [...m, {
          role: "ai", text: r.answer, sources: r.sources, refusal: r.guardrail_triggered,
        }]);
      } catch (e: any) {
        const msg = e?.status === 429 ? "Quota exceeded." : "Network error.";
        setError(msg);
        setMessages((m) => [...m, { role: "ai", text: msg, refusal: true }]);
      } finally {
        setLoading(false);
      }
    },
    [sessionId, userId, provider, model],
  );

  const clear = () => setMessages([]);
  return { messages, send, loading, error, clear };
}
