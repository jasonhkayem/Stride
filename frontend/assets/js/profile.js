async function renderProfile() {
  await Promise.all([ensureActivitiesLoaded(), ensureUsersLoaded(), ensureStravaStatusLoaded()]);
  const [followers, following] = await Promise.all([
    apiFetch(`/user_follows/followers/${state.userId}`).catch(() => []),
    apiFetch(`/user_follows/following/${state.userId}`).catch(() => []),
  ]);

  const myActivities = getCurrentUserActivities().slice(0, 6);
  const user = state.user || {};
  const topActivity = computeTopActivityLabel(getCurrentUserActivities());

  app.innerHTML = renderLayout({
    active: "profile",
    title: "Profile",
    subtitle: "Your public training snapshot.",
    actions: false,
    content: `
      <section class="section-block">
        <div class="profile-hero">
          ${renderAvatarEl(user, "profile-avatar-lg")}
          <div class="profile-identity">
            <h2>${escapeHtml(user.name || "Athlete")}</h2>
            <div class="profile-stats">
              <div class="profile-stat clickable-stat" id="followersStatBtn">
                <span class="stat-value">${Array.isArray(followers) ? followers.length : 0}</span>
                <span class="stat-label">Followers</span>
              </div>
              <div class="profile-stat clickable-stat" id="followingStatBtn">
                <span class="stat-value">${Array.isArray(following) ? following.length : 0}</span>
                <span class="stat-label">Following</span>
              </div>
              <div class="profile-stat">
                <span class="stat-value">${escapeHtml(topActivity)}</span>
                <span class="stat-label">Top activity</span>
              </div>
            </div>
            <div class="mt-3">${renderStatusPill(!!state.stravaStatus?.connected)}</div>
          </div>
          <div class="profile-actions">
            <button class="btn btn-dark" id="editProfileBtn">Edit profile</button>
            <button class="btn btn-outline-secondary" id="profileStravaBtn" style="display:inline-flex;align-items:center;">
              ${STRAVA_SVG}${state.stravaStatus?.connected ? "Disconnect Strava" : "Connect Strava"}
            </button>
            ${state.stravaStatus?.connected ? `<button class="btn btn-outline-secondary" id="stravaSyncBtn" style="display:inline-flex;align-items:center;">${STRAVA_SVG}Sync activities</button>` : ""}
          </div>
        </div>
      </section>

      ${(() => {
        const prs = getPersonalRecordsSummary();
        if (!prs.length) return "";
        return `
          <section class="section-block">
            <div class="section-header"><h3>Personal records</h3><span class="tag">${prs.length} PR${prs.length !== 1 ? "s" : ""}</span></div>
            <div class="pr-grid">
              ${prs.map((pr) => `
                <div class="pr-card">
                  <span class="pr-label">${escapeHtml(pr.label)}</span>
                  <span class="pr-value">${escapeHtml(pr.value)}</span>
                  <span class="pr-date">${escapeHtml(formatShortDate(pr.date))}</span>
                </div>`).join("")}
            </div>
          </section>`;
      })()}

      <section class="section-block">
        <div class="section-header">
          <h3>Recent activities</h3>
          <span class="tag">Last 6</span>
        </div>
        <div class="activity-grid">
          ${
            myActivities.length
              ? myActivities.map((activity) => renderProfileActivity(activity)).join("")
              : `
            <div class="panel-card">
              <h3>No recent activities</h3>
              <p class="text-muted">Once your workouts are in the system, they will show up here.</p>
            </div>
          `
          }
        </div>
      </section>

      ${renderActivityModal()}
      ${renderAddActivityModal()}
      ${renderEditProfileModal(user)}
      ${renderFollowsListModal()}
    `,
  });

  initLayoutActions();
  attachEditProfileActions();
  attachProfileStravaAction();
  attachProfileActivityHandlers();
  attachFollowsModalActions(state.userId, followers, following);
}

