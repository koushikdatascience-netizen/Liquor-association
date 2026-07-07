/* Basic client-side table search and filters */

function applyTableControls(tableSelector) {
  const table = document.querySelector(tableSelector);
  if (!table) return;

  const searches = document.querySelectorAll(`[data-table-search="${tableSelector}"]`);
  const filters = document.querySelectorAll(`[data-table-filter="${tableSelector}"]`);
  const query = Array.from(searches)
    .map((input) => input.value.trim().toLowerCase())
    .filter(Boolean)
    .join(" ");

  table.querySelectorAll("tbody tr").forEach((row) => {
    const rowText = row.innerText.toLowerCase();
    const matchesSearch = !query || rowText.includes(query);
    const matchesFilters = Array.from(filters).every((filter) => {
      const value = filter.value.trim().toLowerCase();
      if (!value) return true;
      const column = filter.getAttribute("data-filter-column");
      if (!column) return rowText.includes(value);
      const cell = row.children[Number(column)];
      return cell ? cell.innerText.toLowerCase().includes(value) : true;
    });
    row.style.display = matchesSearch && matchesFilters ? "" : "none";
  });
}

document.addEventListener("input", (e) => {
  const target = e.target;
  const tableSelector = target.getAttribute("data-table-search");
  if (tableSelector) applyTableControls(tableSelector);
});

document.addEventListener("change", (e) => {
  const target = e.target;
  const tableSelector = target.getAttribute("data-table-filter");
  if (tableSelector) applyTableControls(tableSelector);
});

document.addEventListener("click", (e) => {
  const reset = e.target.closest("[data-table-reset]");
  if (!reset) return;
  const tableSelector = reset.getAttribute("data-table-reset");
  document.querySelectorAll(`[data-table-search="${tableSelector}"], [data-table-filter="${tableSelector}"]`).forEach((control) => {
    control.value = "";
  });
  applyTableControls(tableSelector);
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
