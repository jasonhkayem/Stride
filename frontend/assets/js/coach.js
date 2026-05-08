function getSessionTitle(chatbotId, createdAt) {
  const stored = localStorage.getItem(`stride.sessionTitle.${chatbotId}`);
  if (stored) return stored;
  return formatShortDate(createdAt);
}

function saveSessionTitle(chatbotId, title) {
  const text = (title || "").trim();
  if (text) localStorage.setItem(`stride.sessionTitle.${chatbotId}`, text);
}

async function renderCoach() {
  await Promise.all([ensureCoachLoaded(), ensureTrainingPlanLoaded()]);
  const messages = normalizeCoachMessages(state.coachMessages);
  const isExpanded = messages.length > 0;
  const messageHtml = messages.length
    ? messages.map((message) => renderCoachMessage(message)).join("")
    : `
      <div class="message coach">
        <p class="message-meta">Coach - just now</p>
        <p>Start the conversation with how training is feeling today.</p>
      </div>
    `;

  const activeSession = state.coachSessions.find((s) => s.chatbot_id === state.coachSessionId);
  const relatedActivityId = activeSession?.related_activity_id ?? null;
  const relatedActivity = relatedActivityId
    ? (state.activities || []).find((a) => String(a.activity_id) === String(relatedActivityId))
    : null;
  const activityBannerHtml = relatedActivityId
    ? `<div style="padding:8px 12px;margin-bottom:8px;border-radius:10px;background:#f1f5f9;border:1px solid #e2e8f0;font-size:12px;color:var(--text-muted);display:flex;align-items:center;gap:6px">
        <span>Activity context:</span>
        <strong style="color:var(--text-primary)">${relatedActivity
          ? `${escapeHtml(formatActivityType(relatedActivity.activity_type))} &middot; ${escapeHtml(formatShortDate(relatedActivity.timestamp))}${relatedActivity.distance ? ` &middot; ${escapeHtml(formatDistance(relatedActivity.distance))}` : ""}`
          : "Linked activity"
        }</strong>
      </div>`
    : "";

  const sessionListHtml = state.coachSessions
    .map(
      (s) => `
      <div class="coach-session-row">
        <button class="coach-session-item ${s.chatbot_id === state.coachSessionId ? "active" : ""}" data-session-id="${escapeHtml(s.chatbot_id)}">
          <span class="coach-session-label">${escapeHtml(getSessionTitle(s.chatbot_id, s.created_at))}</span>
          <span class="coach-session-time">${escapeHtml(formatTimeAgo(s.created_at))}</span>
        </button>
        <button class="coach-session-delete" data-session-id="${escapeHtml(s.chatbot_id)}" title="Delete session" aria-label="Delete session">&times;</button>
      </div>
    `
    )
    .join("");

  app.innerHTML = renderLayout({
    active: "coach",
    title: "Coach",
    subtitle: "Talk through your training, recovery, and next steps.",
    actions: false,
    content: `
      <div class="coach-layout">
        <aside class="coach-sessions-sidebar">
          <button class="btn btn-dark btn-sm coach-new-btn" id="coachNewBtn">+ New chat</button>
          <div class="coach-session-list" id="coachSessionList">
            ${sessionListHtml}
          </div>
        </aside>

        <div class="coach-main">
          <section class="section-block" style="margin-top:0">
            <div class="coach-center ${isExpanded ? "expanded" : ""}" id="coachCenter">
              <div class="panel-card coach-thread">
                ${activityBannerHtml}
                <div id="coachMessages" class="coach-message-list">${messageHtml}</div>
                <div class="message-input">
                  <input type="text" class="form-control" id="coachInput" placeholder="Share how you feel..." />
                  ${getCurrentPlanVersion()
                    ? `<button class="btn btn-outline-secondary" id="coachAdjustPlanBtn">Adjust plan</button>`
                    : `<a class="btn btn-outline-secondary coach-no-plan-link" href="#/training-plan" style="font-size:13px;white-space:nowrap">Create a plan</a>`}
                  <button class="btn btn-dark" id="coachSendBtn">Send</button>
                </div>
                <div class="inline-error d-none" id="coachError"></div>
              </div>
            </div>
          </section>

          <section class="section-block ${isExpanded ? "d-none" : ""}" id="coachPrompts">
            <div class="section-header">
              <h3>Check-in prompts</h3>
              <a href="#/training-plan">View plan</a>
            </div>
            <div class="prompt-grid">
              <div class="prompt-card">
                <h4>Post-run reflection</h4>
                <p class="text-muted">What felt strong today? What would you change?</p>
                <button class="btn btn-outline-secondary coach-prompt" data-prompt="I just finished my workout. Help me reflect on what went well and what I should adjust.">Use prompt</button>
              </div>
              <div class="prompt-card">
                <h4>Fueling check</h4>
                <p class="text-muted">Help me review my workout fueling and recovery choices.</p>
                <button class="btn btn-outline-secondary coach-prompt" data-prompt="Help me review my workout fueling and recovery choices.">Use prompt</button>
              </div>
              <div class="prompt-card">
                <h4>Sleep tracker</h4>
                <p class="text-muted">How many hours did you sleep last night?</p>
                <button class="btn btn-outline-secondary coach-prompt" data-prompt="I want to talk about how sleep is affecting my training this week.">Use prompt</button>
              </div>
            </div>
          </section>
        </div>
      </div>
    `,
  });

  initLayoutActions();
  attachCoachInteractions();
  scrollCoachToBottom();
}

