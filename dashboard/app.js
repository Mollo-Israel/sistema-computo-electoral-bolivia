const REFRESH_MS = 10000;
const PARTY_NAMES = {
  partido_1: "Partido 1",
  partido_2: "Partido 2",
  partido_3: "Partido 3",
  partido_4: "Partido 4",
};

async function fetchData(path) {
  const separator = path.includes("?") ? "&" : "?";
  const url = `${path}${separator}_ts=${Date.now()}`;
  const response = await fetch(url, {
    cache: "no-store",
    headers: {
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  });

  if (!response.ok) {
    throw new Error(`No se pudo cargar ${path}: ${response.status}`);
  }

  const payload = await response.json();
  return payload.data;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("es-BO");
}

function formatPercent(value) {
  return `${Number(value || 0).toLocaleString("es-BO", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}%`;
}

function formatSigned(value) {
  const numericValue = Number(value || 0);
  const sign = numericValue > 0 ? "+" : "";
  return `${sign}${formatNumber(numericValue)}`;
}

function getWinner(summary) {
  const entries = Object.entries(summary.votos_por_partido || {});
  if (!entries.length) {
    return null;
  }

  const sorted = entries.sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0));
  const [winnerKey, winnerVotes] = sorted[0];
  return {
    key: winnerKey,
    label: PARTY_NAMES[winnerKey] || winnerKey,
    votes: Number(winnerVotes || 0),
    percentage: summary.porcentaje_por_partido?.[winnerKey] ?? 0,
  };
}

