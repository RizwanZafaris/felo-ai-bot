const API = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

export type Source = { type: string; label: string; value: string };

export type CoachResponse = {
  answer: string;
  session_id: string;
  sources: Source[];
  guardrail_triggered: boolean;
  refusal_category: string | null;
  tokens_used: number;
  cost_usd: number;
  quota_remaining: number;
};

export async function sendChat(body: {
  message: string; session_id: string; user_id: string;
  provider: string; model: string;
}): Promise<CoachResponse> {
  const r = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw Object.assign(new Error("chat_failed"), { status: r.status, body: await r.json().catch(() => ({})) });
  return r.json();
}

export async function getQuota(userId: string) {
  const r = await fetch(`${API}/api/quota/${userId}`);
  return r.json();
}

export async function getModels() {
  const r = await fetch(`${API}/api/models`);
  return r.json();
}

export async function clearSession(sessionId: string) {
  await fetch(`${API}/api/chat/${sessionId}`, { method: "DELETE" });
}
