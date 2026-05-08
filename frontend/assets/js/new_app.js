async function renderDashboard() {
  await Promise.all([
    ensureUsersLoaded(),
    ensureActivitiesLoaded(),
    ensureTrainingPlanLoaded(),
    ensureStravaStatusLoaded(),
    ensureActivityLikesLoaded(),
    ensureActivityCommentsLoaded(),
  ]);
  const myActivities = getCurrentUserActivities();
  const weeklyActivities = myActivities.filter((activity) => {
    const timestamp = new Date(activity.timestamp);
    return Date.now() - timestamp.getTime() <= 7 * 24 * 60 * 60 * 1000;
  });

  const weeklyDistance = weeklyActivities.reduce((sum, activity) => sum + (activity.distance || 0), 0);
  const sessionsCompleted = weeklyActivities.length;
  const currentVersion = getCurrentPlanVersion();
  const planSessions = currentVersion?.plan_snapshot?.weeks?.[0]?.sessions || [];
  const nextSession = planSessions[0]?.type
    ? formatSessionType(planSessions[0].type)
    : "Next session pending";

  const recentActivities = myActivities.slice(0, 3);
  const isNewUser = myActivities.length === 0;

  const onboardingSection = isNewUser ? `
    <section class="section-block">
      <div class="section-header">
        <h3>Get started</h3>
      </div>
      <div class="onboarding-grid">
        <div class="onboarding-card">
          <div class="onboarding-icon">🏃</div>
          <h4>Log your first activity</h4>
          <p class="text-muted">Add a workout manually or connect Strava to import your runs, rides and swims.</p>
          <button class="btn btn-dark onboarding-add-btn">Add activity</button>
        </div>
        <div class="onboarding-card">
          <div class="onboarding-icon">⚡</div>
          <h4>Connect Strava</h4>
          <p class="text-muted">Sync your training history automatically and keep your stats up to date.</p>
          <button class="btn btn-outline-secondary onboarding-strava-btn">${STRAVA_SVG}${state.stravaStatus?.connected ? "Sync Strava" : "Connect Strava"}</button>
        </div>
        <div class="onboarding-card">
          <div class="onboarding-icon">📋</div>
          <h4>Create a training plan</h4>
          <p class="text-muted">Let the AI coach build a personalised plan based on your goals and fitness level.</p>
          <a class="btn btn-outline-secondary" href="#/training-plan">View plans</a>
        </div>
      </div>
    </section>
  ` : `
    <section class="section-block">
      <div class="page-grid">
        <div>
          <div class="section-header">
            <h3>Recent activity</h3>
            <a href="#/activities">View all</a>
          </div>
          <div class="activity-feed">${recentActivities.map((activity) => renderApiActivityCard(activity)).join("")}</div>
        </div>
        <aside class="panel-card">
          <h3 style="margin:0 0 16px">Weekly distance</h3>
          <canvas id="weeklyDistanceChart" height="180"></canvas>
        </aside>
      </div>
    </section>
  `;

  app.innerHTML = renderLayout({
    active: "dashboard",
    title: "Dashboard",
    subtitle: `Welcome back, ${escapeHtml(state.user?.name || "athlete")}. ${renderStatusPill(
      !!state.stravaStatus?.connected
    )}`,
    content: `
      <section class="kpi-grid">
        <div class="kpi-card">
          <p class="kpi-label">Weekly distance</p>
          <h2>${weeklyDistance.toFixed(1)} km</h2>
          <span class="kpi-meta">${sessionsCompleted} sessions in the last 7 days</span>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Sessions</p>
          <h2>${sessionsCompleted}</h2>
          <span class="kpi-meta">Recent workouts completed</span>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Plan status</p>
          <h2>${currentVersion ? "Active" : "No plan"}</h2>
          <span class="kpi-meta">${escapeHtml(nextSession)}</span>
        </div>
        ${state.user?.weekly_goal_km ? `
        <div class="kpi-card">
          <p class="kpi-label">Weekly goal</p>
          <h2>${weeklyDistance.toFixed(1)} <span style="font-size:16px;font-weight:400">/ ${state.user.weekly_goal_km} km</span></h2>
          <div class="goal-progress">
            <div class="goal-progress-bar" style="width:${Math.min(100, (weeklyDistance / state.user.weekly_goal_km) * 100).toFixed(1)}%"></div>
          </div>
          <span class="kpi-meta">${Math.min(100, Math.round((weeklyDistance / state.user.weekly_goal_km) * 100))}% of weekly target</span>
        </div>` : ""}
      </section>

      ${onboardingSection}

      ${renderActivityModal()}
    `,
  });

  initLayoutActions();
  attachActivityCardHandlers();
  if (!isNewUser) {
    renderWeeklyDistanceChart(myActivities);
    initActivityMaps();
  }

  document.querySelector(".onboarding-add-btn")?.addEventListener("click", () => {
    document.getElementById("addActivityModal")?.classList.add("open");
  });
  document.querySelector(".onboarding-strava-btn")?.addEventListener("click", () => {
    document.getElementById("syncStravaBtn")?.click();
  });
}

