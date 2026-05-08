function _filterRunnableSessions(sessions) {
  return (sessions || []).filter((s) => {
    const type = (s.type || "").toLowerCase();
    if (type === "rest") return false;
    if (type === "race") return true;
    return !!(s.distance_km || s.duration_min);
  });
}

function getOverallProgress(snapshot, versionId) {
  let total = 0;
  let completed = 0;
  (snapshot.weeks || []).forEach((week, weekIdx) => {
    _filterRunnableSessions(week.sessions).forEach((_, sessionIdx) => {
      total++;
      if (isSessionCompleted(versionId, weekIdx, sessionIdx)) completed++;
    });
  });
  return { total, completed };
}

function getWeekProgress(snapshot, versionId, weekIdx) {
  let total = 0;
  let completed = 0;
  _filterRunnableSessions((snapshot.weeks || [])[weekIdx]?.sessions).forEach((_, sessionIdx) => {
    total++;
    if (isSessionCompleted(versionId, weekIdx, sessionIdx)) completed++;
  });
  return { total, completed };
}

function isSessionCompleted(versionId, weekIdx, sessionIdx) {
  const key = `${versionId}_${weekIdx}_${sessionIdx}`;
  return Boolean(state.completedPlanSessionsMap[key]);
}

async function markSessionCompleted(versionId, weekIdx, sessionIdx) {
  const result = await apiFetch("/completed_plan_sessions", {
    method: "POST",
    body: JSON.stringify({ version_id: versionId, week_index: weekIdx, session_index: sessionIdx }),
  });
  const key = `${versionId}_${weekIdx}_${sessionIdx}`;
  if (!state.completedPlanSessionsMap[key]) {
    state.completedPlanSessions.push(result);
    state.completedPlanSessionsMap[key] = result;
  }
}

