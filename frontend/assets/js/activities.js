function initActivityMaps() {
  if (typeof L === "undefined") return;
  document.querySelectorAll("[data-polyline]").forEach((el) => {
    if (el._leafletMap) return;
    const encoded = el.dataset.polyline;
    if (!encoded) return;
    try {
      const coords = decodePolyline(encoded);
      if (!coords.length) return;
      const map = L.map(el, { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
      const polyline = L.polyline(coords, { color: "#111827", weight: 3 }).addTo(map);
      map.fitBounds(polyline.getBounds(), { padding: [8, 8] });
      el._leafletMap = map;
    } catch (_e) { /* ignore decode errors */ }
  });
}

function renderWeeklyDistanceChart(activities) {
  const canvas = document.getElementById("weeklyDistanceChart");
  if (!canvas || typeof Chart === "undefined") return;

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d;
  });
  const labels = days.map((d) => d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric" }));
  const data = days.map((day) => {
    const dayStr = day.toISOString().slice(0, 10);
    return (activities || [])
      .filter((a) => (a.timestamp || "").slice(0, 10) === dayStr)
      .reduce((sum, a) => sum + (a.distance || 0), 0);
  });

  new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "km",
        data,
        backgroundColor: "#111827",
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { callback: (v) => `${v} km` } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderModalPaceChart(activityId, activityType) {
  const modalCharts = document.getElementById("modalCharts");
  const canvas = document.getElementById("modalPaceChart");
  if (!canvas || typeof Chart === "undefined" || !modalCharts) return;

  if (canvas._chartInstance) { canvas._chartInstance.destroy(); canvas._chartInstance = null; }

  const isRun = activityType === "run";
  const recentOwn = state.activities
    .filter((a) => a.user_id === state.userId && a.activity_type === activityType && a.distance > 0 && a.duration > 0)
    .slice(0, 8)
    .reverse();

  if (recentOwn.length < 2) { modalCharts.style.display = "none"; return; }
  modalCharts.style.display = "block";

  const labels = recentOwn.map((a) => formatShortDate(a.timestamp));
  const data = recentOwn.map((a) =>
    isRun ? parseFloat((a.duration / 60 / a.distance).toFixed(2)) : parseFloat(a.distance.toFixed(2))
  );
  const currentIdx = recentOwn.findIndex((a) => String(a.activity_id) === String(activityId));
  const colors = data.map((_, i) => (i === currentIdx ? "#111827" : "#e5e7eb"));

  canvas._chartInstance = new Chart(canvas, {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        label: (ctx) => isRun ? `${ctx.parsed.y} min/km` : `${ctx.parsed.y} km`,
      }}},
      scales: {
        y: { reverse: isRun, ticks: { font: { size: 10 } } },
        x: { ticks: { font: { size: 10 } } },
      },
    },
  });
}

function renderModalLapChart(laps) {
  const section = document.getElementById("modalLapCharts");
  const canvas = document.getElementById("modalLapChart");
  if (!section || !canvas || typeof Chart === "undefined") return;

  if (canvas._chartInstance) { canvas._chartInstance.destroy(); canvas._chartInstance = null; }

  if (!laps || !laps.length) { section.style.display = "none"; return; }

  const validLaps = laps.filter((l) => l.distance_km > 0 && l.duration_sec > 0);
  if (!validLaps.length) { section.style.display = "none"; return; }

  section.style.display = "block";

  const labels = validLaps.map((l) => `Lap ${l.lap_index}`);
  const paceData = validLaps.map((l) =>
    parseFloat((l.duration_sec / 60 / l.distance_km).toFixed(3))
  );
  const hrData = validLaps.map((l) => (l.avg_hr != null ? Math.round(l.avg_hr) : null));
  const hasHr = hrData.some((v) => v !== null);

  const formatPaceVal = (v) => {
    const m = Math.floor(v);
    const s = String(Math.round((v - m) * 60)).padStart(2, "0");
    return `${m}:${s}`;
  };

  const datasets = [
    {
      type: "bar",
      label: "Pace",
      data: paceData,
      backgroundColor: "#e5e7eb",
      borderRadius: 4,
      yAxisID: "yPace",
    },
  ];

  const scales = {
    x: { ticks: { font: { size: 10 } } },
    yPace: {
      type: "linear",
      position: "left",
      reverse: true,
      ticks: { font: { size: 10 }, callback: formatPaceVal },
      title: { display: true, text: "Pace (min/km)", font: { size: 10 } },
    },
  };

  if (hasHr) {
    datasets.push({
      type: "line",
      label: "Avg HR",
      data: hrData,
      borderColor: "#ef4444",
      backgroundColor: "rgba(239,68,68,0.08)",
      pointRadius: 4,
      tension: 0.3,
      yAxisID: "yHr",
    });
    scales.yHr = {
      type: "linear",
      position: "right",
      grid: { drawOnChartArea: false },
      ticks: { font: { size: 10 }, callback: (v) => `${v}` },
      title: { display: true, text: "HR (bpm)", font: { size: 10 } },
    };
  }

  canvas._chartInstance = new Chart(canvas, {
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: {
        legend: { display: hasHr, labels: { font: { size: 10 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: (ctx) =>
              ctx.dataset.label === "Avg HR"
                ? `HR: ${ctx.parsed.y} bpm`
                : `Pace: ${formatPaceVal(ctx.parsed.y)} /km`,
          },
        },
      },
      scales,
    },
  });
}

