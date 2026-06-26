"use client";
// Registry dei tile del wallboard. Ogni tile = componente + endpoint + intervallo refresh.
// Le scene (produzione/vetrina/ufficio) si limitano a dichiarare quali key montano.
import { useEffect, useState } from "react";
import { usePoll, flagEmoji, useFlashOnIncrease } from "@/components/wallboard/usePoll";
import { TileShell, PollBody } from "@/components/wallboard/Tile";
import { useReportAlert } from "@/components/wallboard/freshness";
import {
  lateOrdersStatus,
  pacingStatus,
  cutoffStatus,
  workdayFraction,
  pillClass,
  type Status,
} from "@/lib/wb/thresholds";
import { cutoffFor, minutesToCutoff, fmtCountdown } from "@/lib/wb/cutoffs";

// Intervalli (ms) da brief.
const R = {
  tasks: 20_000,
  mrp: 30_000,
  qc: 20_000,
  ordini: 30_000,
  spedizioni: 60_000,
  revenue: 300_000,
  export: 300_000,
  ticker: 60_000,
  fiera: 3_600_000,
  certs: 86_400_000, // di fatto mai
  pipeline: 60_000,
  goal: 30_000,
  cutoffs: 60_000,
  exceptions: 30_000,
} as const;

const eur = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const num = new Intl.NumberFormat("it-IT");

interface Props {
  token: string;
  /** true → tile in scena dove gli importi sono ammessi (ufficio). */
  withMoney?: boolean;
}

/* ---------------------------------------------------------------- PRODUZIONE */

type QueueRow = { partner: string; countryCode: string | null; colli: number; due: string | null; late: boolean };