async function renderPublicProfile(userId) {
  await Promise.all([ensureUsersLoaded(), ensureActivitiesLoaded(), ensureFollowingLoaded()]);
  const profileUser = state.usersById[userId] || (await apiFetch(`/users/${userId}`));
  const [followers, following] = await Promise.all([
    apiFetch(`/user_follows/followers/${userId}`).catch(() => []),
    apiFetch(`/user_follows/following/${userId}`).catch(() => []),
  ]);
  const userActivities = state.activities.filter((activity) => activity.user_id === userId).slice(0, 6);
  const topActivity = computeTopActivityLabel(state.activities.filter((activity) => activity.user_id === userId));
  const ownProfile = userId === state.userId;

  app.innerHTML = renderLayout({
    active: ownProfile ? "profile" : "",
    title: ownProfile ? "Profile" : "Public Profile",
    subtitle: ownProfile ? "Your public training snapshot." : "See how this athlete trains and stays active.",
    actions: false,
    content: `
      <section class="section-block">
        <div class="profile-hero">
          ${renderAvatarEl(profileUser, "profile-avatar-lg")}
          <div class="profile-identity">
            <h2>${escapeHtml(profileUser.name || "Athlete")}</h2>
            <div class="profile-stats">
              <div class="profile-stat clickable-stat" id="followersStatBtn">
                <span class="stat-value">${Array.isArray(followers) ? followers.length : 0}</span>
                <span class="stat-label">Followers</span>
              </div>
              <div class="profile-stat clickable-stat" id="followingStatBtn">
                <span class="stat-value">${Array.isArray(following) ? following.length : 0}</span>
                <span class="stat-label">Following</span>
              </div>
              <div class="profile-stat">
                <span class="stat-value">${escapeHtml(topActivity)}</span>
                <span class="stat-label">Top activity</span>
              </div>
            </div>
          </div>
          <div class="profile-actions">
            ${
              ownProfile
                ? `<button class="btn btn-dark" id="editProfileBtn">Edit profile</button>`
                : `<button class="btn ${isFollowingUser(userId) ? "btn-dark" : "btn-outline-secondary"}" id="publicFollowBtn" data-user-id="${userId}">
                    ${isFollowingUser(userId) ? "Following" : "Follow"}
                  </button>`
            }
            <button class="btn btn-outline-secondary" id="backToActivitiesBtn">Back</button>
          </div>
        </div>
      </section>

      <section class="section-block">
        <div class="section-header">
          <h3>Recent activities</h3>
          <span class="tag">Last 6</span>
        </div>
        <div class="activity-grid">
          ${
            userActivities.length
              ? userActivities.map((activity) => renderProfileActivity(activity)).join("")
              : `
            <div class="panel-card">
              <h3>No recent activities</h3>
              <p class="text-muted">This athlete has not logged a recent activity yet.</p>
            </div>
          `
          }
        </div>
      </section>

      ${renderActivityModal()}
      ${ownProfile ? renderAddActivityModal() : ""}
      ${ownProfile ? renderEditProfileModal(profileUser) : ""}
      ${renderFollowsListModal()}
    `,
  });

  initLayoutActions();
  if (ownProfile) {
    attachEditProfileActions();
  } else {
    attachPublicProfileActions();
  }
  attachProfileActivityHandlers();
  attachFollowsModalActions(userId, followers, following);
}

function renderProfileActivity(activity) {
  const typeLabel = formatActivityType(activity.activity_type);
  const hasDistance = DISTANCE_ACTIVITY_TYPES.has(activity.activity_type);
  const hasMap = hasDistance && activity.activity_type !== "swim";
  const meta = hasDistance
    ? `${formatDistance(activity.distance)} - ${formatDuration(activity.duration)}`
    : formatDuration(activity.duration);
  const kpis = hasDistance
    ? [
        { label: "Distance", value: formatDistance(activity.distance) },
        { label: "Duration", value: formatDuration(activity.duration) },
        { label: "Pace", value: formatPace(activity) },
      ]
    : [{ label: "Duration", value: formatDuration(activity.duration) }];

  return `
    <article
      class="activity-tile"
      data-title="${escapeHtml(`${formatTiming(activity.timestamp)} ${typeLabel}`)}"
      data-type="${escapeHtml(typeLabel)}"
      data-meta="${escapeHtml(meta)}"
      data-has-map="${hasMap}"
      data-activity-id="${escapeHtml(activity.activity_id || "")}"
      data-user-id="${escapeHtml(activity.user_id || "")}"
      data-raw-type="${escapeHtml(activity.activity_type || "")}"
      data-raw-ts="${escapeHtml(activity.timestamp || "")}"
      data-raw-dist="${activity.distance || ""}"
      data-raw-dur="${Math.round((activity.duration || 0) / 60)}"
    >
      <div class="activity-tile-media">
        ${hasMap ? '<span class="map-placeholder">Map preview</span>' : renderActivityKpis(kpis)}
        <span class="activity-type-badge">${escapeHtml(typeLabel)}</span>
      </div>
      <div class="activity-tile-body">
        <h4>${escapeHtml(`${formatTiming(activity.timestamp)} ${typeLabel}`)}</h4>
        <p class="text-muted">${escapeHtml(meta)}</p>
      </div>
    </article>
  `;
}

