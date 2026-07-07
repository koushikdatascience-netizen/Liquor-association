/* Global keyboard shortcut for search */
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    document.querySelector(".header .search input")?.focus();
  }
});
