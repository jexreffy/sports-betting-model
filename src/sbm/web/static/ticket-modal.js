function ticketModal() {
  return document.getElementById("ticket-modal");
}

function ticketForm() {
  return document.getElementById("ticket-modal-form");
}

function setField(form, name, value) {
  const el = form.elements.namedItem(name);
  if (!el) return;
  el.value = value == null || value === undefined ? "" : String(value);
}

window.openTicketModal = function openTicketModal(prefill) {
  const modal = ticketModal();
  const form = ticketForm();
  if (!modal || !form) return;
  const data = prefill || {};
  setField(form, "sportsbook", data.sportsbook || "Novig");
  setField(form, "stake_dollars", data.stake_dollars || "");
  setField(form, "american_odds", data.american_odds);
  setField(form, "implied_prob", data.implied_prob);
  setField(form, "kind", data.kind || "straight");
  setField(form, "league", data.league || "nfl");
  setField(form, "season", data.season);
  setField(form, "week", data.week || 1);
  setField(form, "team_or_side", data.team_or_side || "");
  setField(form, "opponent", data.opponent || "");
  setField(form, "market", data.market || "moneyline");
  setField(form, "side", data.side || "");
  setField(form, "market_line", data.market_line);
  setField(form, "game_id", data.game_id || "");
  setField(form, "notes", data.notes || "");
  if (typeof modal.showModal === "function") {
    modal.showModal();
  } else {
    modal.setAttribute("open", "");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const modal = ticketModal();
  const form = ticketForm();
  const cancel = document.getElementById("ticket-modal-cancel");
  if (cancel && modal) {
    cancel.addEventListener("click", () => {
      if (typeof modal.close === "function") modal.close();
      else modal.removeAttribute("open");
    });
  }
  if (!form) return;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const implied = data.get("implied_prob");
    const american = data.get("american_odds");
    const line = data.get("market_line");
    const market = data.get("market");
    const side = data.get("side");
    const payload = {
      sportsbook: data.get("sportsbook"),
      stake_dollars: Number(data.get("stake_dollars")),
      american_odds: american ? Number(american) : null,
      implied_prob: implied ? Number(implied) : null,
      kind: data.get("kind"),
      season: Number(data.get("season")),
      notes: data.get("notes") || null,
      legs: [{
        league: data.get("league"),
        season: Number(data.get("season")),
        week: Number(data.get("week") || 1),
        team_or_side: data.get("team_or_side"),
        opponent: data.get("opponent") || null,
        market: market || null,
        side: side || null,
        market_line: line ? Number(line) : null,
        game_id: data.get("game_id") || null,
      }],
    };
    const resp = await fetch("/api/journal/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      window.alert(await resp.text());
      return;
    }
    window.location.href = "/journal";
  });
});