function renderFollowsListModal() {
  return `
    <div class="modal-overlay" id="followsListModal">
      <div class="modal-card" style="max-width:360px">
        <div class="modal-header">
          <h4 class="modal-title" id="followsListTitle" style="font-size:18px">Followers</h4>
          <button class="modal-close" id="followsListClose">&times;</button>
        </div>
        <div class="modal-body" id="followsListBody" style="max-height:400px;overflow-y:auto">
          <p class="text-muted small mb-0">Loading...</p>
        </div>
      </div>
    </div>
  `;
}

function attachFollowsModalActions(profileUserId, followers, following) {
  const modal = document.getElementById("followsListModal");
  if (!modal) return;

  const title = document.getElementById("followsListTitle");
  const body = document.getElementById("followsListBody");

  document.getElementById("followsListClose")?.addEventListener("click", () => modal.classList.remove("open"));
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("open"); });

  function renderFollowsList(users, emptyMsg) {
    return users.length
      ? users.map((u) => `
          <div class="follows-list-item" data-user-id="${escapeHtml(u?.user_id || "")}">
            ${renderAvatarEl(u, "liker-avatar")}
            <span class="follows-user-name liker-name">${escapeHtml(u?.name || "Athlete")}</span>
          </div>`).join("")
      : `<p class="text-muted small mb-0">${emptyMsg}</p>`;
  }

  function openFollows(type) {
    if (type === "followers") {
      title.textContent = "Followers";
      const users = (Array.isArray(followers) ? followers : []).map((rel) => state.usersById[rel.follower_id]).filter(Boolean);
      body.innerHTML = renderFollowsList(users, "No followers yet.");
    } else {
      title.textContent = "Following";
      const users = (Array.isArray(following) ? following : []).map((rel) => state.usersById[rel.following_id]).filter(Boolean);
      body.innerHTML = renderFollowsList(users, "Not following anyone yet.");
    }
    body.querySelectorAll(".follows-list-item").forEach((item) => {
      item.addEventListener("click", () => {
        const uid = item.dataset.userId;
        if (uid) { modal.classList.remove("open"); window.location.hash = `#/athlete/${uid}`; }
      });
    });
    modal.classList.add("open");
  }

  document.getElementById("followersStatBtn")?.addEventListener("click", () => openFollows("followers"));
  document.getElementById("followingStatBtn")?.addEventListener("click", () => openFollows("following"));
}