function renderSuggestionItem(user) {
  const following = isFollowingUser(user.user_id);
  const avatarHtml = user.profile_picture_url
    ? `<div class="avatar"><img src="${escapeHtml(API_BASE + user.profile_picture_url)}" alt="${escapeHtml(user.name || "")}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" /></div>`
    : `<div class="avatar"></div>`;
  return `
    <div class="suggestion-item" data-user-id="${user.user_id}">
      ${avatarHtml}
      <div>
        <p class="name">${escapeHtml(user.name)}</p>
        ${user.username ? `<span>@${escapeHtml(user.username)}</span>` : ""}
      </div>
      <button class="btn btn-sm ${following ? "btn-dark" : "btn-outline-secondary"} follow-toggle-btn">
        ${following ? "Following" : "Follow"}
      </button>
    </div>
  `;
}

function renderCoachMessage(message) {
  const senderClass = message.sender === "user" ? "user" : "coach";
  const senderLabel = message.sender === "user" ? "You" : "Coach";
  let contentHtml;
  if (message.sender !== "user") {
    let content = message.content || "";
    const trimmed = content.trim();
    if (trimmed.startsWith("{")) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed.rationale) content = parsed.rationale;
      } catch (_) {}
    }
    contentHtml = `<div class="coach-md">${typeof marked !== "undefined" ? DOMPurify.sanitize(marked.parse(content)) : escapeHtml(content)}</div>`;
  } else {
    contentHtml = `<p>${escapeHtml(message.content)}</p>`;
  }
  return `
    <div class="message ${senderClass}">
      <p class="message-meta">${escapeHtml(senderLabel)} - ${escapeHtml(formatTimeAgo(message.created_at))}</p>
      ${contentHtml}
    </div>
  `;
}

