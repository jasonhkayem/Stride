function renderLogo() {
  return `
    <div class="brand-row">
      <img src="svg/stride-wordmark.svg" alt="Stride" class="brand-logo" />
    </div>
  `;
}

function renderLayout({ active, title, subtitle, content, actions = true }) {
  const adminLink =
    state.platformRole === "super_admin"
      ? `<a class="nav-link ${active === "admin" ? "active" : ""}" href="#/admin">Admin</a>`
      : "";

  return `
    <div class="sidebar-overlay" id="sidebarOverlay"></div>
    <div class="app-layout">
      <aside class="sidebar" id="appSidebar">
        <div>
          ${renderLogo()}
          <nav class="nav-links">
            <a class="nav-link ${active === "dashboard" ? "active" : ""}" href="#/dashboard">Dashboard</a>
            <a class="nav-link ${active === "activities" ? "active" : ""}" href="#/activities">Activities</a>
            <a class="nav-link ${active === "training-plan" ? "active" : ""}" href="#/training-plan">Training Plan</a>
            <a class="nav-link ${active === "coach" ? "active" : ""}" href="#/coach">Coach</a>
            <a class="nav-link ${active === "clubs" ? "active" : ""}" href="#/clubs">Clubs</a>
            <a class="nav-link ${active === "profile" ? "active" : ""}" href="#/profile">Profile</a>
            ${adminLink}
          </nav>
        </div>
        <div class="nav-links">
          <a class="nav-link" id="logoutBtn" href="#">Log out</a>
        </div>
      </aside>

      <div class="main-content">
        <header class="top-bar">
          <div class="top-bar-left">
            <button class="hamburger-btn" id="hamburgerBtn" aria-label="Open menu">&#9776;</button>
            <div>
              <h1 class="page-title">${title}</h1>
              <p class="text-muted">${subtitle}</p>
            </div>
          </div>
          ${
            actions
              ? `
            <div class="quick-actions">
              <button class="btn btn-outline-secondary" id="addActivityBtn">Add Activity</button>
              <button class="btn btn-dark" id="syncStravaBtn">${STRAVA_SVG}Sync Strava</button>
            </div>
          `
              : ""
          }
        </header>

        ${content}
      </div>
    </div>
    ${actions ? renderAddActivityModal() : ""}
    ${renderClubModal()}
    ${renderClubDetailModal()}
    ${renderLeaveClubModal()}
    ${renderCancelRequestModal()}
    ${renderKickMemberModal()}
    ${renderDeleteClubModal()}
    ${renderEventModal()}
    ${renderDeleteSessionModal()}
  `;
}

function renderInfoCard(title, body) {
  return `
    <div class="panel-card">
      <h3>${title}</h3>
      <p class="text-muted">${body}</p>
    </div>
  `;
}

function renderStatusPill(connected) {
  return `
    <span class="status-pill ${connected ? "connected" : "disconnected"}" style="display:inline-flex;align-items:center;gap:4px;">
      ${STRAVA_SVG}${connected ? "Strava connected" : "Strava not connected"}
    </span>
  `;
}

function renderEmptyState(title, body) {
  return `
    <section class="section-block">
      ${renderInfoCard(title, body)}
    </section>
  `;
}

function renderAvatarEl(user, extraClass = "") {
  const url = user?.profile_picture_url;
  const classes = ["profile-avatar", extraClass].filter(Boolean).join(" ");
  if (url) {
    return `<div class="${classes}"><img src="${escapeHtml(API_BASE + url)}" alt="${escapeHtml(user.name || "Avatar")}" /></div>`;
  }
  return `<div class="${classes}"></div>`;
}

