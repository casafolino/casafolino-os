"use client";
// Composer completo — Rispondi / Inoltra / Nuova mail via gateway (console_reply / console_send).
// Rich-text (HTML), firma per-casella, allegati (SOLO upload nuovi → anti-exfiltration lato gateway).
// Kill-switch False → bozza; True → invio reale (cap/dedup/audit nel gateway). operator_uid da sessione.
import { useEffect, useRef, useState } from "react";
import { BP } from "@/lib/basePath";
import type { LibraryItem, MailTemplate } from "@/lib/bundle";

export type ComposerTarget = { id: number; subject: string; senderEmail: string; senderName: string; accountId?: number | null };
export type ComposerMode = "reply" | "forward" | "new";
export type Account = { id: number; name: string; email: string; signature: string };
type Attach = { filename: string; content: string; mimetype: string; size: number };

// CC suggeriti SEMPRE (chip rimovibili, non forzati). Pattern firstname.lastname@.
const SUGGESTED_CC = ["martina.sinopoli@casafolino.com", "maria.mirabelli@casafolino.com"];

function readFileB64(file: File): Promise<Attach> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => {
      const s = String(r.result || "");
      const b64 = s.includes(",") ? s.slice(s.indexOf(",") + 1) : s; // strip data:...;base64,
      resolve({ filename: file.name, content: b64, mimetype: file.type || "application/octet-stream", size: file.size });
    };
    r.onerror = () => reject(new Error("lettura file fallita"));
    r.readAsDataURL(file);
  });
}

