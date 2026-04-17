function esc(v) {
  return String(v || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fuzzy(q, t) {
  q = (q || "").toLowerCase().trim();
  t = (t || "").toLowerCase();
  if (!q) return true;
  if (t.includes(q)) return true;
  let i = 0;
  for (const c of t) {
    if (c === q[i]) i++;
    if (i === q.length) return true;
  }
  return false;
}

function parseDate(value) {
  if (!value) return null;
  const s = String(value);
  if (s.includes(".")) {
    const parts = s.split(".");
    if (parts.length === 3) {
      const [day, month, year] = parts;
      const d = new Date(year, month - 1, day);
      return isNaN(d.getTime()) ? null : d;
    }
  }
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function renderChips(items, cls = "") {
  return (items || []).map(item => `<span class="chip ${cls}">${esc(item)}</span>`).join("");
}

function shortText(text, n = 180) {
  const raw = String(text || "").replace(/\s+/g, " ").trim();
  if (!raw) return "";
  return esc(raw.slice(0, n)) + (raw.length > n ? "..." : "");
}

function makePdfSnippets(text, query) {
  if (!query) return "";
  const raw = String(text || "");
  const lower = raw.toLowerCase();
  const q = query.toLowerCase();

  let snippets = [];
  let idx = 0;

  while ((idx = lower.indexOf(q, idx)) !== -1 && snippets.length < 8) {
    const start = Math.max(0, idx - 100);
    const end = Math.min(raw.length, idx + q.length + 180);
    let snippet = raw.slice(start, end);
    snippet = esc(snippet);
    const re = new RegExp(query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "ig");
    snippet = snippet.replace(re, m => `<mark>${m}</mark>`);
    snippets.push("..." + snippet + "...");
    idx += q.length;
  }

  return snippets.length ? snippets.join("<br><br>") : "Hakusanalla ei löytynyt osumia.";
}

function leadScore(item) {
  let s = 0;
  if (item.is_new) s += 4;
  if (item.cpv_primary) s += 2;
  if (item.estimated_budget_value) s += 4;
  if (item.deadline_at) s += 4;
  if (item.contract_end_date) s += 4;
  if (item.snippet_image) s += 5;
  if (item.generated_from_attachment) s += 5;
  if (item.extraction_confidence === "korkea") s += 7;
  if (item.extraction_confidence === "keskitaso") s += 3;
  if ((item.signal_tags || []).includes("kilpailutus tulossa")) s += 4;
  if ((item.signal_tags || []).includes("budjetoitu")) s += 4;
  if ((item.signal_tags || []).includes("uusintahankinta")) s += 4;
  return s;
}

async function loadProcurementData() {
  const urls = [
    "./data/procurements.json?v=" + Date.now(),
    "./history/2026/procurements-2026.json?v=" + Date.now()
  ];

  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) continue;
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        return data;
      }
    } catch (e) {
      // fallback seuraavaan
    }
  }

  return [];
}
