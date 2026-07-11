/* ============================================================
   Shared Sidebar + Header injector
   Add data-page="dashboard" on <body> to mark the active nav item.
   ============================================================ */

const NAV_ITEMS = [
  { section: "Overview" },
  { key: "dashboard",     label: "Dashboard",            icon: "bi-grid-1x2",         href: "dashboard.html" },
  { key: "applications",  label: "Applications",         icon: "bi-file-earmark-text",href: "applications.html" },
  { key: "payments",      label: "Payment Verification", icon: "bi-cash-coin",        href: "payments.html" },
  { section: "Members" },
  { key: "members",       label: "Members",              icon: "bi-people",           href: "members.html" },
  { key: "cards",         label: "Membership Cards",     icon: "bi-card-heading",     href: "membership-card.html" },
  { key: "notifications", label: "Notifications",        icon: "bi-megaphone",        href: "notifications.html" },
  { section: "Insights" },
  { key: "reports",       label: "Reports",              icon: "bi-bar-chart",        href: "reports.html" },
  { key: "masters",       label: "Masters",              icon: "bi-sliders",          href: "masters.html" },
  { section: "Account" },
  { key: "settings",      label: "Settings",             icon: "bi-gear",             href: "settings.html" },
  { key: "profile",       label: "My Profile",           icon: "bi-person-circle",    href: "profile.html" },
  { key: "logout",        label: "Logout",               icon: "bi-box-arrow-right",  href: "#" },
];

function renderSidebar(activeKey) {
  const items = NAV_ITEMS.map((it) => {
    if (it.section) {
      return `<div class="sidebar__section">${it.section}</div>`;
    }
    const isActive = it.key === activeKey ? " active" : "";
    return `<a class="nav-item${isActive}" href="${it.href}" data-key="${it.key}">
      <i class="bi ${it.icon}"></i><span>${it.label}</span>
    </a>`;
  }).join("");

  return `
    <aside class="sidebar">
      <div class="sidebar__brand">
        <div class="sidebar__logo">L</div>
        <div class="sidebar__brand-text">
          <div class="name">WB Foreign Liquor and IML Licensees</div>
          <div class="sub">Admin Console</div>
        </div>
      </div>
      <nav class="sidebar__nav">${items}</nav>
      <div class="sidebar__footer">
        <div class="avatar">RA</div>
        <div class="meta">
          <div class="n">Rahul Admin</div>
          <div class="r">Super Admin</div>
        </div>
      </div>
    </aside>
  `;
}

function renderHeader(pageTitle, crumbs = []) {
  const crumbHtml = crumbs.map((c, i) => {
    const sep = i > 0 ? `<i class="bi bi-chevron-right sep"></i>` : "";
    const el = c.href
      ? `<a class="crumb" href="${c.href}">${c.label}</a>`
      : `<span class="crumb">${c.label}</span>`;
    return `${sep}${el}`;
  }).join("");

  return `
    <header class="header">
      <div class="header__left">
        <button class="icon-btn" id="sidebarToggle" aria-label="Toggle sidebar">
          <i class="bi bi-list"></i>
        </button>
        <div class="breadcrumb">
          ${crumbHtml}
          ${crumbs.length ? `<i class="bi bi-chevron-right sep"></i>` : ""}
          <span class="page-title">${pageTitle}</span>
        </div>
      </div>
      <div class="header__right">
        <div class="search">
          <i class="bi bi-search"></i>
          <input type="text" placeholder="Search members, applications…" />
          <span class="kbd">⌘K</span>
        </div>
        <button class="icon-btn bell" aria-label="Notifications">
          <i class="bi bi-bell"></i><span class="dot"></span>
        </button>
        <button class="icon-btn" aria-label="Settings">
          <i class="bi bi-gear"></i>
        </button>
        <div class="avatar" style="width:36px;height:36px;">RA</div>
      </div>
    </header>
  `;
}

function mountShell({ page, title, crumbs = [] }) {
  const app = document.getElementById("app");
  if (!app) return;
  const mainInner = app.innerHTML;
  app.innerHTML = `
    ${renderSidebar(page)}
    <div class="main">
      ${renderHeader(title, crumbs)}
      <div class="content">${mainInner}</div>
    </div>
  `;

  document.getElementById("sidebarToggle")?.addEventListener("click", () => {
    if (window.innerWidth <= 900) {
      app.classList.toggle("mobile-open");
    } else {
      app.classList.toggle("collapsed");
    }
  });
}
