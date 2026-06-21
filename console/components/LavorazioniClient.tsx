"use client";
// "Le mie lavorazioni" — superficie operatore mobile-first. Lista degli step dell'operatore
// (console_list_my_steps, filtra per sessione server-side). Per ognuno check-in + conferma.
// Logistica: tracking_code+carrier obbligatori (il gateway blocca senza → gestiamo il messaggio).
import { useCallback, useEffect, useState } from "react";
import {
  listMySteps, stepCheckin, stepConfirm, type MyStep,
  roleLabel, stepStateLabel, lightColor,
} from "@/lib/campionatura";

export function LavorazioniClient() {
  const [steps, setSteps] = useState<MyStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const data = await listMySteps();
      if (Array.isArray(data)) setSteps(data);
      else setErr((data as { message?: string }).message ?? "errore");
    } catch (e) { setErr((e as Error).message); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="muted" style={{ padding: 16 }}>Carico…</div>;
  if (err) return <div style={{ padding: 16, color: "var(--bad, #B23B3B)" }}>Errore: {err}</div>;
  if (!steps.length) return <div className="muted" style={{ padding: 16 }}>Nessuna lavorazione assegnata. 🎉</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 560, margin: "0 auto" }}>
      {steps.map((s) => <StepCard key={s.stepId} step={s} onDone={load} />)}
    </div>
  );
}

function StepCard({ step, onDone }: { step: MyStep; onDone: () => void }) {
  const [tracking, setTracking] = useState(step.tracking || "");
  const [carrier, setCarrier] = useState(step.carrier || "");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  function onTracking(e: React.ChangeEvent<HTMLInputElement>) { setTracking(e.target.value); }
  function onCarrier(e: React.ChangeEvent<HTMLInputElement>) { setCarrier(e.target.value); }

  async function checkin() {
    setBusy(true); setMsg(null);
    try {
      const r = await stepCheckin(step.stepId);
      if (r.ok) onDone(); else setMsg(r.message ?? "errore check-in");
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }

  async function confirm() {
    setBusy(true); setMsg(null);
    try {
      const r = await stepConfirm(step.stepId, tracking || undefined, carrier || undefined);
      if (r.ok) onDone(); else setMsg(r.message ?? "errore conferma");
    } catch (e) { setMsg((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="card" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>{roleLabel[step.role] ?? step.role}</div>
          <div className="muted" style={{ fontSize: 13 }}>{step.taskName}</div>
          {step.partner ? <div className="muted" style={{ fontSize: 12 }}>{step.partner}</div> : null}
        </div>
        <span style={{ width: 12, height: 12, borderRadius: 8, background: lightColor[step.trafficLight], display: "inline-block", marginTop: 4 }} />
      </div>

      <div className="row" style={{ gap: 8, alignItems: "center" }}>
        <span className="chip" style={{ fontSize: 12 }}>{stepStateLabel[step.state] ?? step.state}</span>
        <span className="muted" style={{ fontSize: 12 }}>{step.hours}h lavorative</span>
      </div>

      {/* Logistica: tracking + carrier obbligatori per confermare */}
      {step.isLogistica ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <input value={carrier} onChange={onCarrier} placeholder="Corriere (obbligatorio)"
            style={{ padding: "10px 12px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 15 }} />
          <input value={tracking} onChange={onTracking} placeholder="Tracking (obbligatorio)"
            style={{ padding: "10px 12px", borderRadius: 8, border: "1px solid var(--line)", fontSize: 15 }} />
        </div>
      ) : null}

      {msg ? <div style={{ color: "var(--bad, #B23B3B)", fontSize: 13 }}>{msg}</div> : null}

      <div className="row" style={{ gap: 8 }}>
        {step.canCheckin ? (
          <button className="btn-secondary" onClick={checkin} disabled={busy} style={{ flex: 1, padding: 12, fontSize: 15 }}>
            {busy ? "…" : "Check-in"}
          </button>
        ) : null}
        <button className="btn-primary" onClick={confirm} disabled={busy} style={{ flex: 1, padding: 12, fontSize: 15 }}>
          {busy ? "…" : "Conferma"}
        </button>
      </div>
    </div>
  );
}
