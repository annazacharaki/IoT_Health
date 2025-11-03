# chat_verb_fixed.py — Improved LLM-to-SQL translator for app8.py
# Fixes: temperature→temp mapping, proper daily aggregates, English-only verbalizer

import os, re, time, json, sqlite3, requests
from typing import List, Tuple, Any

# === Ollama Config ===
OLLAMA_URL = os.environ.get("OLLAMA_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
#MODEL_NAME = os.environ.get("OLLAMA_MODEL", "orca-mini:3b")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2:1.5b-instruct")
TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.2"))
MAX_TOKENS_SQL = int(os.environ.get("OLLAMA_TOKENS_SQL", "200"))
MAX_TOKENS_SUM = int(os.environ.get("OLLAMA_TOKENS_SUM", "160"))
HTTP_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

# === Schema & Prompt Guidance ===
SCHEMA = """
CREATE TABLE temp_data (id INTEGER PRIMARY KEY, timestamp TEXT, temp REAL);
CREATE TABLE spo2_data (id INTEGER PRIMARY KEY, timestamp TEXT, spo2 REAL);
Mapping: temperature/temp → temp_data.temp, SpO2/oxygen → spo2_data.spo2.
"""

GUIDANCE = r""" Use this minimal guidance to produce clear, correct SQL for the temp_data and spo2_data tables. Keep it concise — fewer rules, less confusion.

Output: Return exactly one fenced SQL block (sql ... ), one SELECT statement, ending with a semicolon. No prose.

Tables & columns:

temp_data(id, timestamp, temp) — use temp for temperature.

spo2_data(id, timestamp, spo2) — use spo2 for SpO2.

Latest / last:

For "last" or "latest" requests, return the newest rows by time: ORDER BY datetime(timestamp) DESC LIMIT 1 (for single latest) or LIMIT 10 (for plural/latest readings)

Do NOT use aggregates or GROUP BY for "latest".

Daily aggregates:

When user asks for daily results: SELECT date(timestamp) AS day, FROM GROUP BY day ORDER BY day;

Always aggregate metrics (AVG(temp), AVG(spo2), etc). No raw timestamp with aggregates.

Average / aggregates (non-daily):

Example: SELECT AVG(temp) AS avg_temp FROM temp_data [WHERE ...];

Do not mix non-aggregated columns with aggregates unless you use GROUP BY.

Time filters (only if user mentions time):

"on YYYY-MM-DD": WHERE date(timestamp) = 'YYYY-MM-DD'

"last 24 hours": WHERE timestamp >= datetime('now','-24 hours')

"in July 2025": WHERE timestamp >= '2025-07-01' AND timestamp < '2025-08-01'

Examples:
-- Latest SpO2 reading
SELECT timestamp, spo2 FROM spo2_data ORDER BY datetime(timestamp) DESC LIMIT 1;
-- Average temperature last 24 hours
SELECT AVG(temp) AS avg_temp FROM temp_data WHERE timestamp >= datetime('now','-24 hours');
-- Daily SpO2 for last 7 days
SELECT date(timestamp) AS day, AVG(spo2) AS avg_spo2 FROM spo2_data WHERE date(timestamp) >= date('now','-6 days') GROUP BY day ORDER BY day;
"""


FENCED_SQL = re.compile(r"```sql\s*(.*?)\s*```", re.I | re.S)
DATE_ONE = re.compile(r"\bon\s+(\d{4}-\d{2}-\d{2})\b", re.I)

# =====================
# Ollama HTTP helper
# =====================

def ollama_chat(messages, model=MODEL_NAME, num_predict=200, temperature=TEMPERATURE, url=OLLAMA_URL, timeout=HTTP_TIMEOUT) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": float(temperature),
            "num_predict": int(num_predict),
        },
    }
    r = requests.post(f"{url}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "message" in data:
        return data["message"].get("content", "")
    choices = data.get("choices") or []
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return ""

# =====================
# Public API (used by app8.py)
# =====================

def extract_sql(text: str) -> str:
    if not text:
        return ""
    m = FENCED_SQL.search(text)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"(?is)\bselect\b[\s\S]+?;", text or "")
    return (m2.group(0).strip() if m2 else "")

