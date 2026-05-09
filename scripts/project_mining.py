#!/usr/bin/env python3
"""
Project Mining — antonio@casafolino.com
Analizza thread email dormienti, classifica via Groq, genera report MD + JSON.
One-shot script. Read-only su DB Odoo.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DOCKER_PSQL = (
    'docker exec -e PGPASSWORD=odoo odoo-app '
    'psql -h odoo-db -U odoo folinofood -t -A -F "|||" -c'
)
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_RATE_SLEEP = 2.0
GROQ_TIMEOUT = 30

# Noise domains / addresses to exclude
NOISE_DOMAINS = {
    "casafolino.com",  # internal — filtered separately by name
    "noreply", "no-reply", "no_reply",
    "notifications@", "bounce@", "mailer-daemon@",
    "linkedin.com", "mailchimp.com", "mailgun.org", "mailgun.net",
    "odoo.com", "aruba.it", "legalmail.it",
    "paypal.it", "paypal.com",
    "stripe.com", "fattureincloud.it",
    "amazonaws.com", "google.com", "googlemail.com",
    "coupang.com", "lovable.dev",
    "newsletter@", "info@plma.nl", "scanner@plma.nl",
    "foodweb.it", "thatsagrowth.com",
    "mktg-effetto-b2b.com",
    "substack.com", "beehiiv.com", "sendinblue.com",
    "hubspot.com", "mailerlite.com",
}

# Internal team from_name patterns (casafolino.com senders to keep only if external)
INTERNAL_NAMES = {"josefina", "martina", "maria", "anna", "teresa"}

# Newsletter / promo subject patterns
NOISE_SUBJECT_RE = re.compile(
    r"(newsletter|unsubscribe|webinar|save the date|la settimana:|"
    r"promo(zione)?|offerta speciale|black friday|cyber monday|"
    r"fai emergere|potenziale del tuo|credits now go|limited time)",
    re.IGNORECASE,
)


def run_sql(query):
    """Run SQL via docker exec, return list of rows (each row = list of cols)."""
    cmd = f"{DOCKER_PSQL} \"{query}\""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"SQL ERROR: {result.stderr[:300]}", file=sys.stderr)
        return []
    rows = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line:
            rows.append(line.split("|||"))
    return rows


def get_groq_key():
    rows = run_sql(
        "SELECT value FROM ir_config_parameter "
        "WHERE key='casafolino.groq_api_key'"
    )
    if not rows:
        print("FATAL: Groq API key not found in ir_config_parameter", file=sys.stderr)
        sys.exit(1)
    return rows[0][0].strip()


def get_account_id():
    rows = run_sql(
        "SELECT id FROM cf_mail_account "
        "WHERE email_address='antonio@casafolino.com' LIMIT 1"
    )
    if not rows:
        print("FATAL: Antonio account not found", file=sys.stderr)
        sys.exit(1)
    return int(rows[0][0])


def is_noise(from_address, from_name, subject):
    """Return True if message is noise (newsletter, internal, system)."""
    addr = (from_address or "").lower().strip()
    name = (from_name or "").lower().strip()
    subj = subject or ""

    # Internal team
    if "casafolino.com" in addr:
        first = name.split()[0] if name else ""
        if first in INTERNAL_NAMES:
            return True

    # Noise domains / patterns
    for pattern in NOISE_DOMAINS:
        if pattern in addr:
            return True

    # Noise subjects
    if NOISE_SUBJECT_RE.search(subj):
        return True

    return False


def fetch_threads(account_id, days):
    """Fetch all messages for account in date range, group by thread_key."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = (
        "SELECT id, thread_key, subject, from_address, from_name, "
        "direction, date, partner_id, "
        "LEFT(body_text, 1000) as body_snippet "
        f"FROM cf_mail_message "
        f"WHERE account_id={account_id} "
        f"AND date >= '{cutoff}' "
        "ORDER BY date ASC"
    )
    rows = run_sql(query)
    threads = {}
    for row in rows:
        if len(row) < 9:
            continue
        msg = {
            "id": int(row[0]),
            "thread_key": row[1],
            "subject": row[2],
            "from_address": row[3],
            "from_name": row[4],
            "direction": row[5],
            "date": row[6],
            "partner_id": row[7] if row[7] else None,
            "body_snippet": row[8],
        }
        tk = msg["thread_key"]
        if tk not in threads:
            threads[tk] = []
        threads[tk].append(msg)
    return threads