async function renderAdmin() {
  if (state.platformRole !== "super_admin") {
    app.innerHTML = renderLayout({
      active: "admin",
      title: "Admin",
      subtitle: "Restricted area.",
      actions: false,
      content: renderEmptyState("Access denied", "This account is not a super admin."),
    });
    initLayoutActions();
    return;
  }

  await Promise.all([ensureAdminLoaded(), ensureUsersLoaded(), ensureClubsLoaded()]);
  const overview = state.adminOverview || {};
  const totals = overview.totals || {};
  const userRows = state.adminUsers?.items || state.adminUsers?.results || [];

  let kickLogs = [];
  try { kickLogs = await apiFetch("/admin/kick_logs"); } catch (err) { showToast(`Could not load kick logs: ${err.message}`, "error"); }

  app.innerHTML = renderLayout({
    active: "admin",
    title: "Admin",
    subtitle: "Your platform at a glance — users, sessions, and activity in real time.",
    actions: false,
    content: `
      <section class="section-block">
        <div class="kpi-grid">
          <div class="kpi-card">
            <p class="kpi-label">Total users</p>
            <h2>${totals.users ?? 0}</h2>
            <span class="kpi-meta">All-time registrations</span>
          </div>
          <div class="kpi-card">
            <p class="kpi-label">Chat sessions</p>
            <h2>${totals.chatbot_sessions ?? 0}</h2>
            <span class="kpi-meta">All-time sessions</span>
          </div>
          <div class="kpi-card">
            <p class="kpi-label">Activities</p>
            <h2>${totals.activities ?? 0}</h2>
            <span class="kpi-meta">Tracked workouts</span>
          </div>
        </div>
      </section>

      <section class="section-block">
        <div class="section-header">
          <h3>User Oversight</h3>
          <span class="tag">Live data</span>
        </div>
        <div class="panel-card">
          <table class="admin-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              ${
                userRows.length
                  ? userRows
                      .map(
                        (row) => `
                    <tr>
                      <td>${escapeHtml(row.name || row.username || "User")}</td>
                      <td>${escapeHtml(row.email || "--")}</td>
                      <td>${escapeHtml(row.platform_role || "user")}</td>
                      <td>${escapeHtml(formatShortDate(row.created_at))}</td>
                    </tr>
                  `
                      )
                      .join("")
                  : `
                    <tr>
                      <td colspan="4">No admin user rows returned yet.</td>
                    </tr>
                  `
              }
            </tbody>
          </table>
        </div>
      </section>

      ${kickLogs.length ? `
      <section class="section-block">
        <div class="section-header">
          <h3>Member Removals</h3>
          <span class="tag">${kickLogs.length} logged</span>
        </div>
        <div class="panel-card">
          <table class="admin-table">
            <thead>
              <tr><th>Member</th><th>Removed by</th><th>Club</th><th>Reason</th><th>Date</th></tr>
            </thead>
            <tbody>
              ${kickLogs.map((log) => `
                <tr>
                  <td>${escapeHtml(state.usersById[log.kicked_user_id]?.name || "User")}</td>
                  <td>${escapeHtml(state.usersById[log.kicked_by]?.name || "Admin")}</td>
                  <td>${escapeHtml(state.clubs?.find((c) => c.club_id === log.club_id)?.name || "Club")}</td>
                  <td>${escapeHtml(log.reason || "—")}</td>
                  <td>${escapeHtml(formatShortDate(log.created_at))}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </section>
      ` : ""}
    `,
  });

  initLayoutActions();
}

const routes = {
  "": renderLogin,
  "#/login": renderLogin,
  "#/signup": renderSignup,
  "#/dashboard": renderDashboard,
  "#/activities": renderActivities,
  "#/training-plan": renderTrainingPlan,
  "#/coach": renderCoach,
  "#/profile": renderProfile,
  "#/clubs": renderClubs,
  "#/admin": renderAdmin,
};

window.addEventListener("hashchange", () => {
  handleRoute().catch((error) => {
    app.innerHTML = renderEmptyState("Something went wrong", error.message);
  });
});

window.addEventListener("load", () => {
  handleRoute().catch((error) => {
    app.innerHTML = renderEmptyState("Something went wrong", error.message);
  });
});