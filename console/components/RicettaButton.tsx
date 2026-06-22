"use client";
// Brief 10 — Ricetta personalizzata: wizard che crea un cf.task R&D (template_key='ricetta'),
// step Formulazione (default Maria, override). Niente ordine/spedizione. Manager-only.
import { useState } from "react";
import { creaRicetta, type RicettaStep } from "@/lib/documents";
import { lightColor } from "@/lib/campionatura";

export function RicettaButton({ leadId, partnerId, small = false, label = "Ricetta" }: {
  leadId?: number | null; partnerId?: number | null; small?: boolean; label?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className={small ? "btn-mini" : "btn-secondary"} onClick={() => setOpen(true)}>{label}</button>
      {open ? <Panel leadId={leadId} partnerId={partnerId} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function Panel({ leadId, partnerId, onClose }: { leadId?: number | null; partnerId?: number | null; onClose: () => void }) {
  const [productType, setProductType] = useState("");
  const [spec, setSpec] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [steps, setSteps] = useState<RicettaStep[] | null>(null);
  const [taskName, setTaskName] = useState("");

  function onType(e: React.ChangeEvent<HTMLInputElement>) { setProductType(e.target.value); }
  function onSpec(e: React.ChangeEvent<HTMLTextAreaElement>) { setSpec(e.target.value); }

  async function create() {
    setBusy(true); setErr(null);
    try {
      const r = await creaRicetta({ leadId: leadId ?? undefined, partnerId: partnerId ?? undefined, recipeSpec: spec, productType: productType || undefined });
      if (r.ok && r.steps) { setSteps(r.steps); setTaskName(r.name ?? "Ricetta"); } else setErr(r.message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: "min(480px,100%)", maxHeight: "90vh", overflow: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>Ricetta personalizzata</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>
        {err ? <div style={{ color: "var(--danger)", fontSize: 13 }}>{err}</div> : null}
        {steps ? (
          <>
            <div className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)", alignSelf: "flex-start" }}>Task creato ✓</div>
            <div style={{ fontWeight: 600, fontSize: 14 }}>{taskName}</div>
            {steps.map((s) => (
              <div key={s.stepId} className="row" style={{ justifyContent: "space-between", alignItems: "center", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)" }}>
                <div className="row" style={{ gap: 8, alignItems: "center" }}>
                  <span style={{ width: 10, height: 10, borderRadius: 6, background: lightColor[s.trafficLight as "green" | "yellow" | "red"] ?? "var(--line)", display: "inline-block" }} />
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{s.name}</span>
                </div>
                <span className="muted" style={{ fontSize: 12 }}>{s.assignee} · {s.state}</span>
              </div>
            ))}
            <button className="btn-primary" onClick={onClose} style={{ alignSelf: "flex-end" }}>Chiudi</button>
          </>
        ) : (
          <>
            <div>
              <label className="muted" style={{ fontSize: 11 }}>Tipo prodotto</label>
              <input value={productType} onChange={onType} placeholder="es. crema spalmabile pistacchio" style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13 }} />
            </div>
            <div>
              <label className="muted" style={{ fontSize: 11 }}>Spec ricetta</label>
              <textarea value={spec} onChange={onSpec} rows={5} placeholder="Requisiti: ingredienti, allergeni, target, vincoli…" style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 13, resize: "vertical" }} />
            </div>
            <div className="muted" style={{ fontSize: 12 }}>Step: <b>Formulazione → Maria</b> (R&D, niente ordine/spedizione)</div>
            <button className="btn-primary" onClick={create} disabled={busy || !spec.trim()} style={{ alignSelf: "flex-end" }}>
              {busy ? "Creo…" : "Crea ricetta"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