function renderEditProfileModal(user) {
  const avatarUrl = user.profile_picture_url ? `${API_BASE}${user.profile_picture_url}` : null;
  const avatarHtml = avatarUrl
    ? `<img src="${escapeHtml(avatarUrl)}" alt="Profile photo" />`
    : "";
  return `
    <div class="modal-overlay" id="editProfileModal">
      <div class="modal-card edit-profile-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta">Account</p>
            <h2 class="modal-title">Edit profile</h2>
          </div>
          <button class="modal-close" id="editProfileClose">&times;</button>
        </div>
        <div class="modal-body">

          <div class="edit-avatar-section">
            <div class="edit-avatar" id="editAvatarPreview">${avatarHtml}</div>
            <div class="edit-avatar-info">
              <p class="edit-avatar-name">${escapeHtml(user.name || "Athlete")}</p>
              <label class="btn btn-outline-secondary btn-sm edit-avatar-label" for="editAvatarInput">Change photo</label>
              <input type="file" id="editAvatarInput" accept="image/jpeg,image/png,image/gif,image/webp" class="d-none" />
              <p class="edit-avatar-hint" id="editAvatarStatus"></p>
            </div>
          </div>

          <div class="plan-form-grid mt-3">
            <div>
              <label class="form-label">Full name</label>
              <input class="form-control" id="editProfileName" value="${escapeHtml(user.name || "")}" />
            </div>
            <div>
              <label class="form-label">Email</label>
              <input class="form-control" id="editProfileEmail" type="email" value="${escapeHtml(user.email || "")}" />
            </div>
            <div>
              <label class="form-label">Weekly distance goal (km)</label>
              <input class="form-control" id="editProfileGoal" type="number" min="0" step="0.5" placeholder="e.g. 40" value="${user.weekly_goal_km != null ? user.weekly_goal_km : ""}" />
            </div>
          </div>

          <div class="password-toggle-header" id="passwordToggle">
            <span>Change password</span>
            <span class="password-toggle-icon">+</span>
          </div>
          <div class="password-section" id="passwordSection">
            <div>
              <label class="form-label">New password</label>
              <input class="form-control" id="editProfilePassword" type="password" placeholder="At least 8 characters" />
            </div>
            <div>
              <label class="form-label">Confirm new password</label>
              <input class="form-control" id="editProfilePasswordConfirm" type="password" placeholder="Re-enter new password" />
            </div>
          </div>

          <div class="inline-error mt-3 d-none" id="editProfileError"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="editProfileCancel">Cancel</button>
          <button class="btn btn-dark" id="editProfileSubmit">Save changes</button>
        </div>
      </div>
    </div>
  `;
}