async function renderTrainingPlan() {
  await ensureTrainingPlanLoaded();
  await ensureTrainingTemplatesLoaded();
  await ensureCoachLoaded();
  const currentVersion = getCurrentPlanVersion();
  if (currentVersion) await ensureCompletedPlanSessionsLoaded(currentVersion.version_id);
  const planHeader = `
    <section class="section-block">
      <div class="section-header">
        <h3>Plan Builder</h3>
        ${currentVersion
          ? `<div class="d-flex gap-2">
               <button class="btn btn-outline-secondary btn-sm" id="newPlanBtn">New Plan</button>
               <button class="btn btn-dark" id="regenPlanBtn">Regenerate Plan</button>
               <button class="btn btn-outline-danger btn-sm" id="abandonPlanBtn">Delete Plan</button>
             </div>`
          : `<button class="btn btn-dark" id="createPlanBtn">Create Plan</button>`}
      </div>
    </section>
  `;

  if (!currentVersion) {
    app.innerHTML = renderLayout({
      active: "training-plan",
      title: "Training Plan",
      subtitle: "Your personalized training plan.",
      content:
        planHeader +
        `<section class="section-block">
          <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:64px 24px;max-width:480px;margin:0 auto">
            <div style="font-size:48px;margin-bottom:16px">📋</div>
            <h3 style="margin-bottom:8px">No active training plan</h3>
            <p class="text-muted" style="margin-bottom:24px">Let the AI coach build a personalised plan based on your goals and fitness level.</p>
            <button class="btn btn-dark" id="createPlanCtaBtn">Create Training Plan</button>
          </div>
        </section>` +
        renderTrainingPlanModal(),
    });
    initLayoutActions();
    attachTrainingPlanActions();
    return;
  }

  const snapshot = currentVersion.plan_snapshot || {};
  const weeks = snapshot.weeks || [];
  if (state.selectedPlanWeek === undefined || state.selectedPlanWeek >= weeks.length) {
    state.selectedPlanWeek = 0;
  }
  const activeWeek = weeks[state.selectedPlanWeek] || {};
  const sessions = activeWeek.sessions || [];
  const weekProgress = getWeekProgress(snapshot, currentVersion.version_id, state.selectedPlanWeek);
  const overallProgress = getOverallProgress(snapshot, currentVersion.version_id);
  const weekPct = weekProgress.total ? Math.round((weekProgress.completed / weekProgress.total) * 100) : 0;
  const overallPct = overallProgress.total ? Math.round((overallProgress.completed / overallProgress.total) * 100) : 0;
  const actions = (state.trainingPlan.actions || []).filter(
    (action) => action.version_id === currentVersion.version_id
  );

  app.innerHTML = renderLayout({
    active: "training-plan",
    title: "Training Plan",
    subtitle: "Your personalized training plan.",
    content: `
      ${planHeader}
      <section class="section-block">
        <div class="page-grid">
          <div class="panel-card">
            <div class="section-header">
              <h3>${escapeHtml(formatGoalRace(snapshot.goal_race) || "Training Plan")}</h3>
              <span class="tag">Version ${currentVersion.version_number}</span>
            </div>
            ${snapshot.plan_overview ? `<p class="text-muted small mt-1">${escapeHtml(snapshot.plan_overview)}</p>` : ""}
            ${weeks.length > 1 ? `
            <div class="week-nav">
              <button class="btn btn-outline-secondary btn-sm" id="weekPrevBtn" aria-label="Previous week" ${state.selectedPlanWeek === 0 ? "disabled" : ""}>&#8592;</button>
              <span class="week-nav-label">Week ${(activeWeek.week || state.selectedPlanWeek + 1)}${activeWeek.phase ? ` — ${escapeHtml(activeWeek.phase)}` : ""}</span>
              <button class="btn btn-outline-secondary btn-sm" id="weekNextBtn" aria-label="Next week" ${state.selectedPlanWeek >= weeks.length - 1 ? "disabled" : ""}>&#8594;</button>
            </div>
            ` : ""}
            ${weekProgress.total > 0 ? `
            <div style="margin: 8px 0 4px">
              <div class="progress-track" style="margin: 0 0 4px">
                <div class="progress-bar" style="width:${weekPct}%"></div>
              </div>
              <span style="font-size:12px;color:var(--text-muted)">${weekProgress.completed} / ${weekProgress.total} sessions completed this week</span>
            </div>
            ` : ""}
            <div class="plan-list">
              ${(() => {
                const filtered = _filterRunnableSessions(sessions);
                return filtered.length
                  ? filtered
                      .map((session, index) =>
                        renderPlanItem(
                          session.day || `Day ${index + 1}`,
                          formatSessionType(session.type),
                          `${session.distance_km ?? "--"} km · ${session.duration_min ?? "--"} min`,
                          "Upcoming",
                          state.selectedPlanWeek,
                          index,
                          currentVersion.version_id,
                          session.type === "interval" ? (session.notes || null) : null
                        )
                      )
                      .join("")
                  : renderPlanItem("Plan", "No structured sessions yet", "Snapshot loaded without week sessions", "Upcoming");
              })()}
            </div>
          </div>

          <aside class="panel-card">
            <h3>Plan Summary</h3>
            <div class="stat-list">
              <div class="stat-row">
                <span>Goal race</span>
                <strong>${escapeHtml(formatGoalRace(snapshot.goal_race))}</strong>
              </div>
              <div class="stat-row">
                <span>Goal time</span>
                <strong>${escapeHtml(snapshot.goal_time || "--")}</strong>
              </div>
              <div class="stat-row">
                <span>Weeks in snapshot</span>
                <strong>${snapshot.duration_weeks || weeks.length || 0}</strong>
              </div>
              <div class="stat-row">
                <span>Runs per week</span>
                <strong>${snapshot.min_runs_per_week || "--"}</strong>
              </div>
              <div class="stat-row">
                <span>Created by</span>
                <strong>${escapeHtml(formatCreatedBy(currentVersion.created_by))}</strong>
              </div>
              ${overallProgress.total > 0 ? `
              <div class="stat-row">
                <span>Overall progress</span>
                <strong>${overallProgress.completed} / ${overallProgress.total} sessions</strong>
              </div>
              ` : ""}
            </div>
            ${overallProgress.total > 0 ? `
            <div class="progress-track">
              <div class="progress-bar" style="width:${overallPct}%"></div>
            </div>
            <p style="font-size:12px;color:var(--text-muted);margin:-8px 0 8px">${overallPct}% complete</p>
            ` : ""}
            ${currentVersion.change_summary && currentVersion.version_number > 1 ? `
            <div class="mini-card">
              <p class="mini-title">Change Summary</p>
              <p class="mini-body">${escapeHtml(currentVersion.change_summary)}</p>
            </div>` : ""}
          </aside>
        </div>
      </section>

      ${
        actions.length
          ? `
        <section class="section-block">
          <div class="section-header">
            <h3>Suggested Actions</h3>
          </div>
          <div class="suggested-actions-list">
            ${actions
              .map(
                (action) => {
                  const params = Object.entries(action.parameters || {})
                    .map(([k, v]) => `${escapeHtml(String(k))}: ${escapeHtml(String(v))}`)
                    .join(" · ");
                  return `
              <div class="suggested-action-item">
                <span class="action-label">${escapeHtml(formatActionLabel(action.action_type))}</span>
                ${params ? `<span class="text-muted small action-params">${params}</span>` : ""}
              </div>
            `;
                }
              )
              .join("")}
          </div>
        </section>
      `
          : ""
      }

      ${renderVersionHistorySection(state.trainingPlan)}
      ${renderAbandonPlanModal()}
      ${renderTrainingPlanModal()}
      ${renderPlanSessionModal()}
    `,
  });

  initLayoutActions();
  attachTrainingPlanActions();
}

