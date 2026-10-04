(function () {
  const buttons = Array.from(document.querySelectorAll(".chore"));
  const status = document.querySelector(".chore-status");
  if (!buttons.length || !status) return;

  const pending = sessionStorage.getItem("sbm-chore-note");
  if (pending) {
    status.textContent = pending;
    sessionStorage.removeItem("sbm-chore-note");
  }

  function noteFor(kind, body) {
    if (kind === "refresh") {
      const nfl = body.nfl_games ?? 0;
      const cfb = body.cfb_games ?? 0;
      return `Wrote ${nfl} NFL and ${cfb} CFB games for ${body.season}.`;
    }
    const n = body.settled ?? 0;
    if (n === 0) return "No open tickets were ready to settle.";
    if (n === 1) return "Settled 1 ticket.";
    return `Settled ${n} tickets.`;
  }

  function workingCopy(kind) {
    if (kind === "refresh") return "Refreshing 2026 scores…";
    return "Settling journal…";
  }

  async function run(button) {
    const kind = button.dataset.chore;
    buttons.forEach((item) => {
      item.disabled = true;
    });
    status.textContent = workingCopy(kind);
    try {
      const resp = await fetch(button.dataset.url, { method: "POST" });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = body.detail;
        status.textContent = typeof detail === "string" ? detail : "That did not finish.";
        buttons.forEach((item) => {
          item.disabled = false;
        });
        return;
      }
      sessionStorage.setItem("sbm-chore-note", noteFor(kind, body));
      window.location.reload();
    } catch (_err) {
      status.textContent = "Could not reach the server.";
      buttons.forEach((item) => {
        item.disabled = false;
      });
    }
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      run(button);
    });
  });
})();
