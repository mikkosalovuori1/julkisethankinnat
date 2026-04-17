<!DOCTYPE html>
<html lang="fi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <title>HankintaSeuranta</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div class="page">
    <div class="topbar">
      <div class="brand">
        <div class="brand-mark"></div>
        <div>
          <h1>HankintaSeuranta</h1>
          <p>Elegantti näkymä julkisiin hankintoihin</p>
        </div>
      </div>

      <div class="nav">
        <a href="attachment_extractions.html">Liitepoiminnat</a>
        <a href="best_findings.html">Parhaat löydökset</a>
        <a href="contracts.html">Sopimukset</a>
        <a href="agent.html">Agentti</a>
      </div>
    </div>

    <div class="hero">
      <div class="card">
        <h2 class="hero-title">Löydä oikeat julkiset hankinnat nopeammin.</h2>
        <div class="hero-sub">
          Selkeä, kevyt ja hienovarainen käyttöliittymä hankintojen selaamiseen, suodattamiseen ja arviointiin. Näet tärkeimmät löydökset, osumakuvat liitteistä ja olennaiset signaalit yhdellä silmäyksellä.
        </div>

        <div class="quick-stats" id="quickStats">
          <div class="stat">
            <div class="stat-label">Hankintoja</div>
            <div class="stat-value">-</div>
          </div>
          <div class="stat">
            <div class="stat-label">Liitepoimintoja</div>
            <div class="stat-value">-</div>
          </div>
          <div class="stat">
            <div class="stat-label">Korkea luottamus</div>
            <div class="stat-value">-</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="section-head" style="margin-top:0;">
          <div>
            <h2>Pikareitit</h2>
            <p>Siirry suoraan tärkeimpiin näkymiin</p>
          </div>
        </div>

        <div class="mini-list">
          <div class="mini-item">
            <h4><a href="best_findings.html">Parhaat löydökset</a></h4>
            <p>Korkean luottamuksen liitepoiminnat ja parhaat liidit.</p>
          </div>
          <div class="mini-item">
            <h4><a href="attachment_extractions.html">Liitepoiminnat</a></h4>
            <p>OCR- ja liitepoiminnat yhdestä näkymästä.</p>
          </div>
          <div class="mini-item">
            <h4><a href="agent.html">Agentti</a></h4>
            <p>Hae termeillä, profiileilla ja loogisilla hauilla.</p>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="section-head" style="margin-top:0;">
        <div>
          <h2>Haku</h2>
          <p>Suodata hankintoja sisällön, teeman, signaalin ja ajan mukaan</p>
        </div>
      </div>

      <div class="filters">
        <input id="q" class="input" placeholder="Sanahaku" />
        <input id="entity" class="input" placeholder="Hankintayksikkö" />
        <input id="area" class="input" placeholder="Alue" />
        <input id="cpv" class="input" placeholder="CPV-koodi" />

        <select id="themeFilter" class="select">
          <option value="">Kaikki teemat</option>
        </select>

        <select id="signalFilter" class="select">
          <option value="">Kaikki signaalit</option>
        </select>

        <select id="type" class="select">
          <option value="">Kaikki tilat</option>
          <option>budjetti</option>
          <option>investointipäätös</option>
          <option>hankintasuunnitelma</option>
          <option>hankintakalenteritieto</option>
          <option>käynnissä oleva hankinta</option>
          <option>mennyt kilpailutus</option>
          <option>sopimus päättymässä</option>
          <option>poimittu hankinta</option>
          <option>muu hankintatieto</option>
        </select>

        <input id="fromDate" class="input" type="date" />
        <input id="toDate" class="input" type="date" />

        <select id="highConfidenceOnly" class="select">
          <option value="">Kaikki luottamusasteet</option>
          <option value="korkea">Vain korkea</option>
          <option value="keskitaso">Vain keskitaso</option>
          <option value="matala">Vain matala</option>
        </select>

        <button id="searchBtn" class="button">Näytä tulokset</button>
      </div>
    </div>

    <div class="section-head">
      <div>
        <h2>Tulokset</h2>
        <p id="resultMeta">Ladataan hankintoja…</p>
      </div>
    </div>

    <div id="results" class="results-grid"></div>
  </div>

  <script src="ui.js"></script>
  <script>
    fetch('./data/procurements.json?v=' + Date.now())
      .then(r => r.json())
      .then(data => {
        const q = document.getElementById('q');
        const entity = document.getElementById('entity');
        const area = document.getElementById('area');
        const cpv = document.getElementById('cpv');
        const type = document.getElementById('type');
        const themeFilter = document.getElementById('themeFilter');
        const signalFilter = document.getElementById('signalFilter');
        const fromDate = document.getElementById('fromDate');
        const toDate = document.getElementById('toDate');
        const highConfidenceOnly = document.getElementById('highConfidenceOnly');
        const searchBtn = document.getElementById('searchBtn');
        const results = document.getElementById('results');
        const resultMeta = document.getElementById('resultMeta');
        const quickStats = document.getElementById('quickStats');

        const themes = [...new Set(data.flatMap(x => x.theme_tags || []).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fi'));
        const signals = [...new Set(data.flatMap(x => x.signal_tags || []).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'fi'));

        themeFilter.innerHTML = `<option value="">Kaikki teemat</option>` + themes.map(t => `<option value="${esc(t)}">${esc(t)}</option>`).join("");
        signalFilter.innerHTML = `<option value="">Kaikki signaalit</option>` + signals.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join("");

        const total = data.length;
        const attachmentExtractions = data.filter(x => x.generated_from_attachment === true).length;
        const highConfidence = data.filter(x => x.extraction_confidence === "korkea").length;

        quickStats.innerHTML = `
          <div class="stat">
            <div class="stat-label">Hankintoja</div>
            <div class="stat-value">${total}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Liitepoimintoja</div>
            <div class="stat-value">${attachmentExtractions}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Korkea luottamus</div>
            <div class="stat-value">${highConfidence}</div>
          </div>
        `;

        function render() {
          const filtered = data.filter(item => {
            const text = item.search_text || "";

            if (q.value && !fuzzy(q.value, text)) return false;
            if (entity.value && !String(item.entity || "").toLowerCase().includes(entity.value.toLowerCase())) return false;
            if (area.value && !String(item.area || "").toLowerCase().includes(area.value.toLowerCase())) return false;
            if (cpv.value && !String(item.cpv_primary || "").includes(cpv.value)) return false;
            if (type.value && item.item_type !== type.value) return false;
            if (themeFilter.value && !(item.theme_tags || []).includes(themeFilter.value)) return false;
            if (signalFilter.value && !(item.signal_tags || []).includes(signalFilter.value)) return false;
            if (highConfidenceOnly.value && String(item.extraction_confidence || "") !== highConfidenceOnly.value) return false;

            const d = parseDate(item.published_at || item.found_at);
            const fromD = parseDate(fromDate.value);
            const toD = parseDate(toDate.value);
            if (fromD && d && d < fromD) return false;
            if (toD && d && d > toD) return false;
            if ((fromD || toD) && !d) return false;

            return true;
          }).sort((a, b) => leadScore(b) - leadScore(a));

          resultMeta.textContent = `${filtered.length} tulosta`;

          if (!filtered.length) {
            results.innerHTML = `<div class="card empty-state">Ei tuloksia nykyisillä suodattimilla.</div>`;
            return;
          }

          results.innerHTML = filtered.map(item => `
            <article class="proc-card">
              <div class="proc-top">
                <div>
                  <div class="proc-org">${esc(item.entity)} · ${esc(item.area || "-")}</div>
                  <h3 class="proc-title">${esc(item.title)}</h3>
                </div>
                <div class="chips">
                  ${item.generated_from_attachment ? `<span class="chip warn">Liitepoiminta</span>` : ""}
                  ${item.extraction_confidence === "korkea" ? `<span class="chip success">Korkea</span>` : ""}
                  ${item.deadline_at ? `<span class="chip info">${esc(item.deadline_at)}</span>` : ""}
                </div>
              </div>

              <div class="proc-summary">${shortText(item.ai_summary || item.pdf_text || "", 220)}</div>

              <div class="chips">
                ${(item.cpv_primary || item.cpv_label) ? `<span class="chip">${esc(item.cpv_primary)} ${esc(item.cpv_label || "")}</span>` : ""}
                ${renderChips((item.theme_tags || []).slice(0,3), "theme")}
                ${renderChips((item.signal_tags || []).slice(0,3), "signal")}
              </div>

              <div class="proc-footer">
                <div class="proc-meta">
                  ${item.estimated_budget_value ? `Arvioitu arvo: ${esc(item.estimated_budget_value)}<br>` : ""}
                  ${esc(item.published_at || item.found_at || "-")}
                </div>

                <div class="proc-actions">
                  <a class="btn-inline" href="detail.html?id=${encodeURIComponent(item.id || item.url)}">Avaa</a>
                  ${item.document_url ? `<a class="btn-inline secondary" href="${esc(item.document_url)}" target="_blank">Liite</a>` : ""}
                </div>
              </div>
            </article>
          `).join("");
        }

        searchBtn.onclick = render;
        render();
      });
  </script>
</body>
</html>
