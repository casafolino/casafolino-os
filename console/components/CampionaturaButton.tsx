"use client";
// Bottone "Campionatura" + wizard in modal. Punto di lancio da mail / dossier partner / pipeline.
// Wizard: partner/lead precompilato, picker prodotti+qty, assegnatari (default mostrati, override),
// carrier opz. "Crea" → console_crea_campionatura → mostra la timeline.
import { useEffect, useState, useCallback } from "react";
import {
  searchProducts, createCampionatura, getCampDefaults,
  type ProductHit, type WizardLine, type CampDefaults, roleLabel,
} from "@/lib/campionatura";
import { CampionaturaTimeline } from "@/components/CampionaturaTimeline";

const ROLES = ["coordinazione", "creazione", "logistica"] as const;

export function CampionaturaButton({
  partnerId, leadId, label = "Campionatura", small = false,
}: { partnerId?: number | null; leadId?: number | null; label?: string; small?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button className={small ? "btn-mini" : "btn-primary"} onClick={() => setOpen(true)}>{label}</button>
      {open ? <CampionaturaModal partnerId={partnerId} leadId={leadId} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function CampionaturaModal({ partnerId, leadId, onClose }: { partnerId?: number | null; leadId?: number | null; onClose: () => void }) {
  const [lines, setLines] = useState<WizardLine[]>([]);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<ProductHit[]>([]);
  const [carrier, setCarrier] = useState("");
  const [defs, setDefs] = useState<CampDefaults | null>(null);
  const [override, setOverride] = useState<Record<string, number>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [createdShipment, setCreatedShipment] = useState<number | null>(null);

  useEffect(() => { getCampDefaults().then(setDefs).catch(() => {}); }, []);

  const runSearch = useCallback(async (q: string) => {
    setQuery(q);
    if (q.trim().length < 2) { setHits([]); return; }
    try { setHits(await searchProducts(q)); } catch { setHits([]); }
  }, []);

  function addLine(p: ProductHit) {
    if (lines.some((l) => l.productId === p.id)) return;
    setLines([...lines, { productId: p.id, name: p.name, qty: 1 }]);
    setQuery(""); setHits([]);
  }
  function setQty(productId: number, qty: number) {
    setLines(lines.map((l) => (l.productId === productId ? { ...l, qty: Math.max(1, qty) } : l)));
  }
  function removeLine(productId: number) {
    setLines(lines.filter((l) => l.productId !== productId));
  }

  function onSearchChange(e: React.ChangeEvent<HTMLInputElement>) { runSearch(e.target.value); }
  function onCarrierChange(e: React.ChangeEvent<HTMLInputElement>) { setCarrier(e.target.value); }
  function onAssigneeChange(role: string) {
    return (e: React.ChangeEvent<HTMLSelectElement>) => {
      const uid = Number(e.target.value);
      setOverride((o) => ({ ...o, [role]: uid }));
    };
  }
  function onQtyChange(productId: number) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setQty(productId, Number(e.target.value));
  }

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const assignees = Object.keys(override).length ? override : undefined;
      const res = await createCampionatura({
        partnerId, leadId,
        lines: lines.map((l) => ({ productId: l.productId, qty: l.qty })),
        assignees, carrier: carrier || undefined,
      });
      if (res.ok && res.shipment_id) {
        setCreatedShipment(res.shipment_id);
      } else {
        setErr(res.message ?? "Creazione fallita.");
      }
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: 16 }}>
      <div className="card" onClick={(e) => e.stopPropagation()}
        style={{ width: "min(560px, 100%)", maxHeight: "90vh", overflow: "auto", padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>Nuova campionatura</div>
          <button className="btn-mini" onClick={onClose}>✕</button>
        </div>

        {createdShipment ? (
          <>
            <div className="chip" style={{ background: "var(--ok-t)", color: "var(--ok)", alignSelf: "flex-start" }}>Creata ✓</div>
            <CampionaturaTimeline shipmentId={createdShipment} />
            <button className="btn-primary" onClick={onClose} style={{ alignSelf: "flex-end" }}>Chiudi</button>
          </>
        ) : (
          <>
            {!partnerId && !leadId ? (
              <div className="muted" style={{ fontSize: 12, color: "var(--bad, #B23B3B)" }}>
                Nessun partner/lead collegato: serve un contatto.
              </div>
            ) : null}

            {/* picker prodotti */}
            <div>
              <label className="muted" style={{ fontSize: 12 }}>Prodotti</label>
              <input value={query} onChange={onSearchChange} placeholder="Cerca prodotto (nome o codice)…"
                style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)" }} />
              {hits.length ? (
                <div className="card" style={{ marginTop: 4, padding: 4, maxHeight: 160, overflow: "auto" }}>
                  {hits.map((p) => (
                    <div key={p.id} onClick={() => addLine(p)}
                      style={{ padding: "6px 8px", cursor: "pointer", borderRadius: 6, fontSize: 13 }}
                      className="hover-row">
                      {p.name} {p.code ? <span className="muted">· {p.code}</span> : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            {/* righe selezionate */}
            {lines.length ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {lines.map((l) => (
                  <div key={l.productId} className="row" style={{ justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                    <span style={{ fontSize: 13, flex: 1 }}>{l.name}</span>
                    <input type="number" min={1} value={l.qty} onChange={onQtyChange(l.productId)}
                      style={{ width: 64, padding: "4px 6px", borderRadius: 6, border: "1px solid var(--line)" }} />
                    <button className="btn-mini" onClick={() => removeLine(l.productId)}>✕</button>
                  </div>
                ))}
              </div>
            ) : <div className="muted" style={{ fontSize: 12 }}>Nessun prodotto aggiunto.</div>}

            {/* assegnatari */}
            <div>
              <label className="muted" style={{ fontSize: 12 }}>Assegnatari</label>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
                {ROLES.map((role) => {
                  const def = defs?.defaults[role];
                  return (
                    <div key={role} className="row" style={{ justifyContent: "space-between", gap: 8, alignItems: "center" }}>
                      <span style={{ fontSize: 13, width: 110 }}>{roleLabel[role]}</span>
                      <select onChange={onAssigneeChange(role)} value={override[role] ?? (def ? def.uid : 0)}
                        style={{ flex: 1, padding: "6px 8px", borderRadius: 6, border: "1px solid var(--line)" }}>
                        {def ? <option value={def.uid}>{def.name} (default)</option> : <option value={0}>—</option>}
                        {defs?.operators.filter((o) => !def || o.uid !== def.uid).map((o) => (
                          <option key={o.uid} value={o.uid}>{o.name}</option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* carrier */}
            <div>
              <label className="muted" style={{ fontSize: 12 }}>Corriere (opzionale)</label>
              <input value={carrier} onChange={onCarrierChange} placeholder="es. BRT, DHL…"
                style={{ width: "100%", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)" }} />
            </div>

            {err ? <div style={{ color: "var(--bad, #B23B3B)", fontSize: 13 }}>{err}</div> : null}

            <button className="btn-primary" onClick={submit}
              disabled={busy || !lines.length || (!partnerId && !leadId)}
              style={{ alignSelf: "flex-end" }}>
              {busy ? "Creo…" : "Crea campionatura"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