BANNED = re.compile(r"\b(attach|pragma|create|insert|update|delete|drop|alter|vacuum|reindex|analyze|explain)\b", re.I)

def is_safe_readonly(sql: str) -> bool:
    s = (sql or "").strip()
    if not s:
        return False
    if s.count(";") > 1:
        return False
    if not s.lower().startswith(("select", "with")):
        return False
    if BANNED.search(s):
        return False
    return True

# Read-only execution

def run_readonly(conn: sqlite3.Connection, sql: str) -> Tuple[List[str], List[tuple], int]:
    start = time.time()
    cur = conn.cursor()
    cur.execute("PRAGMA query_only=ON;")
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    ms = int((time.time() - start) * 1000)
    return cols, rows, ms

# =====================
# Post-processing / hardening
# =====================

def _strip_comments_and_first_stmt(s: str) -> str:
    s = re.sub(r"/\*[\s\S]*?\*/", "", s)  # /* ... */
    s = re.sub(r"--[^\n]*", "", s)          # -- ...
    parts = [p.strip() for p in s.split(";") if p.strip()]
    return (parts[0] if parts else "")


def _fix_table_column_mismatch(s: str) -> str:
    # Global normalization: temperature → temp
    s = re.sub(r"\btemperature\b", "temp", s, flags=re.I)
    return s


def _fix_on_without_join(s: str) -> str:
    if " on " in s.lower() and " join " not in s.lower():
        s = re.sub(r"\bon\b\s+[^\s,]+", "", s, flags=re.I)
    return s


def _ensure_select_from_when_missing(s: str, user_q: str) -> str:
    lowered = s.lower()
    if lowered.startswith("select") and " from " not in lowered:
        table, col = _metric_from_user_q(user_q)
        m = re.search(r"\bwhere\b[\s\S]+$", s, flags=re.I)
        tail = (" " + m.group(0).strip()) if m else ""
        return f"SELECT timestamp, {col} FROM {table}{tail}"
    return s


def _apply_one_day_filter_if_requested(s: str, user_q: str) -> str:
    m = DATE_ONE.search(user_q or "")
    if not m:
        return s
    day = m.group(1)
    if re.search(r"where\b", s, flags=re.I):
        if re.search(rf"date\(timestamp\)\s*=\s*'{day}'", s, flags=re.I):
            return s
        return re.sub(r"(where\b)", rf"\\1 date(timestamp)='{day}' AND ", s, flags=re.I, count=1)
    m2 = re.search(r"\bgroup\s+by\b|\border\s+by\b|\blimit\b", s, flags=re.I)
    if m2:
        return s[:m2.start()].rstrip(" ;") + f"\nWHERE date(timestamp)='{day}'\n" + s[m2.start():]
    return s.rstrip(" ;") + f"\nWHERE date(timestamp)='{day}'"


def _strip_unrequested_time_filters(s: str, user_q: str) -> str:
    if _user_wants_time_filter(user_q):
        return s
    m = re.search(r"\bwhere\b", s, flags=re.I)
    if not m:
        return s
    rest = s[m.end():]
    if not re.search(r"(timestamp|date\s*\()", rest, flags=re.I):
        return s
    m2 = re.search(r"\b(group\s+by|order\s+by|limit)\b", rest, flags=re.I)
    tail = rest[m2.start():] if m2 else ""
    head = s[:m.start()]
    return (head + tail).strip()


def _user_wants_time_filter(user_q: str) -> bool:
    u = (user_q or "").lower()
    if re.search(r"\bon\s+\d{4}-\d{2}-\d{2}\b", u): return True
    if " between " in u and " and " in u: return True
    if re.search(r"\blast\s+\d+\s+(day|days|hour|hours|week|weeks|month|months)\b", u): return True
    if re.search(r"\bin\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b", u): return True
    if re.search(r"\b(since|until|after|before)\b", u): return True
    return False


