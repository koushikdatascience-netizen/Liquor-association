/* Modal + Toast helpers */

function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}
function closeModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

document.addEventListener("click", (e) => {
  const t = e.target;
  if (t.matches("[data-open-modal]")) openModal(t.getAttribute("data-open-modal"));
  if (t.matches("[data-close-modal]") || t.matches(".modal-backdrop")) {
    const back = t.closest(".modal-backdrop");
    if (back) back.classList.remove("open");
  }
});

function toast(message, type = "") {
  let host = document.querySelector(".toast-host");
  if (!host) {
    host = document.createElement("div");
    host.className = "toast-host";
    document.body.appendChild(host);
  }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<i class="bi bi-check-circle"></i><span>${message}</span>`;
  host.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}