function renderPlanItem(day, title, detail, status, weekIdx, sessionIdx, versionId, notes) {
  const completed = versionId != null && isSessionCompleted(versionId, weekIdx, sessionIdx);
  const completedClass = completed ? " plan-item--completed" : "";
  const dataAttrs = versionId != null
    ? `data-plan-week="${weekIdx}" data-plan-session="${sessionIdx}" data-plan-version="${escapeHtml(String(versionId))}"`
    : "";
  return `
    <div class="plan-item${completedClass}" ${dataAttrs} style="${versionId != null ? "cursor:pointer" : ""}">
      <div class="plan-day">${escapeHtml(day)}</div>
      <div class="plan-details">
        <p class="plan-title">${escapeHtml(title)}</p>
        <span class="text-muted">${escapeHtml(detail)}</span>
        ${notes ? `<span class="text-muted small d-block mt-1">${escapeHtml(notes)}</span>` : ""}
      </div>
      <span class="plan-status ${completed ? "done" : String(status).toLowerCase()}">${escapeHtml(completed ? "Done" : status)}</span>
    </div>
  `;
}

function formatGoalRace(value) {
  const mapping = {
    "5k": "5K",
    "10k": "10K",
    half_marathon: "Half Marathon",
    marathon: "Marathon",
  };
  return mapping[value] || value || "--";
}