function attachProfileActivityHandlers() {
  const modal = document.getElementById("activityModal");
  const modalClose = document.getElementById("modalClose");
  if (!modal) return;

  const modalActions = document.getElementById("modalActivityActions");
  let currentActivityId = null;

  const closeModal = () => {
    modal.classList.remove("open");
    currentActivityId = null;
    if (modalActions) modalActions.classList.add("d-none");
  };

  const tiles = Array.from(app.querySelectorAll(".activity-tile"));
  const modalTitle = modal.querySelector(".modal-title");
  const modalMeta = modal.querySelector(".modal-meta");
  const modalStats = modal.querySelector("#modalStats");
  const modalChips = modal.querySelector("#modalChips");
  const modalMap = modal.querySelector("#modalMap");
  const modalCharts = modal.querySelector("#modalCharts");

  tiles.forEach((tile) => {
    tile.addEventListener("click", () => {
      modalTitle.textContent = tile.dataset.title || "Activity";
      modalMeta.textContent = tile.dataset.meta || "";
      modalStats.innerHTML = `
        <div class="modal-stat">
          <span class="label">Type</span>
          <span class="value">${escapeHtml(tile.dataset.type || "Activity")}</span>
        </div>
        <div class="modal-stat">
          <span class="label">Summary</span>
          <span class="value">${escapeHtml(tile.dataset.meta || "")}</span>
        </div>
      `;
      modalChips.innerHTML = `<span class="chip">${escapeHtml(tile.dataset.type || "Activity")}</span><span class="chip">Recent</span>`;

      const hasMap = tile.dataset.hasMap === "true";
      modalMap.style.display = hasMap ? "flex" : "none";
      modalCharts.style.display = hasMap ? "block" : "none";
      const lapChartsEl = document.getElementById("modalLapCharts");
      if (lapChartsEl) lapChartsEl.style.display = "none";

      // Populate user info for other people's tiles
      const tileUserId = tile.dataset.userId;
      const modalUserInfo = document.getElementById("modalUserInfo");
      const modalUserAvatar = document.getElementById("modalUserAvatar");
      const modalUserName = document.getElementById("modalUserName");
      if (modalUserInfo) {
        if (tileUserId && tileUserId !== state.userId) {
          const tileUser = state.usersById[tileUserId];
          modalUserAvatar.innerHTML = tileUser?.profile_picture_url
            ? `<img src="${escapeHtml(API_BASE + tileUser.profile_picture_url)}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />`
            : "";
          modalUserName.textContent = tileUser?.name || "Athlete";
          modalUserName.dataset.userId = tileUserId;
          modalUserInfo.classList.remove("d-none");
        } else {
          modalUserInfo.classList.add("d-none");
        }
      }

      const activityId = tile.dataset.activityId || null;
      const isOwn = activityId && tile.dataset.userId === state.userId;
      currentActivityId = isOwn ? activityId : null;

      if (modalActions) {
        if (currentActivityId) {
          modalActions.classList.remove("d-none");
          modalActions.style.display = "flex";
          modalActions.dataset.rawType = tile.dataset.rawType || "";
          modalActions.dataset.rawTs = tile.dataset.rawTs || "";
          modalActions.dataset.rawDist = tile.dataset.rawDist || "";
          modalActions.dataset.rawDur = tile.dataset.rawDur || "";
        } else {
          modalActions.classList.add("d-none");
        }
      }

      modal.classList.add("open");
    });
  });

  modalClose?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  modal.querySelector("#modalUserName")?.addEventListener("click", () => {
    const uid = modal.querySelector("#modalUserName")?.dataset.userId;
    if (uid) { closeModal(); window.location.hash = `#/athlete/${uid}`; }
  });

  modal.querySelector("#modalDeleteBtn")?.addEventListener("click", async () => {
    if (!currentActivityId) return;
    if (!confirm("Delete this activity?")) return;
    try {
      await apiFetch(`/activities/${currentActivityId}`, { method: "DELETE" });
      closeModal();
      await ensureActivitiesLoaded(true);
      await handleRoute();
    } catch (err) {
      alert(`Could not delete: ${err.message}`);
    }
  });

  modal.querySelector("#modalEditBtn")?.addEventListener("click", () => {
    if (!currentActivityId || !modalActions) return;
    const editId = currentActivityId;
    const rawType = modalActions.dataset.rawType || "run";
    const rawTs = modalActions.dataset.rawTs || "";
    const rawDist = modalActions.dataset.rawDist || "";
    const rawDur = modalActions.dataset.rawDur || "";
    closeModal();
    const addModal = document.getElementById("addActivityModal");
    if (!addModal) return;
    const typeSelectEl2 = document.getElementById("activityTypeSelect");
    if (typeSelectEl2) { typeSelectEl2.value = rawType; typeSelectEl2.dispatchEvent(new Event("change")); }
    document.getElementById("activityDistanceInput").value = rawDist;
    document.getElementById("activityDurationInput").value = rawDur;
    if (rawTs) {
      const local = new Date(new Date(rawTs).getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      document.getElementById("activityTimestampInput").value = local;
    }
    addModal.dataset.editActivityId = editId;
    const titleEl = addModal.querySelector(".modal-meta");
    if (titleEl) titleEl.textContent = "Edit Activity";
    document.getElementById("addActivitySubmit").textContent = "Update Activity";
    // Pre-populate HR and laps
    const editActivity2 = state.activities.find((a) => String(a.activity_id) === String(editId));
    const hrInputEl2 = document.getElementById("activityHrInput");
    if (hrInputEl2) hrInputEl2.value = editActivity2?.average_heart_rate ? Math.round(editActivity2.average_heart_rate) : "";
    if (editActivity2?.laps?.length && addModal._populateLapRows) addModal._populateLapRows(editActivity2.laps);
    addModal.classList.add("open");
  });
}

function attachUserSearch() {
  const searchInput = document.getElementById("userSearchInput");
  const searchDropdown = document.getElementById("userSearchDropdown");
  if (!searchInput || !searchDropdown) return;

  const updateSearchDropdown = () => {
    const value = searchInput.value.trim().toLowerCase();
    if (!value) {
      searchDropdown.classList.remove("open");
      searchDropdown.innerHTML = "";
      return;
    }

    const matches = state.users
      .filter((user) => {
        const haystack = `${user.name} ${user.username || ""} ${user.email}`.toLowerCase();
        return haystack.includes(value);
      })
      .filter((user) => user.user_id !== state.userId)
      .slice(0, 5);

    searchDropdown.innerHTML = matches.length
      ? matches
          .map(
            (user) => `
          <div class="search-result-row" data-user-id="${user.user_id}">
            <button class="search-item search-item-user" type="button">
              ${escapeHtml(user.name)} <span>@${escapeHtml(user.username || user.email)}</span>
            </button>
            <button class="btn btn-sm ${isFollowingUser(user.user_id) ? "btn-dark" : "btn-outline-secondary"} follow-toggle-btn">
              ${isFollowingUser(user.user_id) ? "Following" : "Follow"}
            </button>
          </div>
        `
          )
          .join("")
      : `<button class="search-item" type="button" disabled>No matches</button>`;
    searchDropdown.classList.add("open");
  };

  searchInput.addEventListener("input", updateSearchDropdown);
  searchInput.addEventListener("focus", updateSearchDropdown);
  searchInput.addEventListener("blur", () => {
    setTimeout(() => searchDropdown.classList.remove("open"), 150);
  });
}

async function toggleFollow(userId) {
  if (!userId || userId === state.userId) return;

  const existing = state.followingMap[userId];
  if (existing) {
    await apiFetch(`/user_follows/${existing.follow_id}`, { method: "DELETE" });
  } else {
    const relation = await apiFetch("/user_follows", {
      method: "POST",
      body: JSON.stringify({
        follower_id: state.userId,
        following_id: userId,
      }),
    });
    state.following.push(relation);
  }

  await ensureFollowingLoaded(true);
}

function attachSocialActions() {
  Array.from(document.querySelectorAll(".suggestion-item, .search-result-row")).forEach((row) => {
    const userId = row.dataset.userId;
    const button = row.querySelector(".follow-toggle-btn");
    const userButton = row.querySelector(".search-item-user");

    userButton?.addEventListener("click", () => {
      window.location.hash = `#/athlete/${userId}`;
    });

    if (row.classList.contains("suggestion-item")) {
      row.querySelector(".name")?.addEventListener("click", () => {
        window.location.hash = `#/athlete/${userId}`;
      });
    }

    button?.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      button.disabled = true;
      try {
        await toggleFollow(userId);
        await renderActivities();
      } catch (error) {
        window.alert(`Follow action failed: ${error.message}`);
        button.disabled = false;
      }
    });
  });
}