export function Composer({ mode, target, accounts = [], library = [], templates = [], onClose }: {
  mode: ComposerMode;
  target: ComposerTarget;
  accounts?: Account[];
  library?: LibraryItem[];
  templates?: MailTemplate[];
  onClose: () => void;
}) {
  const cleanSubj = (target.subject || "").replace(/^(re|fwd|fw):\s*/i, "");
  const [to, setTo] = useState(mode === "reply" ? target.senderEmail : "");
  const [subject, setSubject] = useState(mode === "reply" ? "Re: " + cleanSubj : mode === "forward" ? "Fwd: " + cleanSubj : "");
  const [accountId, setAccountId] = useState<number>(mode === "new" ? (accounts[0]?.id ?? 0) : (target.accountId ?? accounts[0]?.id ?? 0));
  const [atts, setAtts] = useState<Attach[]>([]);
  const [cc, setCc] = useState<string[]>(SUGGESTED_CC);   // suggeriti SEMPRE, rimovibili
  const [bcc, setBcc] = useState<string[]>([]);
  const [ccInput, setCcInput] = useState("");
  const [materialIds, setMaterialIds] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  const account = accounts.find((a) => a.id === accountId);
  const title = mode === "reply" ? "Rispondi · R" : mode === "forward" ? "Inoltra" : "Nuova mail";

  useEffect(() => { if (editorRef.current && !editorRef.current.innerHTML) editorRef.current.innerHTML = "<p><br/></p>"; }, []);

  function cmd(c: string, val?: string) { editorRef.current?.focus(); document.execCommand(c, false, val); }
  function insertLink() { const u = prompt("URL:"); if (u) cmd("createLink", u); }
  function insertSig() {
    const el = editorRef.current; if (!el || !account?.signature) return;
    if (el.querySelector("[data-signature]")) return; // già inserita
    el.insertAdjacentHTML("beforeend", `<div data-signature>${account.signature}</div>`);
  }
  function removeSig() { editorRef.current?.querySelector("[data-signature]")?.remove(); }

  async function onFiles(list: FileList | null) {
    if (!list) return;
    try { const next = await Promise.all(Array.from(list).map(readFileB64)); setAtts((a) => [...a, ...next].slice(0, 10)); }
    catch { setMsg("✕ allegato non leggibile"); }
  }
  function applyTemplate(id: number) {
    const t = templates.find((x) => x.id === id); if (!t) return;
    setSubject(t.subject);
    if (editorRef.current) editorRef.current.innerHTML = t.bodyHtml || "<p><br/></p>";
  }
  function addCc(raw: string) {
    const v = raw.trim().toLowerCase();
    if (v && v.includes("@") && !cc.includes(v)) setCc([...cc, v]);
    setCcInput("");
  }
  const libById = (id: number) => library.find((l) => l.id === id);

  async function submit() {
    setBusy(true); setMsg(null);
    const body = editorRef.current?.innerHTML ?? "";
    const url = mode === "reply" ? `${BP}/api/console/reply` : `${BP}/api/console/send`;
    const base = mode === "reply" ? { messageId: target.id, body, subject }
      : mode === "forward" ? { to, subject, body, sourceMessageId: target.id }
        : { to, subject, body, accountId };
    const payload = {
      ...base,
      attachments: atts.map(({ filename, content, mimetype }) => ({ filename, content, mimetype })),
      materialIds, cc, bcc,
    };
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const j = await res.json().catch(() => ({ ok: false, message: "errore rete" }));
    setBusy(false);
    if (j.ok || j.draft_id) {
      const st = j.state === "draft" ? "bozza creata (invio reale disattivo)" : j.state === "sent" ? "inviata" : "ok";
      setMsg(`✓ ${st}${j.attachments ? ` · ${j.attachments} allegati` : ""}`);
      setTimeout(onClose, 1300);
    } else { setMsg(`✕ ${j.message || j.blocked || "non riuscito"}`); }
  }

  const bodyText = () => (editorRef.current?.innerText || "").trim();
  const canSend = !busy && to.trim() && (mode !== "new" || accountId > 0);

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "grid", placeItems: "center", zIndex: 70 }} onClick={onClose}>
      <div className="card" style={{ padding: 18, width: 600, maxWidth: "94vw", display: "flex", flexDirection: "column", gap: 9 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontWeight: 600 }}>{title}</div>
        {mode === "new" ? (
          <label style={{ fontSize: 12 }}>Da (casella)
            <select value={accountId} onChange={(e) => setAccountId(Number(e.target.value))} style={inp}>
              {accounts.length === 0 ? <option value={0}>nessuna casella</option> : null}
              {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} · {a.email}</option>)}
            </select>
          </label>
        ) : null}
        <label style={{ fontSize: 12 }}>A
          <input value={to} onChange={(e) => setTo(e.target.value)} readOnly={mode === "reply"} placeholder={mode === "new" ? "destinatario@…" : undefined} style={{ ...inp, background: mode === "reply" ? "var(--panel-2)" : "#fff" }} />
        </label>
        {/* CC / BCC — Martina+Maria suggeriti SEMPRE (chip rimovibili) */}
        <div style={{ fontSize: 12, display: "flex", flexDirection: "column", gap: 4 }}>
          <div className="row" style={{ gap: 4, flexWrap: "wrap", alignItems: "center" }}>
            <span className="muted">CC:</span>
            {cc.map((e) => <span key={e} className="chip" style={{ background: "var(--panel-2)" }}>{e}<button type="button" onClick={() => setCc(cc.filter((x) => x !== e))} style={chipX}>✕</button></span>)}
            <input value={ccInput} onChange={(e) => setCcInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addCc(ccInput); } }} placeholder="aggiungi CC + Invio" style={{ ...inp, width: 160, marginTop: 0, padding: "3px 7px" }} />
            {SUGGESTED_CC.filter((s) => !cc.includes(s)).map((s) => <button key={s} type="button" className="btn" style={tb} onClick={() => setCc([...cc, s])}>+ {s.split("@")[0]}</button>)}
          </div>
          <div className="row" style={{ gap: 4, flexWrap: "wrap", alignItems: "center" }}>
            <span className="muted">BCC:</span>
            {bcc.map((e) => <span key={e} className="chip" style={{ background: "var(--panel-2)" }}>{e}<button type="button" onClick={() => setBcc(bcc.filter((x) => x !== e))} style={chipX}>✕</button></span>)}
            <input onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); const v = (e.target as HTMLInputElement).value.trim().toLowerCase(); if (v.includes("@") && !bcc.includes(v)) setBcc([...bcc, v]); (e.target as HTMLInputElement).value = ""; } }} placeholder="aggiungi BCC + Invio" style={{ ...inp, width: 160, marginTop: 0, padding: "3px 7px" }} />
          </div>
        </div>
        <div className="row" style={{ gap: 6, alignItems: "center" }}>
          <label style={{ fontSize: 12, flex: 1 }}>Oggetto
            <input value={subject} onChange={(e) => setSubject(e.target.value)} style={inp} />
          </label>
          {templates.length ? (
            <label style={{ fontSize: 11, marginTop: 14 }}>
              <select defaultValue="" onChange={(e) => { applyTemplate(Number(e.target.value)); e.target.value = ""; }} style={{ ...inp, marginTop: 0, padding: "6px 8px" }}>
                <option value="">Template…</option>
                {templates.map((t) => <option key={t.id} value={t.id}>{t.language.toUpperCase()} · {t.name}</option>)}
              </select>
            </label>
          ) : null}
        </div>
        {/* toolbar rich-text */}
        <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
          <button type="button" className="btn" style={tb} onMouseDown={(e) => { e.preventDefault(); cmd("bold"); }}><b>B</b></button>
          <button type="button" className="btn" style={tb} onMouseDown={(e) => { e.preventDefault(); cmd("italic"); }}><i>I</i></button>
          <button type="button" className="btn" style={tb} onMouseDown={(e) => { e.preventDefault(); cmd("insertUnorderedList"); }}>• Lista</button>
          <button type="button" className="btn" style={tb} onMouseDown={(e) => { e.preventDefault(); insertLink(); }}>🔗 Link</button>
          {account?.signature ? <>
            <button type="button" className="btn" style={tb} onMouseDown={(e) => { e.preventDefault(); insertSig(); }}>+ Firma</button>
            <button type="button" className="btn" style={tb} onMouseDown={(e) => { e.preventDefault(); removeSig(); }}>− Firma</button>
          </> : null}
        </div>
        <div ref={editorRef} contentEditable suppressContentEditableWarning
          style={{ minHeight: 160, maxHeight: 320, overflowY: "auto", padding: "8px 10px", border: "1px solid var(--line)", borderRadius: 7, fontSize: 13, lineHeight: 1.5 }} />
        {/* allegati: upload nuovi + libreria invii curata */}
        <div className="row" style={{ gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <label className="btn" style={{ ...tb, cursor: "pointer" }}>📎 Allega
            <input type="file" multiple onChange={(e) => onFiles(e.target.files)} style={{ display: "none" }} />
          </label>
          {library.length ? (
            <select defaultValue="" onChange={(e) => { const id = Number(e.target.value); if (id && !materialIds.includes(id)) setMaterialIds([...materialIds, id]); e.target.value = ""; }} style={{ ...inp, marginTop: 0, padding: "4px 7px", width: "auto", fontSize: 12 }}>
              <option value="">📚 Da libreria…</option>
              {library.map((l) => <option key={l.id} value={l.id}>{l.category} · {l.name}</option>)}
            </select>
          ) : null}
          {atts.map((a, i) => (
            <span key={`u${i}`} className="chip" style={{ background: "var(--panel-2)" }}>
              {a.filename} ({Math.ceil(a.size / 1024)}kb)
              <button type="button" onClick={() => setAtts((s) => s.filter((_, j) => j !== i))} style={chipX}>✕</button>
            </span>
          ))}
          {materialIds.map((id) => (
            <span key={`m${id}`} className="chip" style={{ background: "var(--accent-t)", color: "var(--accent)" }}>
              📚 {libById(id)?.name ?? id}
              <button type="button" onClick={() => setMaterialIds(materialIds.filter((x) => x !== id))} style={chipX}>✕</button>
            </span>
          ))}
        </div>
        {msg ? <div style={{ fontSize: 13, color: msg.startsWith("✓") ? "var(--ok)" : "var(--danger)" }}>{msg}</div> : null}
        <div className="row" style={{ gap: 8, justifyContent: "space-between", alignItems: "center" }}>
          <span className="muted" style={{ fontSize: 11 }}>Invio reale disattivo (kill-switch) → salva bozza.</span>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn" onClick={onClose}>Annulla</button>
            <button className="btn pri" disabled={!canSend} onClick={submit}>{busy ? "…" : "Invia"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

const inp: React.CSSProperties = { width: "100%", marginTop: 3, padding: "8px 10px", border: "1px solid var(--line)", borderRadius: 7, fontSize: 13 };
const tb: React.CSSProperties = { fontSize: 12, padding: "3px 8px" };
const chipX: React.CSSProperties = { border: "none", background: "none", cursor: "pointer", marginLeft: 4 };