def _normalize_metric_columns(s: str) -> str:
    lowered = s.lower()
    if " from temp_data" in lowered:
        s = re.sub(r"\btemperature\b", "temp", s, flags=re.I)
    return s


def _ensure_group_by_if_daily_agg(s: str) -> str:
    lowered = s.lower()
    has_day = "date(timestamp) as day" in lowered
    has_agg = any(k in lowered for k in [" avg(", " min(", " max(", " sum(", " count("])
    if has_day and " group by " not in lowered and has_agg:
        m = re.search(r"\b(order\s+by|limit)\b", s, flags=re.I)
        if m:
            return s[:m.start()].rstrip(" ;") + "\nGROUP BY day\n" + s[m.start():]
        return s.rstrip(" ;") + "\nGROUP BY day"
    return s


def _coerce_daily_shape_if_needed(s: str, user_q: str) -> str:
    lowered = s.lower()
    if " group by day" not in lowered:
        return s
    table = "temp_data" if " from temp_data" in lowered else ("spo2_data" if " from spo2_data" in lowered else None)
    metric = "temp" if table == "temp_data" else ("spo2" if table == "spo2_data" else None)
    m = re.search(r"^\s*select\s+(.+?)\s+from\s", s, flags=re.I | re.S)
    select_list = (m.group(1) if m else "").strip()
    has_day_projection = bool(re.search(r"\bdate\s*\(\s*timestamp\s*\)\s+as\s+day\b", lowered))
    is_agg = bool(re.search(r"\b(avg|min|max|sum|count)\s*\(", select_list, flags=re.I))
    has_metric_projection = bool(metric and re.search(rf"\b{metric}\b", select_list, flags=re.I))
    if (not has_day_projection) or (has_metric_projection and not is_agg):
        s = re.sub(r"^\s*select\s+.+?\s+from\s", f"SELECT date(timestamp) AS day, AVG({metric}) AS avg_{metric}\nFROM ", s, flags=re.I | re.S)
        if re.search(r"\border\s+by\b", s, flags=re.I):
            s = re.sub(r"order\s+by[\s\S]+$", "ORDER BY day", s, flags=re.I)
        else:
            s = s.rstrip(" ;") + "\nORDER BY day"
        if not s.endswith(";"):
            s += ";"
    return s


def _fix_count_clause(s: str) -> str:
    if re.search(r"\bcount\s*\(\s*\*\s*\)\b", s, flags=re.I):
        s = re.sub(r"\border\s+by[\s\S]+?(?=limit|;|$)", "", s, flags=re.I)
        s = re.sub(r"\blimit\s+\d+\b", "", s, flags=re.I)
    return s


def _ensure_order_and_limit(s: str) -> str:
    lowered = s.lower()
    if re.search(r"\bcount\s*\(\s*\*\s*\)\b", lowered):
        return s if s.endswith(";") else s + ";"
    is_grouped = " group by " in lowered
    has_order = " order by " in lowered
    has_limit = " limit " in lowered
    is_agg = bool(re.search(r"\b(avg|min|max|sum)\s*\(", lowered))
#    if not has_order and not is_agg and not is_grouped:
#        s = s.rstrip(" ;") + "\nORDER BY datetime(timestamp) DESC"
#    if not has_limit and not is_agg and not is_grouped:
#        s += "\nLIMIT 200"
    if not s.endswith(";"):
        s += ";"
    return s


def _metric_from_user_q(user_q: str) -> Tuple[str, str]:
    u = (user_q or "").lower()
    if any(k in u for k in ["spo2", "oxygen", "o2", "saturation"]):
        return "spo2_data", "spo2"
    return "temp_data", "temp"


