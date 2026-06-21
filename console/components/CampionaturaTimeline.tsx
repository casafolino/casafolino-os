"use client";
// Vista timeline campionatura: step task (ruolo/assegnatario/stato/semaforo) + spedizione (stato/tracking).
// Semaforo verde/giallo/rosso sui tempi; "Sollecita" sullo step rosso.
import { useCallback, useEffect, useState } from "react";
import {
  getTimeline, stepRemind, type Timeline,
  roleLabel, stepStateLabel, shipmentStateLabel, lightColor,
} from "@/lib/campionatura";

const SHIP_FLOW = ["creato", "preparazione", "spedito", "consegnato"];

export function CampionaturaTimeline({ shipmentId, compact = false }: { shipmentId: number; compact?: boolean }) {
  const [tl, setTl] = useState<Timeline | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true); setErr(null);
    try {
      const data = await getTimeline(shipmentId);
      if ((data as { ok?: boolean; message?: string }).message && !data.steps) {
        setErr((data as { message?: string }).message ?? "errore");
      } else {
        setTl(data);
      }
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }, [shipmentId]);

  useEffect(() => { load(); }, [load]);

  async function remind(stepId: number) {
    await stepRemind(stepId);
    load();
  }

  if (err) return <div className="card" style={{ padding: 14, color: "var(--bad, #B23B3B)" }}>Errore: {err}</div>;
  if (!tl) return <div className="card muted" style={{ padding: 14 }}>Carico timeline…</div>;

  const shipIdx = SHIP_FLOW.indexOf(tl.shipmentState);

  return (
    <div className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 15 }}>{tl.name} · {tl.partner}</div>
          <div className="muted" style={{ fontSize: 12 }}>Campionatura {tl.sampleCode}</div>
        </div>
        <span className="dot" style={{ width: 12, height: 12, borderRadius: 8, background: lightColor[tl.taskTrafficLight], display: "inline-block" }}
          title={`Semaforo task: ${tl.taskTrafficLight}`} />
      </div>

      {/* step task */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {tl.steps.map((s) => (
          <div key={s.stepId} className="row" style={{
            justifyContent: "space-between", alignItems: "center", gap: 8,
            padding: "8px 10px", borderRadius: 8,
            background: s.state === "confermato" ? "rgba(47,107,79,0.06)" : "var(--panel-2, #fafafa)",
            border: `1px solid ${s.trafficLight === "red" ? lightColor.red : "var(--line)"}`,
          }}>
            <div className="row" style={{ gap: 10, alignItems: "center" }}>
              <span style={{ width: 10, height: 10, borderRadius: 6, background: lightColor[s.trafficLight], display: "inline-block" }} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{roleLabel[s.role] ?? s.role}</div>
                <div className="muted" style={{ fontSize: 12 }}>{s.assignee}</div>
              </div>
            </div>
            <div className="row" style={{ gap: 10, alignItems: "center" }}>
              <span className="chip" style={{ fontSize: 11 }}>{stepStateLabel[s.state] ?? s.state}</span>
              <span className="muted" style={{ fontSize: 11 }}>{s.hours}h</span>
              {s.trafficLight === "red" && s.state !== "confermato" ? (
                <button className="btn-mini" onClick={() => remind(s.stepId)} style={{ fontSize: 11 }}>Sollecita</button>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      {/* spedizione */}
      <div style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>Spedizione</span>
          <span className="chip" style={{ fontSize: 11 }}>{shipmentStateLabel[tl.shipmentState] ?? tl.shipmentState}</span>
        </div>
        <div className="row" style={{ gap: 6, marginBottom: 8 }}>
          {SHIP_FLOW.map((st, i) => (
            <span key={st} style={{
              flex: 1, height: 4, borderRadius: 2,
              background: i <= shipIdx ? lightColor.green : "var(--line)",
            }} title={shipmentStateLabel[st]} />
          ))}
        </div>
        <div className="muted" style={{ fontSize: 12 }}>
          Corriere: <b>{tl.carrier || "—"}</b> · Tracking: <b>{tl.tracking || "—"}</b>
        </div>
      </div>

      {!compact ? (
        <button className="btn-mini" onClick={load} disabled={busy} style={{ alignSelf: "flex-start", fontSize: 11 }}>
          {busy ? "Aggiorno…" : "Aggiorna"}
        </button>
      ) : null}
    </div>
  );
}
