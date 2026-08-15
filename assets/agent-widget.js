(function () {
  "use strict";

  var STATUS_URL =
    "https://raw.githubusercontent.com/hpnssflw/webpage/agent-data/agent/status.json";

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function fmtCountdown(seconds) {
    if (seconds <= 0) return "due now";
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = Math.floor(seconds % 60);
    return pad(h) + ":" + pad(m) + ":" + pad(s);
  }

  function isStale(status) {
    var updated = new Date(status.updated_at).getTime();
    var staleAfterMs = status.cadence_hours * 2 * 3600 * 1000;
    return Date.now() - updated > staleAfterMs;
  }

  function sparkline(history) {
    var glyphs = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
    if (!history.length) return "";
    var max = 1;
    for (var i = 0; i < history.length; i++) {
      if (history[i].kept > max) max = history[i].kept;
    }
    return history
      .map(function (run) {
        if (run.kept === 0) return '<span class="agent-spark-zero">▁</span>';
        var level = Math.min(glyphs.length - 1, Math.round((run.kept / max) * (glyphs.length - 1)));
        return glyphs[level];
      })
      .join("");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderUnavailable(mount) {
    mount.innerHTML = '<p class="agent-unavailable mono">agent status unavailable</p>';
  }

  function startCountdown(mount, status) {
    var target = mount.querySelector("[data-countdown]");
    if (!target) return;
    var nextRunAt = new Date(status.updated_at).getTime() + status.cadence_hours * 3600 * 1000;
    function tick() {
      var remaining = Math.round((nextRunAt - Date.now()) / 1000);
      target.textContent = "next check " + fmtCountdown(remaining);
    }
    tick();
    setInterval(tick, 1000);
  }

  function renderCompact(mount, status) {
    var stale = isStale(status);
    var dotClass = stale ? "agent-dot-stale" : "agent-dot-online";
    var label = stale ? "stale" : "online";

    var topicsLine = status.topics
      .map(function (t) {
        return (
          escapeHtml(t.name.toLowerCase()) +
          ' <span class="agent-count">' + t.kept + "/" + t.collected + "</span>"
        );
      })
      .join("   ");

    mount.innerHTML =
      '<a class="agent-widget-link" href="researcher/agent.html">' +
      '<span class="' + dotClass + '">●</span> agent ' + label +
      ' <span class="agent-muted">· runs every ' + status.cadence_hours + 'h · streak ' + status.streak + '</span><br>' +
      '<span class="agent-tagline">schema-validated LLM ranking · full audit trail</span><br>' +
      '<span class="agent-spark">' + sparkline(status.run_history) + '</span> <span class="agent-muted">last ' + status.run_history.length + ' runs</span><br>' +
      '<span class="agent-topics">' + topicsLine + '</span><br>' +
      '<span class="agent-muted" data-countdown></span> <span class="agent-arrow">view dashboard →</span>' +
      '</a>';

    startCountdown(mount, status);
  }

  function renderDashboard(mount, status) {
    var stale = isStale(status);
    var dotClass = stale ? "agent-dot-stale" : "agent-dot-online";
    var label = stale ? "stale" : "online";

    var funnelRows = status.topics
      .map(function (t) {
        var f = status.funnel[t.slug];
        return (
          '<div class="agent-funnel-row">' +
          '<span class="agent-funnel-label">' + escapeHtml(t.name.toUpperCase()) + '</span>' +
          '<span class="agent-funnel-counts">collected ' + f.collected +
          ' → in-window ' + f.in_window +
          ' → new ' + f.new +
          ' → kept ' + f.kept + '</span>' +
          '</div>'
        );
      })
      .join("");

    var tickerRows = status.recent_events
      .map(function (e) {
        var verdictClass = e.verdict === "kept" ? "agent-kept" : "agent-drop";
        var verdictLabel = e.verdict === "kept" ? "KEPT" : "DROP";
        var detail = e.verdict === "kept" ? "score " + e.score : e.reason;
        var time = e.ts.slice(11, 19);
        return (
          '<div class="agent-ticker-row">' +
          '<span class="agent-muted">' + time + '</span> ' +
          '<span class="' + verdictClass + '">' + verdictLabel + '</span> ' +
          '<span class="agent-ticker-topic">' + escapeHtml(e.topic) + '</span> ' +
          '<span class="agent-ticker-title">&quot;' + escapeHtml(e.title) + '&quot;</span> ' +
          '<span class="agent-muted">' + escapeHtml(detail) + '</span>' +
          '</div>'
        );
      })
      .join("");

    mount.innerHTML =
      '<div class="agent-dashboard-header">' +
      '<span class="' + dotClass + '">●</span> AGENT ' + label.toUpperCase() +
      ' <span class="agent-muted">runs every ' + status.cadence_hours + 'h · streak ' + status.streak + '</span>' +
      '</div>' +
      '<p class="agent-tagline">Building production AI pipelines: schema-validated LLM calls, automatic fallback, full audit trail of every decision the ranker makes.</p>' +
      '<div class="agent-spark">' + sparkline(status.run_history) + ' <span class="agent-muted">last ' + status.run_history.length + ' runs</span></div>' +
      '<hr class="agent-divider">' +
      '<div class="agent-funnel">' + funnelRows + '</div>' +
      '<hr class="agent-divider">' +
      '<div class="agent-ticker">' + tickerRows + '</div>';

    startCountdown(mount, status);
  }

  function init() {
    var compactMount = document.getElementById("agent-widget");
    var dashboardMount = document.getElementById("agent-dashboard");
    if (!compactMount && !dashboardMount) return;

    fetch(STATUS_URL, { cache: "no-store" })
      .then(function (res) {
        if (!res.ok) throw new Error("status fetch failed: " + res.status);
        return res.json();
      })
      .then(function (status) {
        if (compactMount) renderCompact(compactMount, status);
        if (dashboardMount) renderDashboard(dashboardMount, status);
      })
      .catch(function () {
        if (compactMount) renderUnavailable(compactMount);
        if (dashboardMount) renderUnavailable(dashboardMount);
      });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
