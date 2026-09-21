function renderLocalTimes() {
  document.querySelectorAll("time[datetime]").forEach((node) => {
    const when = new Date(node.dateTime);
    if (Number.isNaN(when.getTime())) {
      return;
    }
    const date = when.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    const clock = when.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
    node.textContent = `${date} ${clock}`;
  });
}

renderLocalTimes();
