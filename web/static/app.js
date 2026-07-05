document.getElementById("refreshBtn")?.addEventListener("click", async () => {
  const btn = document.getElementById("refreshBtn");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  try {
    const res = await fetch("/api/report/refresh", { method: "POST" });
    if (res.ok) location.reload();
    else alert("Refresh failed");
  } catch {
    alert("Network error");
  } finally {
    btn.disabled = false;
    btn.textContent = "↻ Refresh Analysis";
  }
});

setInterval(() => {
  const el = document.getElementById("clock");
  if (el) el.textContent = new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC";
}, 30000);