def filter_candidates(threads, min_dormant_days):
    """Filter threads to find dormant commercial candidates."""
    candidates = []
    now = datetime.utcnow()

    for tk, msgs in threads.items():
        # Skip single-message threads
        if len(msgs) < 2:
            continue

        # Check noise on first inbound message
        inbound_msgs = [m for m in msgs if m["direction"] == "in"]
        outbound_msgs = [m for m in msgs if m["direction"] == "out"]

        if not inbound_msgs:
            continue

        # Use first inbound to check noise
        first_in = inbound_msgs[0]
        if is_noise(first_in["from_address"], first_in["from_name"], first_in["subject"]):
            continue

        # Last message of thread
        last_msg = msgs[-1]
        last_inbound = inbound_msgs[-1]
        last_inbound_date = datetime.strptime(
            last_inbound["date"][:19], "%Y-%m-%d %H:%M:%S"
        )
        days_dormant = (now - last_inbound_date).days

        # Candidate if: last msg is inbound OR last inbound > min_dormant_days ago
        # with no outbound after it
        last_out_date = None
        if outbound_msgs:
            last_out = outbound_msgs[-1]
            last_out_date = datetime.strptime(
                last_out["date"][:19], "%Y-%m-%d %H:%M:%S"
            )

        is_candidate = False
        if last_msg["direction"] == "in" and days_dormant >= min_dormant_days:
            is_candidate = True
        elif last_out_date and last_inbound_date > last_out_date and days_dormant >= min_dormant_days:
            is_candidate = True
        elif not outbound_msgs and days_dormant >= min_dormant_days:
            is_candidate = True

        if not is_candidate:
            continue

        # Determine partner info
        partner_id = None
        from_addr = first_in["from_address"].lower().strip()
        from_name = first_in["from_name"] or from_addr.split("@")[0]
        for m in inbound_msgs:
            if m["partner_id"]:
                partner_id = m["partner_id"]
                break

        candidates.append({
            "thread_key": tk,
            "subject": first_in["subject"],
            "from_address": from_addr,
            "from_name": from_name,
            "partner_id": partner_id,
            "last_inbound_date": last_inbound_date.strftime("%Y-%m-%d"),
            "last_outbound_date": last_out_date.strftime("%Y-%m-%d") if last_out_date else None,
            "days_dormant": days_dormant,
            "total_messages": len(msgs),
            "messages": msgs,
        })

    # Sort by days_dormant descending
    candidates.sort(key=lambda c: c["days_dormant"], reverse=True)
    return candidates


def build_groq_prompt(candidate):
    """Build Groq prompt for classification."""
    msgs = candidate["messages"]
    # Last 3 messages, body truncated to 800 chars
    recent = msgs[-3:] if len(msgs) >= 3 else msgs
    msg_texts = []
    for m in recent:
        body = (m["body_snippet"] or "")[:800].strip()
        msg_texts.append(
            f"[{m['direction'].upper()}] {m['date'][:10]} | "
            f"Da: {m['from_name']} <{m['from_address']}>\n"
            f"Oggetto: {m['subject']}\n"
            f"Corpo: {body}"
        )

    thread_text = "\n---\n".join(msg_texts)

    system_msg = (
        "Sei un analista commerciale esperto nel settore food/export italiano, "
        "specializzato in private label, distribuzione GDO/HoReCa, export B2B, "
        "e partnership nel settore alimentare gourmet. "
        "Lavori per CasaFolino Srls, produttore artigianale calabrese di conserve, "
        "sughi, salse e condimenti gourmet. "
        "Analizza il thread email e classifica il progetto commerciale. "
        "Rispondi SOLO con JSON valido, senza markdown, senza commenti."
    )

    user_msg = f"""Analizza questo thread email e classifica il progetto commerciale dormiente.

CONTATTO: {candidate['from_name']} ({candidate['from_address']})
GIORNI SENZA RISPOSTA: {candidate['days_dormant']}
MESSAGGI TOTALI: {candidate['total_messages']}

THREAD:
{thread_text}

Rispondi con questo JSON esatto:
{{
  "project_type": "private_label|distribuzione_export|ordine_b2b|sample_request|partnership|richiesta_listino|fiera|logistica|fornitore|altro",
  "stage": "primo_contatto|offerta_inviata|sample_spedito|negoziazione_prezzo|in_attesa_decisione|ghosted|follow_up_necessario",
  "estimated_value": "high|medium|low",
  "block_reason": "max 150 caratteri, motivo del blocco/stallo",
  "next_action": "max 200 caratteri, azione concreta da fare, in italiano",
  "priority": "high|medium|low",
  "summary": "max 250 caratteri, contesto del progetto in italiano"
}}

Esempi:
1. Thread con distributore tedesco che chiede listino → {{"project_type":"distribuzione_export","stage":"primo_contatto","estimated_value":"high","block_reason":"Listino inviato ma nessun feedback ricevuto","next_action":"Inviare follow-up con offerta personalizzata per mercato DACH","priority":"high","summary":"Distributore tedesco interessato a linea sughi per mercato biologico Germania"}}
2. Thread con richiesta campioni da buyer GDO → {{"project_type":"sample_request","stage":"sample_spedito","estimated_value":"medium","block_reason":"Campioni spediti 45gg fa, nessun riscontro","next_action":"Chiamare buyer per feedback su degustazione campioni","priority":"medium","summary":"Buyer catena GDO Nord Italia richiede campionatura sughi e pesti"}}
"""
    return system_msg, user_msg