def postprocess_sql(sql: str, user_q: str) -> str:
    s = _strip_comments_and_first_stmt(sql)
    if not s:
        return ""
    s = _fix_table_column_mismatch(s)
    s = _fix_on_without_join(s)
    s = _ensure_select_from_when_missing(s, user_q)
    s = _apply_one_day_filter_if_requested(s, user_q)
    s = _strip_unrequested_time_filters(s, user_q)
    s = _normalize_metric_columns(s)
    s = _ensure_group_by_if_daily_agg(s)
    s = _coerce_daily_shape_if_needed(s, user_q)
    s = _fix_count_clause(s)
    s = s.strip()
    s = _ensure_order_and_limit(s)
    return s

# =====================
# Prompt assembly
# =====================

def build_system_prompt() -> str:
    return "\n\n".join([
        "You are a careful SQLite assistant.",
        "Goal: Given a user question and the schema, produce ONE safe, read-only SQLite query.",
        "Output format: return ONLY the SQL inside a single fenced block.",
        "Schema:", SCHEMA,
        "Guidance:", GUIDANCE,
    ])

# =====================
# SQL generation
# =====================

def generate_sql_ollama(question: str) -> str:
    system_prompt = build_system_prompt()
    out = ollama_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        num_predict=MAX_TOKENS_SQL,
    )
    sql = extract_sql(out)
    sql = postprocess_sql(sql, question)
    if is_safe_readonly(sql):
        return sql

    tighter = (
        "Return ONLY ONE fenced SQL block with ONE read-only statement. "
        "Do NOT include prose, comments, or multiple statements."
    )
    out2 = ollama_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": tighter + "\n\nUser question:\n" + question},
        ],
        num_predict=MAX_TOKENS_SQL,
        temperature=0.1,
    )
    sql2 = postprocess_sql(extract_sql(out2), question)
    return sql2 if is_safe_readonly(sql2) else ""

# =====================
# Verbalizer (English only)
# =====================

def _render_table_sample(cols: List[str], rows: List[tuple], max_rows: int = 25) -> str:
    if not rows:
        return "(no rows)"
    out = [",".join(cols)]
    for r in rows[:max_rows]:
        out.append(",".join("" if v is None else str(v) for v in r))
    return "\n".join(out)


def verbalize_answer(_unused_model: Any, question: str, cols: List[str], rows: List[tuple]) -> str:
    table_text = _render_table_sample(cols, rows, max_rows=25 if len(rows) <= 50 else 10)
    system = "You are a precise data summarizer. Always answer in English."
    user = (
        f"User question:\n{question}\n\n"
        f"Data (CSV-like):\n{table_text}\n\n"
        "Instructions:\n"
        "- Be brief (≤3 sentences).\n"
        "- If it's a single aggregate value, state it with units if applicable (°C or %).\n"
        "- If it's a list, mention total rows and give 1–2 representative examples with timestamps.\n"
        "- Do NOT invent facts not present in the table."
    )
    try:
        out = ollama_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            num_predict=MAX_TOKENS_SUM,
            temperature=0.2,
        )
        return out.strip()
    except Exception:
        return ""

# =====================
# CLI smoke-test (optional)
# =====================
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="health_data.db")
    args = p.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON;")
    except Exception:
        pass

    print("Chat (Ollama) over temp_data/spo2_data. Ctrl+C to exit.")
    while True:
        try:
            q = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not q:
            continue

        sql = generate_sql_ollama(q)
        if not sql:
            print("Assistant: Failed to produce a safe SQL.")
            continue

        try:
            cols, rows, ms = run_readonly(conn, sql)
        except Exception as e:
            print("SQL error:", e, "\nSQL was:\n", sql)
            continue

        print("\nSQL:\n", sql)
        print(f"Latency: {ms} ms")
        if rows:
            print("Columns:", cols)
            for r in rows[:10]:
                print(r)
            if len(rows) > 10:
                print(f"... (+{len(rows)-10} more)")
        else:
            print("Result: (no rows)")

        print("\nSummary:", verbalize_answer(None, q, cols, rows))

    conn.close()
    
if __name__ == "__main__":
    main()