function renderModalHrChart(activityId, activityType) {
  const section = document.getElementById("modalHrCharts");
  const canvas = document.getElementById("modalHrChart");
  if (!section || !canvas || typeof Chart === "undefined") return;

  if (canvas._chartInstance) { canvas._chartInstance.destroy(); canvas._chartInstance = null; }

  const recentOwn = state.activities
    .filter((a) => a.user_id === state.userId && a.activity_type === activityType && a.average_heart_rate != null)
    .slice(0, 8)
    .reverse();

  if (!recentOwn.length) { section.style.display = "none"; return; }
  section.style.display = "block";

  const labels = recentOwn.map((a) => formatShortDate(a.timestamp));
  const data = recentOwn.map((a) => Math.round(a.average_heart_rate));
  const currentIdx = recentOwn.findIndex((a) => String(a.activity_id) === String(activityId));
  const colors = data.map((_, i) => (i === currentIdx ? "#ef4444" : "#fca5a5"));

  canvas._chartInstance = new Chart(canvas, {
    type: "bar",
    data: { labels, datasets: [{ data, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y} bpm` } },
      },
      scales: {
        y: { ticks: { font: { size: 10 }, callback: (v) => `${v}` } },
        x: { ticks: { font: { size: 10 } } },
      },
    },
  });
}


async function renderActivities() {
  await Promise.all([ensureUsersLoaded(), ensureActivitiesLoaded(), ensureFollowingLoaded(), ensureActivityLikesLoaded(), ensureActivityCommentsLoaded()]);

  const followingIds = new Set(Object.keys(state.followingMap));
  const isFollowingAnyone = followingIds.size > 0;
  const followedFeed = state.activities.filter(
    (activity) => activity.user_id === state.userId || followingIds.has(activity.user_id)
  );
  // Show personalised feed only once the user is following people.
  // Until then, show all platform activity so there is something to discover.
  const feedActivities = isFollowingAnyone ? followedFeed : state.activities;
  const subtitle = isFollowingAnyone
    ? "Recent activities from athletes you follow."
    : "Follow athletes to personalise this feed.";

  const feed = feedActivities.length
    ? feedActivities.map((activity) => renderApiActivityCard(activity)).join("")
    : renderInfoCard("No activities yet", "Once activities are synced or created, your feed will show up here.");

  app.innerHTML = renderLayout({
    active: "activities",
    title: "Activities",
    subtitle,
    content: `
      <section class="section-block">
        <div class="activities-layout">
          <div class="activity-column">
            <div class="filters-bar">
              <div class="filters-group">
                <select class="form-select" id="activityTypeFilter">
                  <option value="all">All types</option>
                  <option value="run">Run</option>
                  <option value="bike">Ride</option>
                  <option value="swim">Swim</option>
                  <option value="walk">Walk</option>
                  <option value="hike">Hike</option>
                  <option value="weights">Strength</option>
                  <option value="mobility">Mobility</option>
                  <option value="yoga">Yoga</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div class="activity-feed">${feed}</div>
          </div>

          <aside class="sidebar-column">
            <div class="sidebar-search">
              <label class="form-label">Search users</label>
              <div class="search-group">
                <input type="text" class="form-control" id="userSearchInput" placeholder="Search username" />
                <div class="search-dropdown" id="userSearchDropdown"></div>
              </div>
            </div>
            <div class="suggestions-card">
              <h4>Who to follow</h4>
              ${(state.users || [])
                .filter((user) => user.user_id !== state.userId && !isFollowingUser(user.user_id))
                .slice(0, 3)
                .map((user) => renderSuggestionItem(user))
                .join("")}
            </div>
          </aside>
        </div>
      </section>

      ${renderActivityModal()}
      ${renderLikersModal()}
    `,
  });

  initLayoutActions();
  attachActivityCardHandlers();
  attachActivityFilters();
  attachUserSearch();
  attachSocialActions();
  initActivityMaps();
}

function renderApiActivityCard(activity) {
  const typeLabel = formatActivityType(activity.activity_type);
  const hasDistance = DISTANCE_ACTIVITY_TYPES.has(activity.activity_type);
  const hrStat = activity.average_heart_rate
    ? { label: "Avg HR", value: `${Math.round(activity.average_heart_rate)} bpm` }
    : null;
  const stats = hasDistance
    ? [
        { label: "Distance", value: formatDistance(activity.distance) },
        { label: "Time", value: formatDuration(activity.duration) },
        { label: "Pace", value: formatPace(activity) },
        ...(hrStat ? [hrStat] : []),
      ]
    : [
        { label: "Time", value: formatDuration(activity.duration) },
        ...(hrStat ? [hrStat] : []),
      ];

  const mapCapable = hasDistance && activity.activity_type !== "swim";
  const isOwnActivity = activity.user_id === state.userId;
  const user = state.usersById[activity.user_id] || null;

  const activityLikesForCard = state.activityLikes.filter((l) => l.activity_id === activity.activity_id);
  const userLike = activityLikesForCard.find((l) => l.user_id === state.userId);
  const engagement = {
    activityId: activity.activity_id,
    likeCount: activityLikesForCard.length,
    hasLiked: Boolean(userLike),
    likeId: userLike?.like_id || null,
    commentCount: state.activityComments.filter((c) => c.activity_id === activity.activity_id).length,
    isOwn: isOwnActivity,
  };

  const prLabels = isOwnActivity ? (state.personalRecords[String(activity.activity_id)] || []) : [];
  const chips = [typeLabel, ...prLabels.map((l) => `🏅 ${l}`)];

  return renderActivityCard(
    `${formatTiming(activity.timestamp)} ${typeLabel}`,
    buildActivityMeta(activity),
    activity.activity_type,
    chips,
    mapCapable,
    stats,
    isOwnActivity ? activity.activity_id : null,
    activity.route_polyline || null,
    isOwnActivity ? { type: activity.activity_type, timestamp: activity.timestamp, distance: activity.distance, durationMins: Math.round((activity.duration || 0) / 60) } : null,
    user,
    engagement
  );
}

function renderActivityCard(title, meta, type = "run", chips = [], hasMap = false, stats = [], activityId = null, routePolyline = null, rawActivity = null, user = null, engagement = null) {
  const chipHtml = chips.length
    ? chips.map((chip) => `<span class="chip">${escapeHtml(chip)}</span>`).join("")
    : `<span class="chip">Activity</span>`;
  const mapId = activityId ? `leaflet-${activityId}` : null;
  const mapHtml = hasMap
    ? routePolyline && mapId
      ? `<div class="activity-map" id="${mapId}" data-polyline="${escapeHtml(routePolyline)}" style="z-index:0"></div>`
      : `<div class="activity-map" aria-hidden="true"><div class="map-placeholder">Map preview</div></div>`
    : "";
  const statsHtml = stats.length
    ? stats
        .map(
          (stat) => `
        <div class="activity-stat">
          <span class="label">${escapeHtml(stat.label)}</span>
          <span class="value">${escapeHtml(stat.value)}</span>
        </div>`
        )
        .join("")
    : "";

  const reflectBtn = activityId
    ? `<button class="btn btn-sm btn-outline-secondary reflect-btn" data-activity-id="${escapeHtml(activityId)}">Reflect with coach</button>`
    : "";

  const rawAttrs = rawActivity
    ? ` data-raw-type="${escapeHtml(rawActivity.type)}" data-raw-ts="${escapeHtml(rawActivity.timestamp)}" data-raw-dist="${rawActivity.distance}" data-raw-dur="${rawActivity.durationMins}"`
    : "";

  const avatarInner = user?.profile_picture_url
    ? `<img src="${escapeHtml(API_BASE + user.profile_picture_url)}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />`
    : "";

  const likeBtn = engagement
    ? engagement.isOwn
      ? `<button class="btn btn-sm likers-btn" data-activity-id="${escapeHtml(engagement.activityId || "")}" title="See who liked this">♥ ${engagement.likeCount}</button>`
      : `<button class="btn btn-sm like-btn${engagement.hasLiked ? " liked" : ""}" data-activity-id="${escapeHtml(engagement.activityId || "")}" data-like-id="${escapeHtml(String(engagement.likeId || ""))}" data-has-liked="${engagement.hasLiked}" title="${engagement.hasLiked ? "Unlike" : "Like"}">${engagement.hasLiked ? "♥" : "♡"} ${engagement.likeCount}</button>`
    : "";
  const engagementHtml = engagement
    ? `${likeBtn}<button class="btn btn-sm comment-toggle-btn" data-activity-id="${escapeHtml(engagement.activityId || "")}">💬 ${engagement.commentCount}</button>`
    : "";

  return `
    <article class="activity-card" data-type="${escapeHtml(type)}" data-has-map="${hasMap}" data-activity-id="${activityId || ""}" data-user-id="${escapeHtml(user?.user_id || "")}"${rawAttrs}>
      <div class="activity-header">
        <div class="activity-avatar" aria-hidden="true">${avatarInner}</div>
        <div class="activity-title">
          <div class="activity-meta">${escapeHtml(meta)}</div>
          <h4>${escapeHtml(title)}</h4>
        </div>
      </div>
      <div class="activity-body">${statsHtml}</div>
      ${mapHtml}
      <div class="activity-footer">${chipHtml}${engagementHtml}${reflectBtn}</div>
    </article>
  `;
}

function renderActivityKpis(kpis) {
  return `
    <div class="activity-kpi-grid">
      ${kpis
        .map(
          (kpi) => `
        <div class="activity-kpi-card">
          <span class="kpi-label">${escapeHtml(kpi.label)}</span>
          <span class="kpi-value">${escapeHtml(kpi.value)}</span>
        </div>`
        )
        .join("")}
    </div>
  `;
}

function renderActivityModal() {
  return `
    <div class="modal-overlay" id="activityModal">
      <div class="modal-card">
        <div class="modal-header">
          <div style="flex:1;min-width:0">
            <div class="modal-user-info d-none" id="modalUserInfo">
              <div class="modal-user-avatar" id="modalUserAvatar"></div>
              <span class="modal-user-name" id="modalUserName"></span>
            </div>
            <p class="modal-meta" id="modalMeta"></p>
            <h2 class="modal-title" id="modalTitle"></h2>
          </div>
          <button class="modal-close" id="modalClose">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-stats" id="modalStats"></div>
          <div class="modal-map" id="modalMap">
            <div id="modalLeafletMap"></div>
          </div>
          <div class="modal-charts" id="modalLapCharts" style="display:none">
            <p style="font-size:13px;font-weight:600;margin-bottom:8px">Lap breakdown</p>
            <canvas id="modalLapChart" height="140"></canvas>
          </div>
          <div class="modal-charts" id="modalCharts">
            <p style="font-size:13px;font-weight:600;margin-bottom:8px">Recent sessions</p>
            <canvas id="modalPaceChart" height="120"></canvas>
          </div>
          <div class="modal-charts" id="modalHrCharts" style="display:none">
            <p style="font-size:13px;font-weight:600;margin-bottom:8px">Heart rate trend</p>
            <canvas id="modalHrChart" height="120"></canvas>
          </div>
          <div class="modal-comments" id="modalComments">
            <h5 class="modal-comments-title">Comments</h5>
            <div id="modalCommentList"><p class="text-muted small">No comments yet. Be the first!</p></div>
            <div class="comment-input-row">
              <input type="text" class="form-control form-control-sm" id="commentInput" placeholder="Add a comment..." />
              <button class="btn btn-sm btn-dark" id="commentSubmitBtn">Post</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <div id="modalChips"></div>
          <div class="d-none" id="modalActivityActions" style="display:flex;gap:8px;margin-top:8px;">
            <button class="btn btn-sm btn-outline-secondary" id="modalEditBtn">Edit</button>
            <button class="btn btn-sm btn-outline-danger" id="modalDeleteBtn">Delete</button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderLikersModal() {
  return `
    <div class="modal-overlay" id="likersModal">
      <div class="modal-card" style="max-width:360px">
        <div class="modal-header">
          <h4 class="modal-title" style="font-size:18px">Liked by</h4>
          <button class="modal-close" id="likersModalClose">&times;</button>
        </div>
        <div class="modal-body" id="likersModalList"></div>
      </div>
    </div>
  `;
}

function renderModalComments(activityId) {
  const list = document.getElementById("modalCommentList");
  if (!list || !activityId) return;
  const allComments = state.activityComments.filter((c) => c.activity_id === activityId);
  const topLevel = allComments.filter((c) => !c.parent_comment_id);
  if (!topLevel.length) {
    list.innerHTML = `<p class="text-muted small">No comments yet. Be the first!</p>`;
    return;
  }
  list.innerHTML = topLevel.map((c) => {
    const commenter = state.usersById[c.user_id];
    const isOwn = c.user_id === state.userId;
    const replies = allComments.filter((r) => String(r.parent_comment_id) === String(c.comment_id));

    const repliesHtml = replies.map((r) => {
      const replier = state.usersById[r.user_id];
      const isOwnReply = r.user_id === state.userId;
      return `
        <div class="comment-item comment-reply">
          <div class="comment-header">
            <strong class="comment-author">${escapeHtml(replier?.name || "Athlete")}</strong>
            <span class="text-muted small"> · ${escapeHtml(formatTimeAgo(r.created_at))}</span>
            ${isOwnReply ? `<button class="btn btn-sm delete-comment-btn" data-comment-id="${escapeHtml(String(r.comment_id))}" data-activity-id="${escapeHtml(activityId)}" title="Delete">&times;</button>` : ""}
          </div>
          <p class="comment-body">${escapeHtml(r.content)}</p>
        </div>`;
    }).join("");

    return `
      <div class="comment-item" data-comment-id="${escapeHtml(String(c.comment_id))}">
        <div class="comment-header">
          <strong class="comment-author">${escapeHtml(commenter?.name || "Athlete")}</strong>
          <span class="text-muted small"> · ${escapeHtml(formatTimeAgo(c.created_at))}</span>
          ${isOwn ? `<button class="btn btn-sm delete-comment-btn" data-comment-id="${escapeHtml(String(c.comment_id))}" data-activity-id="${escapeHtml(activityId)}" title="Delete">&times;</button>` : ""}
        </div>
        <p class="comment-body">${escapeHtml(c.content)}</p>
        <div class="comment-actions">
          <button class="btn btn-sm reply-toggle-btn" data-comment-id="${escapeHtml(String(c.comment_id))}">Reply</button>
          ${replies.length ? `<span class="text-muted small">${replies.length} repl${replies.length === 1 ? "y" : "ies"}</span>` : ""}
        </div>
        ${repliesHtml ? `<div class="comment-replies">${repliesHtml}</div>` : ""}
        <div class="reply-input-row d-none" data-for-comment="${escapeHtml(String(c.comment_id))}">
          <input type="text" class="form-control form-control-sm reply-input" placeholder="Write a reply…" />
          <button class="btn btn-sm btn-dark reply-submit-btn" data-parent-id="${escapeHtml(String(c.comment_id))}" data-activity-id="${escapeHtml(activityId)}">Post</button>
        </div>
      </div>`;
  }).join("");

  list.querySelectorAll(".delete-comment-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const commentId = btn.dataset.commentId;
      if (!commentId) return;
      btn.disabled = true;
      try {
        await apiFetch(`/activity_comments/${commentId}`, { method: "DELETE" });
        state.activityComments = state.activityComments.filter((c) => String(c.comment_id) !== commentId);
        renderModalComments(activityId);
      } catch (err) {
        window.alert(`Could not delete comment: ${err.message}`);
        btn.disabled = false;
      }
    });
  });

  list.querySelectorAll(".reply-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const commentId = btn.dataset.commentId;
      const replyRow = list.querySelector(`.reply-input-row[data-for-comment="${commentId}"]`);
      if (!replyRow) return;
      replyRow.classList.toggle("d-none");
      if (!replyRow.classList.contains("d-none")) replyRow.querySelector(".reply-input")?.focus();
    });
  });

  list.querySelectorAll(".reply-submit-btn").forEach((btn) => {
    const replyRow = btn.closest(".reply-input-row");
    const input = replyRow?.querySelector(".reply-input");
    const submitReply = async () => {
      const content = input?.value.trim();
      if (!content) return;
      const parentId = btn.dataset.parentId;
      const actId = btn.dataset.activityId;
      btn.disabled = true;
      try {
        const reply = await apiFetch("/activity_comments", {
          method: "POST",
          body: JSON.stringify({ activity_id: actId, user_id: state.userId, parent_comment_id: parentId, content }),
        });
        state.activityComments.push(reply);
        renderModalComments(actId);
      } catch (err) {
        window.alert(`Reply failed: ${err.message}`);
        btn.disabled = false;
      }
    };
    btn.addEventListener("click", submitReply);
    input?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); submitReply(); } });
  });
}

function renderAddActivityModal() {
  const now = new Date();
  const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

  return `
    <div class="modal-overlay" id="addActivityModal">
      <div class="modal-card plan-modal-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta">Manual Activity</p>
          </div>
          <button class="modal-close" id="addActivityClose">&times;</button>
        </div>
        <div class="modal-body">
          <div class="plan-form-grid">
            <div>
              <label class="form-label">Activity type</label>
              <select class="form-select" id="activityTypeSelect">
                <option value="run">Run</option>
                <option value="bike">Ride</option>
                <option value="swim">Swim</option>
                <option value="walk">Walk</option>
                <option value="hike">Hike</option>
                <option value="weights">Strength</option>
                <option value="mobility">Mobility</option>
                <option value="yoga">Yoga</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label class="form-label">Date and time</label>
              <input class="form-control" id="activityTimestampInput" type="datetime-local" value="${localIso}" />
            </div>
            <div id="activityDistanceWrapper">
              <label class="form-label">Distance (km)</label>
              <input class="form-control" id="activityDistanceInput" type="number" step="0.01" min="0" placeholder="8.5" />
            </div>
            <div>
              <label class="form-label">Duration (minutes)</label>
              <input class="form-control" id="activityDurationInput" type="number" step="1" min="1" placeholder="45" />
            </div>
            <div>
              <label class="form-label">Avg heart rate <span style="color:var(--text-muted);font-size:11px;font-weight:400">(bpm, optional)</span></label>
              <input class="form-control" id="activityHrInput" type="number" min="40" max="220" placeholder="155" />
            </div>
          </div>
          <div id="activityLapsWrapper" style="display:none;margin-top:14px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
              <span style="font-size:13px;font-weight:600">Laps <span style="font-size:11px;color:var(--text-muted);font-weight:400">(optional)</span></span>
              <button type="button" id="addLapBtn" class="btn btn-sm btn-outline-secondary">+ Add lap</button>
            </div>
            <div style="display:grid;grid-template-columns:24px 1fr 1fr 1fr auto;gap:6px;margin-bottom:4px;padding:0 2px">
              <span></span>
              <span style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">km</span>
              <span style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">mm:ss</span>
              <span style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em">bpm</span>
              <span></span>
            </div>
            <div id="lapRowsContainer"></div>
          </div>
          <div class="inline-error mt-3 d-none" id="addActivityError"></div>
          <div class="inline-success mt-3 d-none" id="addActivitySuccess">Activity saved.</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="addActivityCancel">Cancel</button>
          <button class="btn btn-dark" id="addActivitySubmit">Save Activity</button>
        </div>
      </div>
    </div>
  `;
}

function attachActivityCardHandlers() {
  const modal = document.getElementById("activityModal");
  const modalClose = document.getElementById("modalClose");
  if (!modal) return;

  const cards = Array.from(app.querySelectorAll(".activity-card"));
  const modalTitle = modal.querySelector(".modal-title");
  const modalMeta = modal.querySelector(".modal-meta");
  const modalStats = modal.querySelector("#modalStats");
  const modalChips = modal.querySelector("#modalChips");
  const modalMap = modal.querySelector("#modalMap");
  const modalCharts = modal.querySelector("#modalCharts");
  const modalActions = modal.querySelector("#modalActivityActions");

  let currentActivityId = null;

  const closeModal = () => {
    modal.classList.remove("open");
    currentActivityId = null;
    const mapEl = document.getElementById("modalLeafletMap");
    if (mapEl?._leafletMap) { mapEl._leafletMap.remove(); mapEl._leafletMap = null; }
    const chartCanvas = document.getElementById("modalPaceChart");
    if (chartCanvas?._chartInstance) { chartCanvas._chartInstance.destroy(); chartCanvas._chartInstance = null; }
    const lapCanvas = document.getElementById("modalLapChart");
    if (lapCanvas?._chartInstance) { lapCanvas._chartInstance.destroy(); lapCanvas._chartInstance = null; }
    const hrCanvas = document.getElementById("modalHrChart");
    if (hrCanvas?._chartInstance) { hrCanvas._chartInstance.destroy(); hrCanvas._chartInstance = null; }
  };

  function populateModal(card, forceActivityId = null) {
    modalTitle.textContent = card.querySelector("h4")?.textContent || "Activity";
    modalMeta.textContent = card.querySelector(".activity-meta")?.textContent || "";
    modalStats.innerHTML = Array.from(card.querySelectorAll(".activity-stat"))
      .map(
        (stat) => `
          <div class="modal-stat">
            <span class="label">${escapeHtml(stat.querySelector(".label")?.textContent || "")}</span>
            <span class="value">${escapeHtml(stat.querySelector(".value")?.textContent || "")}</span>
          </div>
        `
      )
      .join("");
    modalChips.innerHTML = Array.from(card.querySelectorAll(".chip"))
      .map((chip) => `<span class="chip">${escapeHtml(chip.textContent)}</span>`)
      .join("");

    const hasMap = card.dataset.hasMap === "true";
    const polylineEncoded = card.querySelector("[data-polyline]")?.dataset.polyline || null;

    // Real Leaflet map when polyline is available
    if (hasMap && polylineEncoded && typeof L !== "undefined") {
      modalMap.style.display = "flex";
      const mapEl = document.getElementById("modalLeafletMap");
      if (mapEl) {
        if (mapEl._leafletMap) { mapEl._leafletMap.remove(); mapEl._leafletMap = null; }
        requestAnimationFrame(() => {
          try {
            const coords = decodePolyline(polylineEncoded);
            if (coords.length) {
              const lmap = L.map(mapEl, { zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false });
              L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(lmap);
              const pl = L.polyline(coords, { color: "#111827", weight: 3 }).addTo(lmap);
              lmap.fitBounds(pl.getBounds(), { padding: [12, 12] });
              mapEl._leafletMap = lmap;
            }
          } catch (_e) {}
        });
      }
    } else {
      modalMap.style.display = "none";
    }

    // Pace/distance trend chart for own activities
    const activityType = card.dataset.type || "";
    const activityId = forceActivityId || card.dataset.activityId || null;
    if (activityId && activityType) {
      renderModalPaceChart(activityId, activityType);
      renderModalHrChart(activityId, activityType);
    } else {
      modalCharts.style.display = "none";
      const hrSection = document.getElementById("modalHrCharts");
      if (hrSection) hrSection.style.display = "none";
    }

    // Lap breakdown chart — look up full activity object (own or others')
    const engagementActId = card.querySelector("[data-activity-id]")?.dataset.activityId || null;
    const lookupId = forceActivityId || card.dataset.activityId || engagementActId;
    const fullActivity = lookupId
      ? state.activities.find((a) => String(a.activity_id) === String(lookupId))
      : null;
    const modalLapCharts = document.getElementById("modalLapCharts");
    if (fullActivity?.laps?.length) {
      renderModalLapChart(fullActivity.laps);
    } else {
      if (modalLapCharts) modalLapCharts.style.display = "none";
      const lapCanvas = document.getElementById("modalLapChart");
      if (lapCanvas?._chartInstance) { lapCanvas._chartInstance.destroy(); lapCanvas._chartInstance = null; }
    }

    // Populate user info for other people's activities
    const cardUserId = card.dataset.userId;
    const modalUserInfo = document.getElementById("modalUserInfo");
    const modalUserAvatar = document.getElementById("modalUserAvatar");
    const modalUserName = document.getElementById("modalUserName");
    if (modalUserInfo) {
      if (cardUserId && cardUserId !== state.userId) {
        const cardUser = state.usersById[cardUserId];
        modalUserAvatar.innerHTML = cardUser?.profile_picture_url
          ? `<img src="${escapeHtml(API_BASE + cardUser.profile_picture_url)}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />`
          : "";
        modalUserName.textContent = cardUser?.name || "Athlete";
        modalUserName.dataset.userId = cardUserId;
        modalUserInfo.classList.remove("d-none");
      } else {
        modalUserInfo.classList.add("d-none");
      }
    }

    currentActivityId = forceActivityId || card.dataset.activityId || null;
    if (modalActions) {
      modalActions.classList.toggle("d-none", !card.dataset.activityId);
      modalActions.dataset.rawType = card.dataset.rawType || "";
      modalActions.dataset.rawTs = card.dataset.rawTs || "";
      modalActions.dataset.rawDist = card.dataset.rawDist || "";
      modalActions.dataset.rawDur = card.dataset.rawDur || "";
    }

    // Populate comments for the actual activity (own or others')
    const commentActivityId = forceActivityId || card.dataset.activityId || null;
    renderModalComments(commentActivityId);
    const commentInput = document.getElementById("commentInput");
    if (commentInput) commentInput.value = "";
  }

  cards.forEach((card) => {
    card.addEventListener("click", (event) => {
      // Don't open modal when like/comment/likers buttons are clicked
      if (event.target.closest(".like-btn, .likers-btn, .comment-toggle-btn, .reflect-btn")) return;
      populateModal(card);
      modal.classList.add("open");
    });
  });

  modalClose?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  document.getElementById("modalUserName")?.addEventListener("click", () => {
    const uid = document.getElementById("modalUserName")?.dataset.userId;
    if (uid) { closeModal(); window.location.hash = `#/athlete/${uid}`; }
  });

  // Like buttons (inline on cards)
  app.querySelectorAll(".like-btn").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.stopPropagation();
      const activityId = btn.dataset.activityId;
      const hasLiked = btn.dataset.hasLiked === "true";
      const likeId = btn.dataset.likeId;
      if (!activityId) return;
      btn.disabled = true;
      try {
        if (hasLiked && likeId) {
          await apiFetch(`/activity_likes/${likeId}`, { method: "DELETE" });
          state.activityLikes = state.activityLikes.filter((l) => String(l.like_id) !== likeId);
        } else {
          const newLike = await apiFetch("/activity_likes", {
            method: "POST",
            body: JSON.stringify({ activity_id: activityId, user_id: state.userId }),
          });
          state.activityLikes.push(newLike);
        }
        const newLikes = state.activityLikes.filter((l) => l.activity_id === activityId);
        const newUserLike = newLikes.find((l) => l.user_id === state.userId);
        const newHasLiked = Boolean(newUserLike);
        btn.dataset.hasLiked = String(newHasLiked);
        btn.dataset.likeId = newUserLike?.like_id || "";
        btn.className = `btn btn-sm like-btn${newHasLiked ? " liked" : ""}`;
        btn.title = newHasLiked ? "Unlike" : "Like";
        btn.textContent = `${newHasLiked ? "♥" : "♡"} ${newLikes.length}`;
      } catch (err) {
        window.alert(`Like failed: ${err.message}`);
      } finally {
        btn.disabled = false;
      }
    });
  });

  // Likers button — own activities: show who liked
  const likersModal = document.getElementById("likersModal");
  const likersModalList = document.getElementById("likersModalList");
  document.getElementById("likersModalClose")?.addEventListener("click", () => likersModal?.classList.remove("open"));
  likersModal?.addEventListener("click", (e) => { if (e.target === likersModal) likersModal.classList.remove("open"); });

  app.querySelectorAll(".likers-btn").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const activityId = btn.dataset.activityId;
      if (!activityId || !likersModal || !likersModalList) return;
      const likers = state.activityLikes.filter((l) => l.activity_id === activityId);
      likersModalList.innerHTML = likers.length
        ? likers.map((l) => {
            const u = state.usersById[l.user_id];
            return `<div class="liker-row">${renderAvatarEl(u, "liker-avatar")}<span class="liker-name">${escapeHtml(u?.name || "Athlete")}</span></div>`;
          }).join("")
        : `<p class="text-muted small mb-0">No likes yet.</p>`;
      likersModal.classList.add("open");
    });
  });

  // Comment toggle buttons — open modal focused on comments
  app.querySelectorAll(".comment-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.stopPropagation();
      const activityId = btn.dataset.activityId;
      if (!activityId) return;
      const card = btn.closest(".activity-card");
      if (card) {
        populateModal(card, activityId);
        modal.classList.add("open");
        setTimeout(() => document.getElementById("commentInput")?.focus(), 100);
      }
    });
  });

  // Comment submit
  const commentInput = document.getElementById("commentInput");
  const commentSubmitBtn = document.getElementById("commentSubmitBtn");

  async function submitComment() {
    const content = commentInput?.value.trim();
    if (!content || !currentActivityId) return;
    if (commentSubmitBtn) commentSubmitBtn.disabled = true;
    try {
      const comment = await apiFetch("/activity_comments", {
        method: "POST",
        body: JSON.stringify({ activity_id: currentActivityId, user_id: state.userId, content }),
      });
      state.activityComments.push(comment);
      if (commentInput) commentInput.value = "";
      renderModalComments(currentActivityId);
    } catch (err) {
      window.alert(`Comment failed: ${err.message}`);
    } finally {
      if (commentSubmitBtn) commentSubmitBtn.disabled = false;
    }
  }

  commentSubmitBtn?.addEventListener("click", submitComment);
  commentInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); submitComment(); }
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
    // Capture before closeModal() nulls currentActivityId
    const editId = currentActivityId;
    const rawType = modalActions.dataset.rawType || "run";
    const rawTs   = modalActions.dataset.rawTs   || "";
    const rawDist = modalActions.dataset.rawDist || "";
    const rawDur  = modalActions.dataset.rawDur  || "";
    closeModal();
    const addModal = document.getElementById("addActivityModal");
    if (!addModal) return;
    const typeSelectEl = document.getElementById("activityTypeSelect");
    if (typeSelectEl) { typeSelectEl.value = rawType; typeSelectEl.dispatchEvent(new Event("change")); }
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
    const editActivity = state.activities.find((a) => String(a.activity_id) === String(editId));
    const hrInputEl = document.getElementById("activityHrInput");
    if (hrInputEl) hrInputEl.value = editActivity?.average_heart_rate ? Math.round(editActivity.average_heart_rate) : "";
    if (editActivity?.laps?.length && addModal._populateLapRows) addModal._populateLapRows(editActivity.laps);
    addModal.classList.add("open");
  });

  // "Reflect with coach" buttons — open a per-activity coaching session
  app.querySelectorAll(".reflect-btn").forEach((btn) => {
    btn.addEventListener("click", async (event) => {
      event.stopPropagation(); // don't open the activity modal
      const activityId = btn.dataset.activityId;
      if (!activityId || !state.userId) return;
      btn.disabled = true;
      btn.textContent = "Opening...";
      try {
        // Find or create a reflection session for this specific activity
        const sessions = await apiFetch("/chatbot_sessions");
        const existing = Array.isArray(sessions)
          ? sessions.find(
              (s) =>
                s.user_id === state.userId &&
                s.session_type === "activity_reflection" &&
                s.related_activity_id === activityId
            )
          : null;

        let sessionId;
        if (existing) {
          sessionId = existing.chatbot_id;
        } else {
          const created = await apiFetch("/chatbot_sessions", {
            method: "POST",
            body: JSON.stringify({
              user_id: state.userId,
              session_type: "activity_reflection",
              related_activity_id: activityId,
            }),
          });
          sessionId = created.chatbot_id;
        }

        // Load this session as the active coach session and navigate
        state.coachSessionId = sessionId;
        state.coachMessages = [];
        window.location.hash = "#/coach";
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "Reflect with coach";
        alert(`Could not open coaching session: ${err.message}`);
      }
    });
  });
}

