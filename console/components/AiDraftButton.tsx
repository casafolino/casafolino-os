"use client";
// Bottone "Bozza AI" — chiama /api/ai-draft (Groq server-side) e mostra la bozza.
import { useState } from "react";
import { Icon } from "./Icons";

export function AiDraftButton({ subject, body, partnerName }: { subject: string; body: string; partnerName?: string }) {
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setLoading(true); setErr(null);
    try {
      const res = await fetch("/api/ai-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, body, partnerName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "errore");
      setDraft(data.draft);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <span className="btn" onClick={run} style={{ opacity: loading ? 0.6 : 1 }}>
        <Icon name="ai" size={14} /> {loading ? "Genero…" : "Bozza AI"}
      </span>
      {draft != null ? (
        <div style={{ flexBasis: "100%", marginTop: 8 }}>
          <textarea defaultValue={draft} rows={8} style={{
            width: "100%", fontFamily: "var(--font)", fontSize: 13, padding: 10,
            border: "1px solid var(--line-2)", borderRadius: "var(--r-md)", background: "var(--paper)", color: "var(--ink)",
          }} />
        </div>
      ) : null}
      {err ? <div style={{ flexBasis: "100%", color: "var(--danger)", fontSize: 12, marginTop: 4 }}>Bozza non riuscita: {err}</div> : null}
    </>
  );
}