async function connectStravaFlow() {
  const result = await apiFetch(`/users/${state.userId}/strava/oauth/start`);
  if (!result.authorize_url) {
    throw new Error("Failed to start Strava authorization.");
  }

  const popup = window.open(result.authorize_url, "_blank", "width=700,height=800");
  const startedAt = Date.now();

  while (Date.now() - startedAt < 120000) {
    await sleep(2000);
    const status = await ensureStravaStatusLoaded(true);
    if (status?.connected) {
      try {
        popup?.close();
      } catch (_error) {
        // noop
      }
      return status;
    }
    if (popup && popup.closed) break;
  }

  throw new Error("Strava connection was not completed yet.");
}

function attachEditProfileActions() {
  const openBtn = document.getElementById("editProfileBtn");
  const modal = document.getElementById("editProfileModal");
  if (!openBtn || !modal) return;

  const closeBtn = document.getElementById("editProfileClose");
  const cancelBtn = document.getElementById("editProfileCancel");
  const submitBtn = document.getElementById("editProfileSubmit");
  const errorEl = document.getElementById("editProfileError");
  const passwordToggle = document.getElementById("passwordToggle");
  const passwordSection = document.getElementById("passwordSection");
  const passwordToggleIcon = modal.querySelector(".password-toggle-icon");
  const avatarInput = document.getElementById("editAvatarInput");
  const avatarPreview = document.getElementById("editAvatarPreview");
  const avatarStatus = document.getElementById("editAvatarStatus");

  const closeModal = () => {
    modal.classList.remove("open");
    errorEl.classList.add("d-none");
    if (passwordSection) passwordSection.classList.remove("open");
    if (passwordToggleIcon) passwordToggleIcon.textContent = "+";
  };

  openBtn.addEventListener("click", () => modal.classList.add("open"));
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  passwordToggle?.addEventListener("click", () => {
    const open = passwordSection.classList.toggle("open");
    if (passwordToggleIcon) passwordToggleIcon.textContent = open ? "−" : "+";
  });

  avatarInput?.addEventListener("change", async () => {
    const file = avatarInput.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      if (avatarPreview) avatarPreview.innerHTML = `<img src="${e.target.result}" alt="Preview" />`;
      const heroAvatar = document.querySelector(".profile-avatar-lg img");
      if (heroAvatar) heroAvatar.src = e.target.result;
    };
    reader.readAsDataURL(file);
    if (avatarStatus) avatarStatus.textContent = "Uploading…";
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/users/${state.userId}/avatar`, {
        method: "POST",
        headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Upload failed");
      if (data.profile_picture_url) {
        state.user = { ...state.user, profile_picture_url: data.profile_picture_url };
        const idx = state.users.findIndex((u) => u.user_id === state.userId);
        if (idx !== -1) {
          state.users[idx] = { ...state.users[idx], profile_picture_url: data.profile_picture_url };
          state.usersById[state.userId] = state.users[idx];
        }
      }
      if (avatarStatus) avatarStatus.textContent = "Photo updated.";
    } catch (err) {
      if (avatarStatus) avatarStatus.textContent = `Upload failed: ${err.message}`;
    }
  });

  submitBtn?.addEventListener("click", async () => {
    errorEl.classList.add("d-none");
    const newPassword = document.getElementById("editProfilePassword")?.value || "";
    const confirmPassword = document.getElementById("editProfilePasswordConfirm")?.value || "";
    if (newPassword && newPassword !== confirmPassword) {
      errorEl.textContent = "Passwords do not match.";
      errorEl.classList.remove("d-none");
      return;
    }
    submitBtn.disabled = true;
    try {
      const goalVal = document.getElementById("editProfileGoal")?.value.trim();
      const payload = {
        name: document.getElementById("editProfileName").value.trim(),
        email: document.getElementById("editProfileEmail").value.trim(),
        weekly_goal_km: goalVal ? parseFloat(goalVal) : null,
      };
      if (newPassword) payload.password_hash = newPassword;
      const updated = await apiFetch(`/users/${state.userId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setAuth(updated, state.token);
      state.users = [];
      state.usersById = {};
      await ensureUsersLoaded(true);
      closeModal();
      await renderProfile();
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

function attachPublicProfileActions() {
  const backBtn = document.getElementById("backToActivitiesBtn");
  backBtn?.addEventListener("click", () => {
    window.history.length > 1 ? window.history.back() : (window.location.hash = "#/activities");
  });

  const followBtn = document.getElementById("publicFollowBtn");
  followBtn?.addEventListener("click", async () => {
    const targetUserId = followBtn.dataset.userId;
    followBtn.disabled = true;
    try {
      await toggleFollow(targetUserId);
      await renderPublicProfile(targetUserId);
    } catch (error) {
      window.alert(`Follow action failed: ${error.message}`);
      followBtn.disabled = false;
    }
  });
}

function attachUserLinkActions() {
  Array.from(document.querySelectorAll(".view-user-btn")).forEach((button) => {
    button.addEventListener("click", () => {
      const userId = button.dataset.userId;
      if (userId) {
        window.location.hash = `#/athlete/${userId}`;
      }
    });
  });
}

function attachProfileStravaAction() {
  const button = document.getElementById("profileStravaBtn");
  if (!button) return;

  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const status = await ensureStravaStatusLoaded(true);
      if (status?.connected) {
        await apiFetch(`/users/${state.userId}/strava`, { method: "DELETE" });
        state.stravaStatus = { connected: false };
        await ensureActivitiesLoaded(true);
        await renderProfile();
      } else {
        await connectStravaFlow();
        await renderProfile();
      }
    } catch (error) {
      window.alert(`Strava action failed: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  });

  const syncBtn = document.getElementById("stravaSyncBtn");
  if (syncBtn) {
    syncBtn.addEventListener("click", async () => {
      syncBtn.disabled = true;
      syncBtn.innerHTML = `${STRAVA_SVG}Syncing…`;
      try {
        const result = await apiFetch("/activities/strava/sync", {
          method: "POST",
          body: JSON.stringify({ per_page: 30, max_pages: 3 }),
        });
        await ensureActivitiesLoaded(true);
        await renderProfile();
        showToast(`Imported ${result.imported} new activit${result.imported === 1 ? "y" : "ies"}.`);
      } catch (error) {
        showToast(`Sync failed: ${error.message}`, "error");
        syncBtn.disabled = false;
        syncBtn.innerHTML = `${STRAVA_SVG}Sync activities`;
      }
    });
  }
}