function attachActivityFilters() {
  const typeFilter = document.getElementById("activityTypeFilter");
  if (!typeFilter) return;

  typeFilter.addEventListener("change", () => {
    const selected = typeFilter.value;
    Array.from(app.querySelectorAll(".activity-card")).forEach((card) => {
      if (selected === "all" || card.dataset.type === selected) {
        card.classList.remove("d-none");
      } else {
        card.classList.add("d-none");
      }
    });
  });
}

function attachAddActivityActions() {
  const modal = document.getElementById("addActivityModal");
  if (!modal) return;

  const closeBtn = document.getElementById("addActivityClose");
  const cancelBtn = document.getElementById("addActivityCancel");
  const submitBtn = document.getElementById("addActivitySubmit");
  const errorEl = document.getElementById("addActivityError");
  const successEl = document.getElementById("addActivitySuccess");
  const typeSelect = document.getElementById("activityTypeSelect");
  const timestampInput = document.getElementById("activityTimestampInput");
  const distanceInput = document.getElementById("activityDistanceInput");
  const durationInput = document.getElementById("activityDurationInput");
  const distanceWrapper = document.getElementById("activityDistanceWrapper");
  const lapsWrapper = document.getElementById("activityLapsWrapper");
  const lapRowsContainer = document.getElementById("lapRowsContainer");
  const addLapBtn = document.getElementById("addLapBtn");

  function updateLapIndices() {
    Array.from(lapRowsContainer?.querySelectorAll(".lap-row") || []).forEach((row, i) => {
      const idx = row.querySelector(".lap-index");
      if (idx) idx.textContent = i + 1;
    });
  }

  function buildLapRow() {
    const div = document.createElement("div");
    div.className = "lap-row";
    div.innerHTML = `
      <span class="lap-index">1</span>
      <input class="form-control lap-dist" type="number" step="0.01" min="0" placeholder="km" />
      <input class="form-control lap-dur" type="text" placeholder="mm:ss" />
      <input class="form-control lap-hr" type="number" min="40" max="220" placeholder="bpm" />
      <button type="button" class="btn btn-sm btn-outline-danger lap-remove-btn">&times;</button>
    `;
    div.querySelector(".lap-remove-btn").addEventListener("click", () => {
      div.remove();
      updateLapIndices();
    });
    return div;
  }

  function parseLapRows() {
    const rows = lapRowsContainer?.querySelectorAll(".lap-row") || [];
    const laps = [];
    let idx = 1;
    rows.forEach((row) => {
      const distVal = row.querySelector(".lap-dist")?.value.trim();
      const durVal = row.querySelector(".lap-dur")?.value.trim();
      const hrVal = row.querySelector(".lap-hr")?.value.trim();
      const dist = distVal ? parseFloat(distVal) : null;
      if (!dist || dist <= 0) return;
      let durSec = null;
      if (durVal) {
        const parts = durVal.split(":");
        if (parts.length === 2) {
          const m = parseInt(parts[0], 10);
          const s = parseInt(parts[1], 10);
          if (!isNaN(m) && !isNaN(s)) durSec = m * 60 + s;
        } else {
          const m = parseFloat(durVal);
          if (!isNaN(m)) durSec = Math.round(m * 60);
        }
      }
      const hr = hrVal ? parseFloat(hrVal) : null;
      laps.push({ lap_index: idx++, distance_km: dist, duration_sec: durSec, avg_hr: hr || null });
    });
    return laps.length ? laps : null;
  }

  function populateLapRows(laps) {
    if (!lapRowsContainer) return;
    lapRowsContainer.innerHTML = "";
    laps.forEach((lap) => {
      const row = buildLapRow();
      lapRowsContainer.appendChild(row);
      const distInput = row.querySelector(".lap-dist");
      const durInput = row.querySelector(".lap-dur");
      const hrInput = row.querySelector(".lap-hr");
      if (distInput) distInput.value = lap.distance_km ?? "";
      if (durInput && lap.duration_sec != null) {
        const m = Math.floor(lap.duration_sec / 60);
        const s = String(lap.duration_sec % 60).padStart(2, "0");
        durInput.value = `${m}:${s}`;
      }
      if (hrInput && lap.avg_hr != null) hrInput.value = Math.round(lap.avg_hr);
    });
    updateLapIndices();
  }

  function updateDistanceVisibility() {
    const needsDist = DISTANCE_ACTIVITY_TYPES.has(typeSelect.value);
    if (distanceWrapper) distanceWrapper.style.display = needsDist ? "" : "none";
    if (lapsWrapper) lapsWrapper.style.display = needsDist ? "" : "none";
    if (!needsDist && lapRowsContainer) lapRowsContainer.innerHTML = "";
  }

  typeSelect?.addEventListener("change", updateDistanceVisibility);
  updateDistanceVisibility();

  addLapBtn?.addEventListener("click", () => {
    const row = buildLapRow();
    lapRowsContainer?.appendChild(row);
    updateLapIndices();
  });

  const clearLaps = () => {
    if (lapRowsContainer) lapRowsContainer.innerHTML = "";
    const hrInput = document.getElementById("activityHrInput");
    if (hrInput) hrInput.value = "";
  };

  const closeModal = () => {
    modal.classList.remove("open");
    errorEl?.classList.add("d-none");
    successEl?.classList.add("d-none");
    delete modal.dataset.editActivityId;
    if (submitBtn) submitBtn.textContent = "Save Activity";
    const metaEl = modal.querySelector(".modal-meta");
    if (metaEl) metaEl.textContent = "Manual Activity";
    clearLaps();
  };

  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  // Expose populateLapRows for the edit flow
  modal._populateLapRows = populateLapRows;

  submitBtn?.addEventListener("click", async () => {
    errorEl.classList.add("d-none");
    successEl.classList.add("d-none");

    const needsDist = DISTANCE_ACTIVITY_TYPES.has(typeSelect.value);
    const distance = needsDist ? Number(distanceInput.value) : 0;
    const durationMinutes = Number(durationInput.value);
    const timestamp = timestampInput.value;

    if (!timestamp || (needsDist && (!Number.isFinite(distance) || distance <= 0)) || !Number.isFinite(durationMinutes) || durationMinutes <= 0) {
      errorEl.textContent = needsDist
        ? "Please enter a valid date, distance, and duration."
        : "Please enter a valid date and duration.";
      errorEl.classList.remove("d-none");
      return;
    }

    const hrRaw = document.getElementById("activityHrInput")?.value.trim();
    const avgHr = hrRaw ? parseFloat(hrRaw) : null;
    const laps = needsDist ? parseLapRows() : null;

    const payload = {
      activity_type: typeSelect.value,
      distance,
      duration: Math.round(durationMinutes * 60),
      timestamp: new Date(timestamp).toISOString(),
      average_heart_rate: (avgHr && avgHr > 0) ? avgHr : null,
      laps,
    };

    submitBtn.disabled = true;
    try {
      const editId = modal.dataset.editActivityId;
      if (editId) {
        await apiFetch(`/activities/${editId}`, { method: "PATCH", body: JSON.stringify(payload) });
      } else {
        await apiFetch("/activities", { method: "POST", body: JSON.stringify({ user_id: state.userId, ...payload }) });
      }

      successEl.classList.remove("d-none");
      await ensureActivitiesLoaded(true);
      await sleep(250);
      closeModal();
      await handleRoute();
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
    } finally {
      submitBtn.disabled = false;
    }
  });
}