def call_groq(api_key, system_msg, user_msg, retry=True):
    """Call Groq API, return parsed JSON or None."""
    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        resp = requests.post(
            GROQ_ENDPOINT, headers=headers, json=payload, timeout=GROQ_TIMEOUT
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Clean markdown fences if present
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
        return json.loads(content)
    except (json.JSONDecodeError, KeyError) as e:
        if retry:
            print(f"  Retry (parse error: {e})", file=sys.stderr)
            time.sleep(GROQ_RATE_SLEEP)
            return call_groq(api_key, system_msg, user_msg, retry=False)
        print(f"  Skip (parse error after retry: {e})", file=sys.stderr)
        return None
    except Exception as e:
        if retry:
            print(f"  Retry (error: {e})", file=sys.stderr)
            time.sleep(GROQ_RATE_SLEEP)
            return call_groq(api_key, system_msg, user_msg, retry=False)
        print(f"  Skip (error after retry: {e})", file=sys.stderr)
        return None


def generate_report(results, days, top_n):
    """Generate markdown report."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    priority_order = {"high": 0, "medium": 1, "low": 2}
    results.sort(
        key=lambda r: (
            priority_order.get(r.get("priority", "low"), 2),
            -r.get("days_dormant", 0),
        )
    )
    top = results[:top_n]

    # Counts
    by_priority = {"high": 0, "medium": 0, "low": 0}
    by_type = {}
    for r in top:
        p = r.get("priority", "low")
        by_priority[p] = by_priority.get(p, 0) + 1
        t = r.get("project_type", "altro")
        by_type[t] = by_type.get(t, 0) + 1

    lines = [
        f"# Project Mining — antonio@casafolino.com",
        f"",
        f"Generato: {now_str}",
        f"Periodo analizzato: ultimi {days} giorni",
        f"Thread candidati totali: {len(results)} | Top selezionati: {len(top)}",
        f"",
        f"## Riepilogo per priorità",
        f"- **HIGH**: {by_priority['high']} progetti",
        f"- **MEDIUM**: {by_priority['medium']} progetti",
        f"- **LOW**: {by_priority['low']} progetti",
        f"",
        f"## Riepilogo per tipo",
    ]
    for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"- **{t}**: {c}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Group by priority
    sections = {
        "high": ("🔴 PRIORITÀ ALTA", []),
        "medium": ("🟡 PRIORITÀ MEDIA", []),
        "low": ("🟢 PRIORITÀ BASSA", []),
    }
    for r in top:
        p = r.get("priority", "low")
        sections[p][1].append(r)

    for prio_key in ["high", "medium", "low"]:
        title, items = sections[prio_key]
        if not items:
            continue
        lines.append(f"## {title}")
        lines.append("")
        for i, r in enumerate(items, 1):
            name = r.get("from_name", r.get("from_address", "?"))
            lines.append(f"### {i}. {name}")
            lines.append(f"- **Email**: {r.get('from_address', '?')}")
            lines.append(f"- **Tipo progetto**: {r.get('project_type', '?')}")
            lines.append(f"- **Stadio**: {r.get('stage', '?')}")
            lines.append(f"- **Valore stimato**: {r.get('estimated_value', '?')}")
            lines.append(f"- **Giorni dormienza**: {r.get('days_dormant', '?')}")
            lines.append(f"- **Ultimo contatto**: {r.get('last_inbound_date', '?')} (in)")
            if r.get("last_outbound_date"):
                lines.append(f"- **Ultimo invio**: {r['last_outbound_date']} (out)")
            lines.append(f"- **Summary**: {r.get('summary', '?')}")
            lines.append(f"- **Motivo blocco**: {r.get('block_reason', '?')}")
            lines.append(f"- **Next action**: {r.get('next_action', '?')}")
            lines.append(f"- **Subject ultimo thread**: {r.get('subject', '?')}")
            lines.append(f"- **Messaggi totali**: {r.get('total_messages', '?')}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Project Mining — CasaFolino")
    parser.add_argument("--days", type=int, default=365, help="Lookback days")
    parser.add_argument("--top", type=int, default=50, help="Top N results in report")
    parser.add_argument(
        "--min-dormant-days", type=int, default=30, help="Min days dormant"
    )
    args = parser.parse_args()

    start_time = time.time()
    print("Project Mining — antonio@casafolino.com")
    print(f"Config: days={args.days}, top={args.top}, min_dormant={args.min_dormant_days}")

    # Step 1: Get account & API key
    print("→ Recupero account Antonio...")
    account_id = get_account_id()
    print(f"  account_id={account_id}")

    print("→ Recupero Groq API key...")
    api_key = get_groq_key()
    print("  API key OK")

    # Step 2: Fetch threads
    print("→ Estrazione thread email...")
    threads = fetch_threads(account_id, args.days)
    print(f"  {len(threads)} thread trovati")

    # Step 3: Filter candidates
    print("→ Filtraggio candidati dormienti...")
    candidates = filter_candidates(threads, args.min_dormant_days)
    print(f"  {len(candidates)} candidati dopo filtraggio")

    if len(candidates) < 10:
        print(
            f"⚠️  WARNING: solo {len(candidates)} candidati — possibile bug nei filtri",
            file=sys.stderr,
        )

    # Step 4: Classify via Groq (top 100 max)
    to_classify = candidates[:100]
    print(f"→ Classificazione via Groq ({len(to_classify)} thread)...")
    classified = []

    for i, cand in enumerate(to_classify):
        try:
            sys_msg, usr_msg = build_groq_prompt(cand)
            result = call_groq(api_key, sys_msg, usr_msg)
            if result:
                # Merge candidate info with Groq result
                entry = {
                    "from_address": cand["from_address"],
                    "from_name": cand["from_name"],
                    "partner_id": cand["partner_id"],
                    "subject": cand["subject"],
                    "last_inbound_date": cand["last_inbound_date"],
                    "last_outbound_date": cand["last_outbound_date"],
                    "days_dormant": cand["days_dormant"],
                    "total_messages": cand["total_messages"],
                    "thread_key": cand["thread_key"],
                }
                entry.update(result)
                classified.append(entry)
                p = result.get("priority", "?")
                print(f"  [{i+1}/{len(to_classify)}] {cand['from_name'][:30]} → {p}")
            else:
                print(f"  [{i+1}/{len(to_classify)}] {cand['from_name'][:30]} → SKIP")
        except Exception as e:
            print(f"  [{i+1}/{len(to_classify)}] ERROR: {e}", file=sys.stderr)
            continue

        time.sleep(GROQ_RATE_SLEEP)

    print(f"  {len(classified)} thread classificati")

    # Step 5: Generate reports
    print("→ Generazione report...")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
    report_dir = "/home/ubuntu/reports"
    os.makedirs(report_dir, exist_ok=True)

    md_path = f"{report_dir}/project_mining_{ts}.md"
    json_path = f"{report_dir}/project_mining_{ts}.json"

    # MD report
    md_content = generate_report(classified, args.days, args.top)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # JSON report
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(classified, f, ensure_ascii=False, indent=2)

    elapsed = (time.time() - start_time) / 60

    # Summary counts
    by_p = {"high": 0, "medium": 0, "low": 0}
    for r in classified[:args.top]:
        by_p[r.get("priority", "low")] = by_p.get(r.get("priority", "low"), 0) + 1

    print()
    print("✅ Project Mining completato")
    print(f"Report MD: {md_path}")
    print(f"Report JSON: {json_path}")
    print(f"Thread analizzati: {len(classified)}")
    print(f"Candidati top {args.top}:")
    print(f"  🔴 HIGH:   {by_p['high']}")
    print(f"  🟡 MEDIUM: {by_p['medium']}")
    print(f"  🟢 LOW:    {by_p['low']}")
    print(f"Tempo totale: {elapsed:.1f} min")


if __name__ == "__main__":
    main()
