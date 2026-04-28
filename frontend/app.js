const API = "http://localhost:8000";
const $ = (id) => document.getElementById(id);

let sessionId = localStorage.getItem("felo_session") || crypto.randomUUID();
localStorage.setItem("felo_session", sessionId);
const userId = localStorage.getItem("felo_user") || "demo-user";
localStorage.setItem("felo_user", userId);

async function loadModels() {
  const r = await fetch(`${API}/api/models`);
  const data = await r.json();
  const providers = [...new Set(data.models.map((m) => m.provider))];
  $("provider").innerHTML = providers.map((p) => `<option>${p}</option>`).join("");
  const refresh = () => {
    const p = $("provider").value;
    $("model").innerHTML = data.models
      .filter((m) => m.provider === p)
      .map((m) => `<option>${m.model}</option>`)
      .join("");
  };
  $("provider").addEventListener("change", refresh);
  refresh();
}

async function loadQuota() {
  try {
    const r = await fetch(`${API}/api/quota/${userId}`);
    const q = await r.json();
    $("quotaText").textContent = `${q.used} / ${q.limit} calls`;
    $("quotaFill").style.width = `${(q.used / q.limit) * 100}%`;
  } catch {}
}

function addMessage(role, text, opts = {}) {
  const div = document.createElement("div");
  div.className = `msg ${role}` + (opts.refusal ? " refusal" : "");
  div.innerHTML = role === "ai" ? marked.parse(text) : text;
  if (opts.sources?.length) {
    const s = document.createElement("details");
    s.className = "sources";
    s.innerHTML = `<summary>Sources (${opts.sources.length})</summary>` +
      opts.sources.map((x) => `<div>${x.label}: ${x.value}</div>`).join("");
    div.appendChild(s);
  }
  $("messages").appendChild(div);
  $("messages").scrollTop = $("messages").scrollHeight;
  return div;
}

function typingBubble() {
  const div = document.createElement("div");
  div.className = "msg ai typing";
  div.innerHTML = "<span></span><span></span><span></span>";
  $("messages").appendChild(div);
  $("messages").scrollTop = $("messages").scrollHeight;
  return div;
}

async function send() {
  const text = $("input").value.trim();
  if (!text) return;
  addMessage("user", text);
  $("input").value = "";
  const t = typingBubble();
  try {
    const r = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        message: text, session_id: sessionId, user_id: userId,
        provider: $("provider").value, model: $("model").value,
      }),
    });
    t.remove();
    if (r.status === 429) {
      addMessage("ai", "**Quota exceeded.** Upgrade your tier or wait until next month.", { refusal: true });
      return;
    }
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      addMessage("ai", `Error: ${err.detail?.message || r.statusText}`, { refusal: true });
      return;
    }
    const data = await r.json();
    addMessage("ai", data.answer, { sources: data.sources, refusal: data.guardrail_triggered });
    loadQuota();
  } catch (e) {
    t.remove();
    addMessage("ai", "Network error.", { refusal: true });
  }
}

$("send").addEventListener("click", send);
$("input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("clear").addEventListener("click", async () => {
  await fetch(`${API}/api/chat/${sessionId}?user_id=${encodeURIComponent(userId)}`, { method: "DELETE" });
  $("messages").innerHTML = "";
});

loadModels();
loadQuota();