export function OrdiniDaEvadere({ token }: Props) {
  const s = usePoll<{ rows: QueueRow[]; total: number; late: number }>("production-queue", token, R.ordini);
  const late = s.data?.late ?? 0;
  const st = lateOrdersStatus(late);
  // Coda priorità: max 5 righe, "+N altri".
  const rows = s.data?.rows ?? [];
  const shown = rows.slice(0, 5);
  const more = rows.length - shown.length;
  useReportAlert("ordini-ritardo", st === "alert");
  return (
    <TileShell
      title="Ordini da evadere"
      tint="clay"
      right={
        late > 0 ? (
          <span className={`wb-pill ${pillClass(st)}`}>{late} in ritardo</span>
        ) : (
          <span className="wb-pill">{s.data?.total ?? 0} colli</span>
        )
      }
    >
      <PollBody state={s} emptyWhen={(d) => !d.rows.length} emptyLabel="Nessun ordine in coda">
        {() => (
          <div className="wb-list">
            {shown.map((r, i) => (
              <div className={`wb-li${i === 0 ? " next" : ""}${r.late ? " late" : ""}`} key={i}>
                <span className="flag">{flagEmoji(r.countryCode)}</span>
                <span className="grow">{r.partner}</span>
                {r.late && <span className="wb-pill alert">ritardo</span>}
                <span className="num">{r.colli}</span>
              </div>
            ))}
            {more > 0 && <div className="wb-more">+{more} altri</div>}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function InProduzione({ token }: Props) {
  const s = usePoll<{ rows: { name: string; product: string; pct: number }[] }>("mrp-active", token, R.mrp);
  return (
    <TileShell title="In produzione" tint="sage">
      <PollBody state={s} emptyWhen={(d) => !d.rows.length} emptyLabel="Nessuna produzione attiva">
        {(d) => (
          <div className="wb-list">
            {d.rows.slice(0, 7).map((r, i) => (
              <div className="wb-li" key={i}>
                <span className="grow">{r.product}</span>
                <span className="wb-bar"><i className={r.pct >= 90 ? "done" : ""} style={{ width: `${r.pct}%` }} /></span>
                <span className="num">{r.pct}%</span>
              </div>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function LavorazioniOggi({ token }: Props) {
  const s = usePoll<{ rows: { operatore: string; mansione: string; titolo: string; light: string; qcOk: boolean }[] }>(
    "tasks-today", token, R.tasks,
  );
  return (
    <TileShell title="Lavorazioni oggi" tint="butter">
      <PollBody state={s} emptyWhen={(d) => !d.rows.length} emptyLabel="Nessuna lavorazione attiva">
        {(d) => (
          <div className="wb-list">
            {d.rows.slice(0, 8).map((r, i) => (
              <div className="wb-li" key={i}>
                <span className={`wb-dot ${r.light}`} />
                <span className="grow"><b>{r.operatore}</b> · {r.mansione}</span>
                <span className="wb-pill">{r.qcOk ? "✓ QC" : r.titolo.slice(0, 18)}</span>
              </div>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function SpedizioniOggi({ token }: Props) {
  const s = usePoll<{ rows: { carrier: string; count: number }[]; total: number }>("shipments-today", token, R.spedizioni);
  return (
    <TileShell title="Spedizioni oggi" tint="sky" right={<span className="wb-pill">{s.data?.total ?? 0}</span>}>
      <PollBody state={s} emptyWhen={(d) => !d.rows.length} emptyLabel="Nessuna spedizione oggi">
        {(d) => (
          <div className="wb-list">
            {d.rows.map((r, i) => (
              <div className="wb-li" key={i}>
                <span className="grow">{r.carrier}</span>
                <span className="num">{r.count}</span>
              </div>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function QcBloccanti({ token }: Props) {
  const s = usePoll<{ rows: { titolo: string; operatore: string }[]; blocked: number }>("qc-blocks", token, R.qc);
  const blocked = s.data?.blocked ?? 0;
  return (
    <TileShell
      title="QC bloccanti"
      tint={blocked > 0 ? "blush" : "sage"}
      right={<span className={`wb-pill ${blocked > 0 ? "alert" : "ok"}`}>{blocked}</span>}
    >
      <PollBody state={s}>
        {(d) =>
          d.blocked === 0 ? (
            <div className="wb-allgood">
              <div className="mark">✓</div>
              <div className="lbl">Tutto a posto</div>
            </div>
          ) : (
            <div className="wb-list">
              {d.rows.map((r, i) => (
                <div className="wb-li" key={i} style={{ color: "var(--alert)" }}>
                  <span className="wb-dot red" />
                  <span className="grow">{r.titolo}</span>
                  <span className="wb-pill alert">{r.operatore}</span>
                </div>
              ))}
            </div>
          )
        }
      </PollBody>
    </TileShell>
  );
}

/* ------------------------------------------------------------------ VETRINA */

export function PaesiExport({ token }: Props) {
  const s = usePoll<{ count: number }>("export-countries", token, R.export);
  return (
    <TileShell title="Export nel mondo" tint="sky">
      <PollBody state={s}>
        {(d) => (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div className="wb-big">{num.format(d.count)}</div>
            <div className="wb-sub">paesi serviti</div>
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function Certificazioni({ token }: Props) {
  const s = usePoll<{ certs: string[] }>("certifications", token, R.certs);
  return (
    <TileShell title="Certificazioni" tint="butter">
      <PollBody state={s}>
        {(d) => (
          <div className="wb-certs">
            {d.certs.map((c) => (
              <span className="wb-cert" key={c}>{c}</span>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function Crescita({ token }: Props) {
  // Vetrina: di default mostra SOLO la % di crescita (figureVisible=false dal server).
  const s = usePoll<{ growthPct: number | null; amount?: number; figureVisible: boolean }>("revenue-mtd", token, R.revenue);
  return (
    <TileShell title="Crescita del mese" tint="sage">
      <PollBody state={s}>
        {(d) => (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <div className="wb-big">{d.growthPct == null ? "—" : `${d.growthPct >= 0 ? "+" : ""}${d.growthPct}%`}</div>
            <div className="wb-sub">{d.figureVisible && d.amount != null ? eur.format(d.amount) : "vs mese precedente"}</div>
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function ProssimaFiera({ token }: Props) {
  const s = usePoll<{ name: string | null; location: string | null; country: string | null; days: number | null }>(
    "next-fair", token, R.fiera,
  );
  return (
    <TileShell title="Prossima fiera" tint="clay">
      <PollBody state={s} emptyWhen={(d) => !d.name} emptyLabel="Nessuna fiera in calendario">
        {(d) => (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 8 }}>
            <div style={{ fontFamily: "var(--wb-serif)", fontSize: "clamp(20px,2vw,34px)", color: "var(--brown)" }}>{d.name}</div>
            <div className="wb-sub">{[d.location, d.country].filter(Boolean).join(" · ")}</div>
            {d.days != null && (
              <div className="wb-count">
                <span className="n">{d.days}</span>
                <span className="u">{d.days === 1 ? "giorno" : "giorni"}</span>
              </div>
            )}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function Ticker({ token }: Props) {
  const s = usePoll<{ items: { icon: string; text: string }[] }>("ticker", token, R.ticker);
  const items = s.data?.items ?? [];
  const ICON: Record<string, string> = { order: "🧾", lot: "📦", ship: "🚚", fair: "🎪" };
  // Duplico la lista per il loop continuo del marquee (translateX -50%).
  const doubled = [...items, ...items];
  return (
    <div className="wb-ticker">
      {items.length === 0 ? (
        <span className="wb-ticker-item">{s.error ? `⚠ ${s.error}` : "…"}</span>
      ) : (
        <div className="wb-ticker-track">
          {doubled.map((it, i) => (
            <span className="wb-ticker-item" key={i}>
              {ICON[it.icon] ?? "•"} <b>{it.text}</b>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ UFFICIO */

export function FatturatoMese({ token }: Props) {
  const s = usePoll<{ amount?: number; target?: number; growthPct: number | null; targetPct: number | null }>(
    "revenue-mtd", token, R.revenue,
  );
  return (
    <TileShell title="Fatturato mese" tint="butter">
      <PollBody state={s}>
        {(d) => (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 6 }}>
            <div className="wb-big ink">{d.amount != null ? eur.format(d.amount) : "—"}</div>
            <div className="wb-sub">
              {d.growthPct != null && <span className={`wb-pill ${d.growthPct >= 0 ? "ok" : "alert"}`}>{d.growthPct >= 0 ? "+" : ""}{d.growthPct}% vs mese prec.</span>}
              {d.targetPct != null && <span style={{ marginLeft: 8 }}>{d.targetPct}% del target</span>}
            </div>
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function Pipeline({ token }: Props) {
  const s = usePoll<{ rows: { stage: string; count: number; expected: number }[]; overdue: number; totalExpected: number }>(
    "pipeline", token, R.pipeline,
  );
  return (
    <TileShell
      title="Pipeline"
      tint="sky"
      right={<span className={`wb-pill ${(s.data?.overdue ?? 0) > 0 ? "alert" : "ok"}`}>{s.data?.overdue ?? 0} scaduti</span>}
    >
      <PollBody state={s} emptyWhen={(d) => !d.rows.length} emptyLabel="Pipeline vuota">
        {(d) => (
          <div className="wb-list">
            {d.rows.map((r, i) => (
              <div className="wb-li" key={i}>
                <span className="grow">{r.stage}</span>
                <span className="wb-pill">{r.count}</span>
                <span className="num">{eur.format(r.expected)}</span>
              </div>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

/* ------------------------------------------------------ V2 — AZIONABILITÀ */

/** Obiettivo giornaliero + pacing (faro scene operative). */
export function DailyGoalTile({ token, dept }: Props & { dept: "produzione" | "logistica" }) {
  const s = usePoll<{ label: string; done: number; goal: number; unit: string }>(
    `daily-goal?dept=${dept}`, token, R.goal,
  );
  const done = s.data?.done ?? 0;
  const goal = s.data?.goal ?? 0;
  const flash = useFlashOnIncrease(s.data?.done);
  const st: Status = pacingStatus(done, goal, workdayFraction());
  const pct = goal > 0 ? Math.min(100, Math.round((done / goal) * 100)) : 0;
  useReportAlert(`goal-${dept}`, st === "alert");
  return (
    <TileShell
      title={s.data?.label ?? "Obiettivo del giorno"}
      tint="butter"
      right={<span className={`wb-pill ${pillClass(st)}`}>{st === "ok" ? "in pari" : st === "warn" ? "rallenta" : "in ritardo"}</span>}
    >
      <div className={`wb-goal${flash ? " flash" : ""}`} style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
        <div className="wb-count">
          <span className="n">{done}</span>
          <span className="u">/ {goal} {s.data?.unit ?? ""}</span>
        </div>
        <div className="wb-bar big"><i className={st === "ok" ? "done" : st === "alert" ? "alert" : ""} style={{ width: `${pct}%` }} /></div>
        <div className="wb-sub">completati oggi: <b>{done}</b></div>
      </div>
    </TileShell>
  );
}

/** Countdown cut-off corrieri (faro logistica). */
export function CutoffTile({ token }: Props) {
  const s = usePoll<{ rows: { carrier: string; open: number }[] }>("cutoffs", token, R.cutoffs);
  // re-render del countdown ogni 30s.
  const [, tick] = useTick(30_000);
  const rows = (s.data?.rows ?? [])
    .map((r) => {
      const cfg = cutoffFor(r.carrier);
      const mins = cfg ? minutesToCutoff(cfg.pickup) : null;
      const st: Status = cfg && mins != null ? cutoffStatus(mins, r.open) : "ok";
      return { ...r, cfg, mins, st };
    })
    .filter((r) => r.cfg) // mostra solo corrieri con orario configurato
    .sort((a, b) => (a.mins ?? 0) - (b.mins ?? 0));
  const anyAlert = rows.some((r) => r.st === "alert");
  useReportAlert("cutoff", anyAlert);
  void tick;
  return (
    <TileShell title="Cut-off corrieri" tint="sky">
      <PollBody state={s} emptyWhen={() => rows.length === 0} emptyLabel="Nessun corriere configurato">
        {() => (
          <div className="wb-list">
            {rows.map((r, i) => (
              <div className={`wb-li${r.st === "alert" ? " late" : ""}`} key={i}>
                <span className="grow"><b>{r.cfg!.label}</b> · ritiro {r.cfg!.pickup}</span>
                <span className={`wb-pill ${pillClass(r.st)}`}>{r.mins != null ? fmtCountdown(r.mins) : "—"}</span>
                <span className="num">{r.open}</span>
              </div>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

/* ------------------------------------------------------------- LOGISTICA */

export function ProntiVsImballare({ token }: Props) {
  const s = usePoll<{ ready: number; toPack: number }>("shipments-today", token, R.spedizioni);
  return (
    <TileShell title="Pronti vs da imballare" tint="sage">
      <PollBody state={s}>
        {(d) => (
          <div className="wb-split">
            <div className="wb-split-h">
              <div className="wb-big ink">{d.ready ?? 0}</div>
              <div className="wb-sub">pronti</div>
            </div>
            <div className="wb-split-h">
              <div className="wb-big">{d.toPack ?? 0}</div>
              <div className="wb-sub">da imballare</div>
            </div>
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

export function InRitardo({ token }: Props) {
  const s = usePoll<{ lateRows: { partner: string; due: string | null }[]; late: number }>("shipments-today", token, R.spedizioni);
  const late = s.data?.late ?? 0;
  useReportAlert("logistica-ritardo", late > 0);
  return (
    <TileShell title="In ritardo" tint={late > 0 ? "blush" : "sage"} right={<span className={`wb-pill ${late > 0 ? "alert" : "ok"}`}>{late}</span>}>
      <PollBody state={s}>
        {(d) =>
          (d.late ?? 0) === 0 ? (
            <div className="wb-allgood"><div className="mark">✓</div><div className="lbl">Nessun ritardo</div></div>
          ) : (
            <div className="wb-list">
              {d.lateRows.map((r, i) => (
                <div className="wb-li late" key={i} style={{ color: "var(--alert)" }}>
                  <span className="grow">{r.partner}</span>
                  <span className="wb-pill alert">{r.due ?? "—"}</span>
                </div>
              ))}
            </div>
          )
        }
      </PollBody>
    </TileShell>
  );
}

export function SpedizioniPartite({ token }: Props) {
  const s = usePoll<{ total: number; rows: { carrier: string; count: number }[] }>("shipments-today", token, R.spedizioni);
  const flash = useFlashOnIncrease(s.data?.total);
  return (
    <TileShell title="Spedizioni di oggi" tint="sky" right={<span className="wb-pill">{s.data?.total ?? 0}</span>}>
      <PollBody state={s} emptyWhen={(d) => !d.rows.length} emptyLabel="Nessuna spedizione">
        {(d) => (
          <div className={`wb-list${flash ? " flash" : ""}`}>
            {d.rows.map((r, i) => (
              <div className="wb-li" key={i}>
                <span className="grow">{r.carrier}</span>
                <span className="num">{r.count}</span>
              </div>
            ))}
          </div>
        )}
      </PollBody>
    </TileShell>
  );
}

/* ------------------------------------------------------------- DIREZIONE */

export function PannelloEccezioni({ token }: Props) {
  const s = usePoll<{
    exceptions: { kind: string; label: string; detail: string; status: Status; count: number }[];
    summary: { lateOrders: number; qcBlocks: number; notStartedLots: number };
  }>("exceptions", token, R.exceptions);
  const exc = s.data?.exceptions ?? [];
  useReportAlert("direzione-exc", exc.some((e) => e.status === "alert"));
  return (
    <TileShell title="Eccezioni da gestire" tint={exc.length ? "blush" : "sage"} span={3}>
      <PollBody state={s}>
        {(d) =>
          d.exceptions.length === 0 ? (
            <div className="wb-allgood">
              <div className="mark">✓</div>
              <div className="lbl">Tutto in linea</div>
              <div className="wb-sub">
                ritardi {d.summary.lateOrders} · QC {d.summary.qcBlocks} · lotti fermi {d.summary.notStartedLots}
              </div>
            </div>
          ) : (
            <div className="wb-list">
              {d.exceptions.map((e, i) => (
                <div className={`wb-li exc ${e.status}`} key={i}>
                  <span className={`wb-dot ${e.status === "alert" ? "red" : "yellow"}`} />
                  <span className="grow"><b>{e.label}</b> · {e.detail}</span>
                  <span className={`wb-pill ${pillClass(e.status)}`}>{e.count}</span>
                </div>
              ))}
            </div>
          )
        }
      </PollBody>
    </TileShell>
  );
}

/* --------------------------------------------------------------- helpers */
/** Forza un re-render ogni N ms (per countdown client-side). */
function useTick(ms: number): [number, () => void] {
  const [n, setN] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setN((x) => x + 1), ms);
    return () => clearInterval(id);
  }, [ms]);
  return [n, () => setN((x) => x + 1)];
}
