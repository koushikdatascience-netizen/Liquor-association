/* Basic client-side table search */

document.addEventListener("input", (e) => {
  const t = e.target;
  if (!t.matches("[data-table-search]")) return;
  const sel = t.getAttribute("data-table-search");
  const table = document.querySelector(sel);
  if (!table) return;
  const q = t.value.trim().toLowerCase();
  table.querySelectorAll("tbody tr").forEach((row) => {
    row.style.display = row.innerText.toLowerCase().includes(q) ? "" : "none";
  });
});

/* Toggle accordion */
document.addEventListener("click", (e) => {
  const head = e.target.closest(".ac-head");
  if (!head) return;
  head.parentElement.classList.toggle("open");
});

/* Tabs */
document.addEventListener("click", (e) => {
  const tab = e.target.closest(".tabs .tab");
  if (!tab) return;
  const tabs = tab.parentElement;
  tabs.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  tab.classList.add("active");
  const target = tab.getAttribute("data-tab");
  if (target) {
    document.querySelectorAll("[data-tab-panel]").forEach((p) => {
      p.style.display = p.getAttribute("data-tab-panel") === target ? "" : "none";
    });
  }
});