function renderHeroInsight(summary, states, comparison) {
  const winner = getWinner(summary);
  const published = states.PUBLICADA?.oficial ?? 0;
  const observed = states.OBSERVADA?.oficial ?? 0;
  const differences = (comparison || []).filter((row) => Number(row.diferencia || 0) !== 0).length;

  document.getElementById("refresh-status").textContent = new Date().toLocaleTimeString("es-BO", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const heroInsight = document.getElementById("hero-insight");
  if (!winner) {
    heroInsight.innerHTML = `
      <span class="mini-label">Lectura general</span>
      <strong>Sin datos consolidados</strong>
      <p>El panel mostrará aquí el liderazgo, margen y estado del flujo oficial.</p>
    `;
    document.getElementById("winner-pill").textContent = "Sin datos";
    return;
  }

  document.getElementById("winner-pill").textContent = `${winner.label} lidera`;
  heroInsight.innerHTML = `
    <span class="mini-label">Lectura general</span>
    <strong>${winner.label} encabeza con ${formatPercent(winner.percentage)}</strong>
    <p>
      Margen estimado: <strong>${formatNumber(summary.margen_victoria)}</strong> votos.
      Publicadas: <strong>${formatNumber(published)}</strong>.
      Observadas: <strong>${formatNumber(observed)}</strong>.
      Diferencias detectadas: <strong>${formatNumber(differences)}</strong>.
    </p>
  `;
}

function renderSummary(summary) {
  const cards = [
    {
      label: "Mesas oficiales",
      value: formatNumber(summary.total_mesas),
      foot: "Base oficial consolidada",
    },
    {
      label: "Mesas procesadas",
      value: formatNumber(summary.mesas_procesadas),
      foot: "Aceptadas u observadas",
    },
    {
      label: "Participación",
      value: formatPercent(summary.participacion_porcentaje),
      foot: "Emitidos sobre habilitados",
    },
    {
      label: "Votos válidos",
      value: formatNumber(summary.votos_validos),
      foot: "Conteo computable",
    },
    {
      label: "Votos blancos",
      value: formatNumber(summary.votos_blancos),
      foot: "Boletas sin preferencia",
    },
    {
      label: "Votos nulos",
      value: formatNumber(summary.votos_nulos),
      foot: "Actas con marcas inválidas",
    },
  ];

  document.getElementById("summary-cards").innerHTML = cards.map((card) => `
    <article class="summary-card">
      <span class="summary-label">${card.label}</span>
      <strong class="summary-value">${card.value}</strong>
      <span class="summary-foot">${card.foot}</span>
    </article>
  `).join("");

  const parties = Object.entries(summary.votos_por_partido || {});
  const max = Math.max(...parties.map(([, votes]) => Number(votes || 0)), 1);
  document.getElementById("party-chart").innerHTML = parties
    .sort((a, b) => Number(b[1] || 0) - Number(a[1] || 0))
    .map(([party, votes]) => `
      <div class="bar-row">
        <div class="bar-head">
          <span>${PARTY_NAMES[party] || party}</span>
          <span>${formatNumber(votes)} (${formatPercent(summary.porcentaje_por_partido?.[party])})</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${(Number(votes || 0) / max) * 100}%"></div>
        </div>
      </div>
    `)
    .join("");
}

function renderStates(states) {
  const entries = Object.entries(states || {});
  document.getElementById("states-grid").innerHTML = entries.map(([state, values]) => `
    <article class="state-pill">
      <div class="muted">${state}</div>
      <strong>Oficial: ${formatNumber(values.oficial)}</strong><br>
      <strong>RRV: ${formatNumber(values.rrv)}</strong>
    </article>
  `).join("");
}

function renderComparison(rows) {
  const sortedRows = [...(rows || [])]
    .sort((a, b) => Math.abs(Number(b.diferencia || 0)) - Math.abs(Number(a.diferencia || 0)));
  const visibleRows = sortedRows.slice(0, 50);
  const differentRows = sortedRows.filter((row) => Number(row.diferencia || 0) !== 0).length;

  document.getElementById("comparison-meta").textContent =
    `${formatNumber(differentRows)} mesas con diferencia distinta de cero`;

  document.getElementById("comparison-body").innerHTML = visibleRows.map((row) => `
    <tr>
      <td>${row.mesa_codigo}</td>
      <td>${row.departamento || "-"}</td>
      <td>${row.rrv_votos_validos ?? "-"}</td>
      <td>${row.oficial_votos_validos ?? "-"}</td>
      <td>${row.diferencia == null ? "-" : formatSigned(row.diferencia)}</td>
    </tr>
  `).join("");
}

function renderGeography(rows) {
  const sortedRows = [...(rows || [])].sort((a, b) => Number(b.votos_emitidos || 0) - Number(a.votos_emitidos || 0));
  const topRows = sortedRows.slice(0, 3);

  document.getElementById("geo-cards").innerHTML = topRows.map((row) => `
    <article class="geo-card">
      <span class="muted">${row.clave}</span>
      <strong>${formatNumber(row.votos_emitidos)}</strong>
      <span class="summary-foot">${formatNumber(row.actas)} actas procesadas</span>
    </article>
  `).join("");

  document.getElementById("geo-body").innerHTML = sortedRows.slice(0, 20).map((row) => `
    <tr>
      <td>${row.clave}</td>
      <td>${formatNumber(row.actas)}</td>
      <td>${formatNumber(row.votos_emitidos)}</td>
      <td>${formatNumber(row.votos_validos)}</td>
    </tr>
  `).join("");
}

function renderTechnical(metrics) {
  document.getElementById("technical-metrics").innerHTML = Object.entries(metrics || {}).map(([key, value]) => `
    <div class="metric-item">
      <span>${key}</span>
      <strong>${typeof value === "number" ? formatNumber(value) : value}</strong>
    </div>
  `).join("");
}

function renderAnomalies(rows) {
  const anomalies = rows || [];
  document.getElementById("anomaly-meta").textContent =
    anomalies.length ? `${formatNumber(anomalies.length)} registros observados` : "Sin observaciones";

  document.getElementById("anomalies-list").innerHTML = anomalies.slice(0, 40).map((row) => `
    <li><strong>${row.fuente}</strong> · ${row.mesa_codigo} · ${row.estado}<br>${row.descripcion}</li>
  `).join("");
}

async function loadDashboard() {
  const [summary, states, comparison, geography, technical, anomalies] = await Promise.all([
    fetchData("/api/dashboard/resumen"),
    fetchData("/api/dashboard/estados"),
    fetchData("/api/dashboard/comparacion"),
    fetchData("/api/dashboard/geografia"),
    fetchData("/api/dashboard/tecnico"),
    fetchData("/api/dashboard/anomalias"),
  ]);

  renderHeroInsight(summary, states, comparison);
  renderSummary(summary);
  renderStates(states);
  renderComparison(comparison);
  renderGeography(geography);
  renderTechnical(technical);
  renderAnomalies(anomalies);
}

async function refreshDashboard() {
  try {
    await loadDashboard();
    const existingError = document.getElementById("dashboard-error");
    if (existingError) {
      existingError.remove();
    }
  } catch (error) {
    console.error(error);
    if (!document.getElementById("dashboard-error")) {
      document.body.insertAdjacentHTML(
        "beforeend",
        `<p id="dashboard-error" style="padding:16px;color:#b91c1c">No se pudo cargar el dashboard.</p>`,
      );
    }
  }
}

refreshDashboard();
setInterval(refreshDashboard, REFRESH_MS);