function createCoachMessageElement(message, initialContent = null) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${message.sender === "user" ? "user" : "coach"}`;

  const meta = document.createElement("p");
  meta.className = "message-meta";
  meta.textContent = `${message.sender === "user" ? "You" : "Coach"} - ${formatTimeAgo(
    message.created_at || new Date().toISOString()
  )}`;

  const body = document.createElement("p");
  body.textContent = initialContent ?? message.content ?? "";

  wrapper.append(meta, body);
  return { wrapper, body };
}

function scrollCoachToBottom() {
  const mainContent = document.querySelector(".main-content");
  if (mainContent) {
    mainContent.scrollTop = mainContent.scrollHeight;
  }
}

function expandCoachUI() {
  document.getElementById("coachCenter")?.classList.add("expanded");
  document.getElementById("coachPrompts")?.classList.add("d-none");
}

function addTypingIndicator(messagesEl) {
  const wrapper = document.createElement("div");
  wrapper.className = "message coach typing";
  wrapper.innerHTML = `
    <p class="message-meta">Coach - thinking</p>
    <div class="typing-dots" aria-label="Coach is thinking">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `;
  messagesEl.appendChild(wrapper);
  scrollCoachToBottom();
  return wrapper;
}

async function animateAssistantMessage(messagesEl, message) {
  const { wrapper, body } = createCoachMessageElement(message, "");
  messagesEl.appendChild(wrapper);

  const text = message.content || "";
  for (let index = 0; index < text.length; index += 1) {
    body.textContent += text[index];
    if (index % 3 === 0) scrollCoachToBottom();
    await sleep(12);
  }
  // Replace plain text with markdown-rendered output
  if (typeof marked !== "undefined") {
    body.className = "coach-md";
    body.innerHTML = DOMPurify.sanitize(marked.parse(text));
  }
  scrollCoachToBottom();
}

function renderDeleteSessionModal() {
  return `
    <div class="modal-overlay" id="deleteSessionModal">
      <div class="modal-card" style="max-width:380px">
        <div class="modal-header">
          <h4 class="modal-title" style="font-size:18px">Delete chat session</h4>
          <button class="modal-close" id="deleteSessionClose" aria-label="Close">&times;</button>
        </div>
        <div class="modal-body">
          <p style="margin:0">Are you sure you want to delete this chat session? This cannot be undone.</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="deleteSessionCancelBtn">Cancel</button>
          <button class="btn btn-outline-danger" id="deleteSessionConfirmBtn">Delete session</button>
        </div>
      </div>
    </div>
  `;
}

function openDeleteSessionModal(sessionId) {
  const modal = document.getElementById("deleteSessionModal");
  if (!modal) return;
  modal.dataset.sessionId = sessionId;
  modal.classList.add("open");
}

async function switchToCoachSession(sessionId) {
  if (sessionId === state.coachSessionId) return;
  state.coachSessionId = sessionId;
  state.coachMessages = [];
  await renderCoach();
}

function attachCoachInteractions() {
  const input = document.getElementById("coachInput");
  const sendBtn = document.getElementById("coachSendBtn");
  const errorEl = document.getElementById("coachError");
  const messagesEl = document.getElementById("coachMessages");

  // New chat button — defer session creation until first message
  document.getElementById("coachNewBtn")?.addEventListener("click", async () => {
    state.coachSessionId = null;
    state.coachMessages = [];
    await renderCoach();
  });

  // Session list switching
  document.querySelectorAll(".coach-session-item").forEach((btn) => {
    btn.addEventListener("click", () => switchToCoachSession(btn.dataset.sessionId));
  });

  // Delete session buttons — open styled modal
  document.querySelectorAll(".coach-session-delete").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openDeleteSessionModal(btn.dataset.sessionId);
    });
  });

  // Delete session modal interactions
  const deleteModal = document.getElementById("deleteSessionModal");
  const closeDeleteModal = () => deleteModal?.classList.remove("open");
  document.getElementById("deleteSessionClose")?.addEventListener("click", closeDeleteModal);
  document.getElementById("deleteSessionCancelBtn")?.addEventListener("click", closeDeleteModal);
  deleteModal?.addEventListener("click", (e) => { if (e.target === deleteModal) closeDeleteModal(); });
  document.getElementById("deleteSessionConfirmBtn")?.addEventListener("click", async () => {
    const sessionId = deleteModal?.dataset.sessionId;
    if (!sessionId) return;
    closeDeleteModal();
    try {
      await apiFetch(`/chatbot_sessions/${sessionId}`, { method: "DELETE" });
      state.coachSessions = state.coachSessions.filter((s) => s.chatbot_id !== sessionId);
      if (state.coachSessionId === sessionId) {
        state.coachSessionId = null;
        state.coachMessages = [];
      }
      await renderCoach();
    } catch (err) {
      showToast(`Could not delete session: ${err.message}`, "error");
    }
  });

  async function sendMessage() {
    const message = input.value.trim();
    if (!message) return;
    errorEl.classList.add("d-none");
    sendBtn.disabled = true;
    expandCoachUI();

    // Lazily create the session on first send
    if (!state.coachSessionId) {
      try {
        const created = await apiFetch("/chatbot_sessions", {
          method: "POST",
          body: JSON.stringify({ user_id: state.userId, session_type: "coach" }),
        });
        state.coachSessionId = created.chatbot_id;
        state.coachSessions.unshift(created);
      } catch (err) {
        sendBtn.disabled = false;
        errorEl.textContent = "Could not start session: " + err.message;
        errorEl.classList.remove("d-none");
        return;
      }
    }

    const isFirstMessage = state.coachMessages.length === 0;

    const userMessage = {
      sender: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    state.coachMessages.push(userMessage);
    const { wrapper: userWrapper } = createCoachMessageElement(userMessage);
    messagesEl.appendChild(userWrapper);
    scrollCoachToBottom();

    const typingIndicator = addTypingIndicator(messagesEl);
    input.value = "";

    try {
      const reply = await apiFetch(`/chatbot_sessions/${state.coachSessionId}/reply`, {
        method: "POST",
        body: JSON.stringify({
          user_message: message,
          max_context_messages: 20,
        }),
      });
      typingIndicator.remove();

      if (isFirstMessage) saveSessionTitle(state.coachSessionId, reply.session_title || message);

      const assistantMessage = {
        sender: "assistant",
        content: reply.assistant_message || "",
        created_at: reply.created_at || new Date().toISOString(),
      };
      state.coachMessages.push(assistantMessage);
      await animateAssistantMessage(messagesEl, assistantMessage);
    } catch (error) {
      typingIndicator.remove();
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
      state.coachMessages.pop();
      userWrapper.remove();
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn?.addEventListener("click", sendMessage);
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }
  });

  Array.from(document.querySelectorAll(".coach-prompt")).forEach((button) => {
    button.addEventListener("click", () => {
      input.value = button.dataset.prompt || "";
      input.focus();
    });
  });

  document.getElementById("coachAdjustPlanBtn")?.addEventListener("click", async () => {
    const userPromptText = input.value.trim() || "Please suggest adjustments to my training plan based on my recent performance.";
    if (!state.trainingPlan) await ensureTrainingPlanLoaded();
    const currentVersion = getCurrentPlanVersion();
    if (!currentVersion) {
      showToast("No active training plan found.", "error");
      return;
    }

    const adjustBtn = document.getElementById("coachAdjustPlanBtn");
    if (adjustBtn) adjustBtn.disabled = true;

    if (!state.coachSessionId) {
      try {
        const created = await apiFetch("/chatbot_sessions", {
          method: "POST",
          body: JSON.stringify({ user_id: state.userId, session_type: "coach" }),
        });
        state.coachSessionId = created.chatbot_id;
        state.coachSessions.unshift(created);
      } catch (err) {
        if (adjustBtn) adjustBtn.disabled = false;
        showToast(`Could not start session: ${err.message}`, "error");
        return;
      }
    }

    expandCoachUI();

    const userMessage = {
      sender: "user",
      content: userPromptText,
      created_at: new Date().toISOString(),
    };
    const isFirstMessage = state.coachMessages.length === 0;
    state.coachMessages.push(userMessage);
    const { wrapper: userWrapper } = createCoachMessageElement(userMessage);
    messagesEl.appendChild(userWrapper);
    input.value = "";
    scrollCoachToBottom();

    const typingIndicator = addTypingIndicator(messagesEl);
    try {
      const result = await apiFetch(`/chatbot_sessions/${state.coachSessionId}/suggest_training_plan_actions`, {
        method: "POST",
        body: JSON.stringify({
          version_id: currentVersion.version_id,
          user_prompt: userPromptText,
          apply_actions: false,
        }),
      });
      typingIndicator.remove();

      if (isFirstMessage) saveSessionTitle(state.coachSessionId, result.session_title || "Training plan adjustment");

      const suggestion = result.validated_suggestion;
      const suggestionEl = document.createElement("div");
      suggestionEl.className = "message coach";
      suggestionEl.innerHTML = `<p class="message-meta">Coach - just now</p>${renderPlanSuggestion(suggestion)}`;
      messagesEl.appendChild(suggestionEl);
      scrollCoachToBottom();

      suggestionEl.querySelector(".approve-btn")?.addEventListener("click", async () => {
        try {
          await apiFetch("/training_plan_versions/apply_ai_actions", {
            method: "POST",
            body: JSON.stringify({
              version_id: currentVersion.version_id,
              proposed_actions: suggestion.proposed_actions,
              rationale: suggestion.rationale,
            }),
          });
          await ensureTrainingPlanLoaded(true);
          showToast("Plan updated successfully.");
          const approveBtn = suggestionEl.querySelector(".approve-btn");
          if (approveBtn) { approveBtn.textContent = "Applied ✓"; approveBtn.disabled = true; }
          const declineBtn = suggestionEl.querySelector(".decline-btn");
          if (declineBtn) declineBtn.disabled = true;
        } catch (err) {
          showToast(`Failed to apply changes: ${err.message}`, "error");
        }
      });

      suggestionEl.querySelector(".decline-btn")?.addEventListener("click", () => {
        suggestionEl.remove();
      });
    } catch (error) {
      typingIndicator.remove();
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
      state.coachMessages.pop();
      userWrapper.remove();
    } finally {
      if (adjustBtn) adjustBtn.disabled = false;
    }
  });
}