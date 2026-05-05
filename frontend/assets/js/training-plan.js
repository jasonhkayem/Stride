function _completedKey(versionId) {
  return `stride.completedSessions.${versionId}`;
}

function getCompletedSessions(versionId) {
  try {
    return JSON.parse(localStorage.getItem(_completedKey(versionId)) || "{}");
  } catch (_) {
    return {};
  }
}

function markSessionCompleted(versionId, weekIdx, sessionIdx) {
  const completed = getCompletedSessions(versionId);
  completed[`${weekIdx}_${sessionIdx}`] = true;
  localStorage.setItem(_completedKey(versionId), JSON.stringify(completed));
}

function isSessionCompleted(versionId, weekIdx, sessionIdx) {
  return Boolean(getCompletedSessions(versionId)[`${weekIdx}_${sessionIdx}`]);
}

async function renderTrainingPlan() {
  await ensureTrainingPlanLoaded();
  await ensureTrainingTemplatesLoaded();
  await ensureCoachLoaded();
  const currentVersion = getCurrentPlanVersion();
  const planHeader = `
    <section class="section-block">
      <div class="section-header">
        <h3>Plan Builder</h3>
        ${currentVersion
          ? `<div class="d-flex gap-2">
               <button class="btn btn-outline-secondary btn-sm" id="newPlanBtn">New Plan</button>
               <button class="btn btn-dark" id="regenPlanBtn">Regenerate Plan</button>
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
        renderEmptyState(
        "No active plan",
        "No training plan has been generated for this account yet. Use the button above to create one."
      ) +
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
              <button class="btn btn-outline-secondary btn-sm" id="weekPrevBtn" ${state.selectedPlanWeek === 0 ? "disabled" : ""}>&#8592;</button>
              <span class="week-nav-label">Week ${(activeWeek.week || state.selectedPlanWeek + 1)}${activeWeek.phase ? ` — ${escapeHtml(activeWeek.phase)}` : ""}</span>
              <button class="btn btn-outline-secondary btn-sm" id="weekNextBtn" ${state.selectedPlanWeek >= weeks.length - 1 ? "disabled" : ""}>&#8594;</button>
            </div>
            ` : ""}
            <div class="plan-list">
              ${(() => {
                const filtered = sessions.filter(
                  (s) => !((s.type || "").toLowerCase() === "rest") && (s.distance_km || s.duration_min)
                );
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
            </div>
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

function renderPlanSuggestion(suggestion) {
  const actions = suggestion.proposed_actions || [];
  const rationale = suggestion.rationale || "";
  const actionRows = actions
    .map((a) => {
      const params = Object.entries(a)
        .filter(([k]) => k !== "action")
        .map(([k, v]) => `${escapeHtml(String(k))}: ${escapeHtml(String(v))}`)
        .join(", ");
      return `<li><strong>${escapeHtml(a.action)}</strong>${params ? ` — ${params}` : ""}</li>`;
    })
    .join("");
  return `
    <div class="mini-card">
      <p class="mini-title">Coach suggestion</p>
      <p class="text-muted small mb-2">${escapeHtml(rationale)}</p>
      ${actionRows ? `<ul class="small mb-3">${actionRows}</ul>` : ""}
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
          <button class="modal-close" id="planSessionModalClose">&times;</button>
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
  const rows = versions.map((v) => `
    <div class="stat-row">
      <span>v${v.version_number} — ${escapeHtml(formatCreatedBy(v.created_by))}</span>
      <strong>${escapeHtml(formatShortDate(v.created_at))}</strong>
    </div>
  `).join("");
  return `
    <section class="section-block">
      <div class="section-header"><h3>Version History</h3></div>
      <div class="panel-card"><div class="stat-list">${rows}</div></div>
    </section>
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
          <button class="modal-close" id="trainingPlanClose">&times;</button>
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
      window.alert("No training plan templates are available yet. Seed the templates first.");
      return;
    }
    errorEl?.classList.add("d-none");
    renderTemplateSummary();
    modal.classList.add("open");
  };

  const openInRegenMode = () => {
    if (!templates.length) { window.alert("No templates available."); return; }
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
    if (!templates.length) { window.alert("No templates available."); return; }
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
      await ensureTrainingPlanLoaded(true);
      await renderTrainingPlan();
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
    } finally {
      submitBtn.disabled = false;
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
      const filteredSessions = (version?.plan_snapshot?.weeks?.[weekIdx]?.sessions || []).filter(
        (s) => !((s.type || "").toLowerCase() === "rest") && (s.distance_km || s.duration_min)
      );
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
      completeBtn.onclick = () => {
        markSessionCompleted(versionId, weekIdx, sessionIdx);
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