function initLayoutActions() {
  const sidebar = document.getElementById("appSidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const hamburger = document.getElementById("hamburgerBtn");

  function openSidebar() {
    sidebar?.classList.add("open");
    overlay?.classList.add("open");
  }
  function closeSidebar() {
    sidebar?.classList.remove("open");
    overlay?.classList.remove("open");
  }

  hamburger?.addEventListener("click", openSidebar);
  overlay?.addEventListener("click", closeSidebar);
  sidebar?.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", closeSidebar);
  });

  const logoutBtn = document.getElementById("logoutBtn");
  logoutBtn?.addEventListener("click", () => {
    clearAuth();
    window.location.hash = "#/login";
  });

  const addActivityBtn = document.getElementById("addActivityBtn");
  addActivityBtn?.addEventListener("click", () => {
    document.getElementById("addActivityModal")?.classList.add("open");
  });

  const syncStravaBtn = document.getElementById("syncStravaBtn");
  if (syncStravaBtn) {
    ensureStravaStatusLoaded()
      .then((status) => {
        syncStravaBtn.innerHTML = `${STRAVA_SVG}${status?.connected ? "Sync Strava" : "Connect Strava"}`;
      })
      .catch(() => {
        syncStravaBtn.innerHTML = `${STRAVA_SVG}Connect Strava`;
      });
  }

  syncStravaBtn?.addEventListener("click", async () => {
    if (!state.userId) return;
    syncStravaBtn.disabled = true;
    try {
      const status = await ensureStravaStatusLoaded(true);
      if (!status?.connected) {
        await connectStravaFlow();
        syncStravaBtn.innerHTML = `${STRAVA_SVG}Sync Strava`;
        showToast("Strava connected successfully.");
        return;
      }

      const result = await apiFetch("/activities/strava/sync", {
        method: "POST",
        body: JSON.stringify({ per_page: 30, page: 1, max_pages: 1 }),
      });
      await ensureActivitiesLoaded(true);
      await ensureStravaStatusLoaded(true);
      const imported = result.imported ?? 0;
      showToast(imported === 0 ? "Already up to date." : `Imported ${imported} new activit${imported === 1 ? "y" : "ies"}.`);
    } catch (error) {
      showToast(`Strava sync failed: ${error.message}`, "error");
    } finally {
      syncStravaBtn.disabled = false;
    }
  });

  attachAddActivityActions();
}

async function handleRoute() {
  const hash = window.location.hash || "";

  if (state.userId && !state.user) {
    try {
      await loadCurrentUser();
    } catch (_error) {
      clearAuth();
    }
  }

  if (protectedRoutes.has(hash) && !state.userId) {
    window.location.hash = "#/login";
    return;
  }

  if ((hash === "#/login" || hash === "#/signup") && state.userId) {
    window.location.hash = "#/dashboard";
    return;
  }

  if (hash === "#/admin" && state.platformRole !== "super_admin") {
    window.location.hash = "#/dashboard";
    return;
  }

  // Show a loading state to prevent blank-content flash during transitions
  if (!app.querySelector(".app-layout")) {
    app.innerHTML = `<div class="route-loading-full"><div class="route-spinner"></div></div>`;
  } else {
    app.classList.add("route-loading");
  }

  try {
    if (hash.startsWith("#/athlete/")) {
      if (!state.userId) {
        window.location.hash = "#/login";
        return;
      }
      const userId = hash.replace("#/athlete/", "").trim();
      await renderPublicProfile(userId);
      return;
    }

    if (hash.startsWith("#/clubs/") && hash.endsWith("/events")) {
      if (!state.userId) {
        window.location.hash = "#/login";
        return;
      }
      const clubId = hash.replace("#/clubs/", "").replace("/events", "").trim();
      await renderClubEvents(clubId);
      return;
    }

    const route = routes[hash];
    if (!route) {
      if (state.userId) {
        app.innerHTML = renderLayout({
          active: "",
          title: "Page not found",
          subtitle: "The page you're looking for doesn't exist.",
          content: renderEmptyState("404 — Not found", "Use the sidebar to navigate."),
        });
        initLayoutActions();
      } else {
        window.location.hash = "#/login";
      }
      return;
    }
    await route();
  } finally {
    app.classList.remove("route-loading");
  }
}