function formatSessionType(value) {
  const mapping = {
    easy_run: "Easy Run",
    tempo: "Tempo Run",
    long_run: "Long Run",
    interval: "Intervals",
    rest: "Rest",
    cross_train: "Cross Train",
    race: "Race",
  };
  return mapping[value] || (value ? value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Session");
}

function formatActionLabel(value) {
  const s = value ? value.replace(/_/g, " ") : "action";
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatCreatedBy(value) {
  if (!value) return "--";
  if (value === "ai") return "AI Coach";
  if (value === "system") return "System";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function _describePlanAction(a) {
  const scope = a.scope === "next_week" ? " next week" : a.scope === "current_week" ? " this week" : "";
  switch (a.action) {
    case "adjust_intensity": {
      const pct = Number(a.intensity_adjustment) || 0;
      const dir = pct >= 0 ? "Increase" : "Decrease";
      return `**${dir} intensity by ${Math.abs(pct)}%**${scope}`;
    }
    case "adjust_volume": {
      const pct = Number(a.percentage) || 0;
      const dir = pct >= 0 ? "Increase" : "Decrease";
      return `**${dir} training volume by ${Math.abs(pct)}%**${scope}`;
    }
    case "insert_rest_day":
      return `**Insert a rest day**${scope}`;
    case "reschedule_session":
      return `**Reschedule session**${scope}`;
    default:
      return `**${a.action.replace(/_/g, " ")}**${scope}`;
  }
}

function renderPlanSuggestion(suggestion) {
  const actions = suggestion.proposed_actions || [];
  const rationale = suggestion.rationale || "";
  const actionLines = actions.map((a) => `- ${_describePlanAction(a)}`).join("\n");
  const md = rationale + (actionLines ? "\n\n" + actionLines : "");
  const contentHtml = typeof marked !== "undefined"
    ? DOMPurify.sanitize(marked.parse(md))
    : `<p>${escapeHtml(md)}</p>`;
  return `
    <div class="mini-card">
      <p class="mini-title">Coach suggestion</p>
      <div class="coach-md small mb-3">${contentHtml}</div>
      <div class="d-flex gap-2">
        <button class="btn btn-dark btn-sm approve-btn">Apply changes</button>
        <button class="btn btn-outline-secondary btn-sm decline-btn">Decline</button>
      </div>
    </div>
  `;
}

function renderPlanSessionModal() {
  return `
    <div class="modal-overlay" id="planSessionModal">
      <div class="modal-card plan-session-modal-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta" id="planSessionModalDay"></p>
            <h2 class="modal-title" id="planSessionModalTitle"></h2>
          </div>
          <button class="modal-close" id="planSessionModalClose" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <p class="text-muted" id="planSessionModalDetail"></p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="planSessionModalCancel">Close</button>
          <button class="btn btn-dark" id="planSessionModalComplete">Mark as completed</button>
        </div>
      </div>
    </div>
  `;
}

function renderVersionHistorySection(plan) {
  const versions = (plan?.versions || []).slice().sort((a, b) => b.version_number - a.version_number);
  if (versions.length < 2) return "";
  const currentVersionId = String(plan?.current_version_id || "");
  const rows = versions.map((v) => {
    const isCurrent = String(v.version_id) === currentVersionId;
    return `
    <div class="stat-row">
      <span>v${v.version_number} — ${escapeHtml(formatCreatedBy(v.created_by))}</span>
      <span style="display:flex;align-items:center;gap:8px">
        <strong>${escapeHtml(formatShortDate(v.created_at))}</strong>
        ${isCurrent
          ? `<span style="font-size:11px;padding:2px 7px;border-radius:10px;background:#e9fbe9;color:#16a34a;font-weight:600">Current</span>`
          : `<button class="btn btn-outline-secondary btn-sm restore-version-btn" style="padding:2px 10px;font-size:12px" data-version-id="${escapeHtml(String(v.version_id))}">Restore</button>`
        }
      </span>
    </div>
  `;
  }).join("");
  return `
    <section class="section-block">
      <div class="section-header"><h3>Version History</h3></div>
      <div class="panel-card"><div class="stat-list">${rows}</div></div>
    </section>
  `;
}

function renderAbandonPlanModal() {
  return `
    <div class="modal-overlay" id="abandonPlanModal">
      <div class="modal-card" style="max-width:420px">
        <div class="modal-header">
          <div>
            <p class="modal-meta">Danger Zone</p>
            <h2 class="modal-title">Delete Training Plan</h2>
          </div>
          <button class="modal-close" id="abandonPlanClose" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <p>This will permanently delete your current training plan and all version history. This action cannot be undone.</p>
          <div class="inline-error d-none mt-3" id="abandonPlanError"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="abandonPlanCancel">Cancel</button>
          <button class="btn btn-danger" id="abandonPlanConfirm">Delete Plan</button>
        </div>
      </div>
    </div>
  `;
}

function renderTrainingPlanModal() {
  const options = (state.trainingTemplates || [])
    .map(
      (template) => `
        <option value="${template.template_id}">
          ${escapeHtml(formatGoalRace(template.goal_race))} - ${template.duration_weeks} weeks
        </option>
      `
    )
    .join("");

  return `
    <div class="modal-overlay" id="trainingPlanModal">
      <div class="modal-card plan-modal-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta">Plan Builder</p>
            <h2 class="modal-title">Create your training plan</h2>
          </div>
          <button class="modal-close" id="trainingPlanClose" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="plan-form-grid">
            <div>
              <label class="form-label">Goal race</label>
              <select class="form-select" id="planTemplateSelect">
                ${options || '<option value="">No templates available</option>'}
              </select>
            </div>
            <div>
              <label class="form-label">Goal time</label>
              <input class="form-control" id="planGoalTime" placeholder="55:00 or 04:00:00" />
            </div>
          </div>
          <div class="mini-card mt-3" id="planTemplateSummary">
            <p class="mini-title">Template overview</p>
            <p class="mini-body">Choose a goal race to see the current template details.</p>
          </div>
          <div class="mini-card mt-3 d-none" id="planResetWarning">
            <p class="mini-body text-warning">This will delete your current plan and version history. A new plan starting at version 1 will be created.</p>
          </div>
          <div class="inline-error mt-3 d-none" id="planCreateError"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="planCancelBtn">Cancel</button>
          <button class="btn btn-dark" id="planSubmitBtn">Generate Plan</button>
        </div>
      </div>
    </div>
  `;
}

async function attachTrainingPlanActions() {
  document.getElementById("weekPrevBtn")?.addEventListener("click", async () => {
    if (state.selectedPlanWeek > 0) {
      state.selectedPlanWeek -= 1;
      await renderTrainingPlan();
    }
  });
  document.getElementById("weekNextBtn")?.addEventListener("click", async () => {
    const weeks = getCurrentPlanVersion()?.plan_snapshot?.weeks || [];
    if (state.selectedPlanWeek < weeks.length - 1) {
      state.selectedPlanWeek += 1;
      await renderTrainingPlan();
    }
  });

  document.querySelectorAll(".restore-version-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const versionId = btn.dataset.versionId;
      const userPlanId = state.trainingPlan?.user_plan_id;
      if (!userPlanId || !versionId) return;
      btn.disabled = true;
      try {
        await apiFetch(`/user_training_plans/${userPlanId}`, {
          method: "PATCH",
          body: JSON.stringify({ current_version_id: versionId }),
        });
        await ensureTrainingPlanLoaded(true);
        showToast("Plan version restored.");
        await renderTrainingPlan();
      } catch (err) {
        showToast(`Could not restore version: ${err.message}`, "error");
        btn.disabled = false;
      }
    });
  });

  const abandonBtn = document.getElementById("abandonPlanBtn");
  const abandonModal = document.getElementById("abandonPlanModal");
  const abandonClose = document.getElementById("abandonPlanClose");
  const abandonCancel = document.getElementById("abandonPlanCancel");
  const abandonConfirm = document.getElementById("abandonPlanConfirm");
  const abandonError = document.getElementById("abandonPlanError");

  if (abandonBtn && abandonModal) {
    const openAbandon = () => {
      if (abandonError) { abandonError.textContent = ""; abandonError.classList.add("d-none"); }
      if (abandonConfirm) abandonConfirm.disabled = false;
      abandonModal.classList.add("open");
    };
    const closeAbandon = () => abandonModal.classList.remove("open");
    abandonBtn.addEventListener("click", openAbandon);
    abandonClose?.addEventListener("click", closeAbandon);
    abandonCancel?.addEventListener("click", closeAbandon);
    abandonModal.addEventListener("click", (e) => { if (e.target === abandonModal) closeAbandon(); });
    abandonConfirm?.addEventListener("click", async () => {
      const userPlanId = state.trainingPlan?.user_plan_id;
      if (!userPlanId) return;
      abandonConfirm.disabled = true;
      try {
        await apiFetch(`/user_training_plans/${userPlanId}`, { method: "DELETE" });
        state.trainingPlan = null;
        closeAbandon();
        await ensureTrainingPlanLoaded(true);
        showToast("Training plan deleted.");
        await renderTrainingPlan();
      } catch (err) {
        if (abandonError) {
          abandonError.textContent = err.message;
          abandonError.classList.remove("d-none");
        }
        abandonConfirm.disabled = false;
      }
    });
  }

  const createPlanBtn = document.getElementById("createPlanBtn");
  const regenPlanBtn = document.getElementById("regenPlanBtn");
  const newPlanBtn = document.getElementById("newPlanBtn");
  const modal = document.getElementById("trainingPlanModal");
  const closeBtn = document.getElementById("trainingPlanClose");
  const cancelBtn = document.getElementById("planCancelBtn");
  const submitBtn = document.getElementById("planSubmitBtn");
  const templateSelect = document.getElementById("planTemplateSelect");
  const goalTimeInput = document.getElementById("planGoalTime");
  const summaryEl = document.getElementById("planTemplateSummary");
  const errorEl = document.getElementById("planCreateError");
  const resetWarningEl = document.getElementById("planResetWarning");

  if (!modal) return;
  if (!createPlanBtn && !regenPlanBtn) return;

  let isNewPlanMode = false;
  const templates = state.trainingTemplates || [];

  const findSelectedTemplate = () =>
    templates.find((t) => t.template_id === templateSelect?.value) || templates[0] || null;

  const renderTemplateSummary = () => {
    const template = findSelectedTemplate();
    if (!template || !summaryEl) return;
    const suggestedGoalTime =
      String(template.goal_race).toLowerCase() === "marathon" ? "04:00:00" : "55:00";
    if (!goalTimeInput.value) goalTimeInput.value = suggestedGoalTime;
    summaryEl.innerHTML = `
      <p class="mini-title">${escapeHtml(formatGoalRace(template.goal_race))} template</p>
      <p class="mini-body">
        ${escapeHtml((template.structure || {}).description || "Structured training block")}<br />
        Duration: ${template.duration_weeks} weeks<br />
        Minimum runs per week: ${(template.structure || {}).min_runs_per_week || "--"}
      </p>
    `;
  };

  const closeModal = () => {
    modal.classList.remove("open");
    errorEl?.classList.add("d-none");
    resetWarningEl?.classList.add("d-none");
    if (templateSelect) templateSelect.disabled = false;
  };

  const openModal = () => {
    if (!templates.length) {
      showToast("No training plan templates are available yet. Seed the templates first.", "error");
      return;
    }
    errorEl?.classList.add("d-none");
    renderTemplateSummary();
    modal.classList.add("open");
  };

  const openInRegenMode = () => {
    if (!templates.length) { showToast("No training plan templates available.", "error"); return; }
    isNewPlanMode = false;
    const snapshot = getCurrentPlanVersion()?.plan_snapshot || {};
    const matchingTemplate = templates.find((t) => t.goal_race === snapshot.goal_race);
    if (templateSelect) {
      if (matchingTemplate) templateSelect.value = matchingTemplate.template_id;
      templateSelect.disabled = true;
    }
    if (goalTimeInput && snapshot.goal_time) goalTimeInput.value = snapshot.goal_time;
    document.querySelector("#trainingPlanModal .modal-title").textContent = "Regenerate Plan";
    resetWarningEl?.classList.add("d-none");
    errorEl?.classList.add("d-none");
    renderTemplateSummary();
    modal.classList.add("open");
  };

  const openInNewPlanMode = () => {
    if (!templates.length) { showToast("No training plan templates available.", "error"); return; }
    isNewPlanMode = true;
    if (templateSelect) {
      templateSelect.disabled = false;
      templateSelect.value = templates[0]?.template_id || "";
    }
    if (goalTimeInput) goalTimeInput.value = "";
    document.querySelector("#trainingPlanModal .modal-title").textContent = "Create New Plan";
    resetWarningEl?.classList.remove("d-none");
    errorEl?.classList.add("d-none");
    renderTemplateSummary();
    modal.classList.add("open");
  };

  createPlanBtn?.addEventListener("click", openModal);
  document.getElementById("createPlanCtaBtn")?.addEventListener("click", openModal);
  regenPlanBtn?.addEventListener("click", openInRegenMode);
  newPlanBtn?.addEventListener("click", openInNewPlanMode);
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
  templateSelect?.addEventListener("change", () => {
    goalTimeInput.value = "";
    renderTemplateSummary();
  });

  submitBtn?.addEventListener("click", async () => {
    const template = findSelectedTemplate();
    if (!template) {
      errorEl.textContent = "Please choose a template.";
      errorEl.classList.remove("d-none");
      return;
    }
    const goalTime = goalTimeInput.value.trim();
    if (!goalTime) {
      errorEl.textContent = "Goal time is required.";
      errorEl.classList.remove("d-none");
      return;
    }
    if (!/^\d{1,2}:\d{2}(:\d{2})?$/.test(goalTime)) {
      errorEl.textContent = "Goal time must be in MM:SS or HH:MM:SS format (e.g. 55:00 or 04:00:00).";
      errorEl.classList.remove("d-none");
      return;
    }

    submitBtn.disabled = true;
    const originalLabel = submitBtn.textContent;
    submitBtn.textContent = "Generating…";
    try {
      let userPlanId = state.trainingPlan?.user_plan_id || null;
      if (!userPlanId) {
        const createdPlan = await apiFetch("/user_training_plans", {
          method: "POST",
          body: JSON.stringify({
            user_id: state.userId,
            template_id: template.template_id,
            current_version_id: null,
            start_date: new Date().toISOString().slice(0, 10),
          }),
        });
        userPlanId = createdPlan.user_plan_id;
      }

      await apiFetch("/training_plan_versions/generate_from_template", {
        method: "POST",
        body: JSON.stringify({
          user_plan_id: userPlanId,
          template_id: template.template_id,
          goal_time: goalTime,
          ...(isNewPlanMode ? { reset: true } : {}),
        }),
      });

      closeModal();
      state.trainingPlan = null;
      await ensureTrainingPlanLoaded(true);
      showToast("Training plan generated.");
      await renderTrainingPlan();
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
      submitBtn.disabled = false;
      submitBtn.textContent = originalLabel;
    }
  });

  renderTemplateSummary();

  // Plan session click → detail modal
  const sessionModal = document.getElementById("planSessionModal");
  document.querySelectorAll(".plan-item[data-plan-week]").forEach((item) => {
    item.addEventListener("click", () => {
      const weekIdx = parseInt(item.dataset.planWeek, 10);
      const sessionIdx = parseInt(item.dataset.planSession, 10);
      const versionId = item.dataset.planVersion;
      const version = getCurrentPlanVersion();
      const filteredSessions = _filterRunnableSessions(version?.plan_snapshot?.weeks?.[weekIdx]?.sessions);
      const session = filteredSessions[sessionIdx];
      if (!session) return;

      document.getElementById("planSessionModalDay").textContent = session.day || `Day ${sessionIdx + 1}`;
      document.getElementById("planSessionModalTitle").textContent = formatSessionType(session.type);
      document.getElementById("planSessionModalDetail").textContent =
        `${session.distance_km ?? "--"} km · ${session.duration_min ?? "--"} min${session.notes ? " · " + session.notes : ""}`;

      const completeBtn = document.getElementById("planSessionModalComplete");
      const alreadyDone = isSessionCompleted(versionId, weekIdx, sessionIdx);
      completeBtn.textContent = alreadyDone ? "Completed ✓" : "Mark as completed";
      completeBtn.disabled = alreadyDone;
      completeBtn.onclick = async () => {
        completeBtn.disabled = true;
        try {
          await markSessionCompleted(versionId, weekIdx, sessionIdx);
        } catch (err) {
          showToast(`Could not save progress: ${err.message}`, "error");
          completeBtn.disabled = false;
          return;
        }
        sessionModal.classList.remove("open");
        renderTrainingPlan();
      };

      sessionModal.classList.add("open");
    });
  });

  document.getElementById("planSessionModalClose")?.addEventListener("click", () => {
    document.getElementById("planSessionModal")?.classList.remove("open");
  });
  document.getElementById("planSessionModalCancel")?.addEventListener("click", () => {
    document.getElementById("planSessionModal")?.classList.remove("open");
  });
  document.getElementById("planSessionModal")?.addEventListener("click", (e) => {
    if (e.target === document.getElementById("planSessionModal"))
      document.getElementById("planSessionModal").classList.remove("open");
  });
}