async function renderClubs() {
  await Promise.all([
    ensureUsersLoaded(),
    ensureClubsLoaded(),
    ensureEventsLoaded(),
    ensureClubMembershipsLoaded(),
  ]);

  // Build admin panel for clubs where the current user is an admin and there are pending requests
  const adminPendingByClub = state.clubs
    .filter((club) => isClubAdmin(club.club_id))
    .map((club) => ({
      club,
      pending: state.clubMemberships.filter((m) => m.club_id === club.club_id && m.status === "pending"),
    }))
    .filter(({ pending }) => pending.length > 0);

  const totalPending = adminPendingByClub.reduce((n, x) => n + x.pending.length, 0);
  const adminPanel = adminPendingByClub.length
    ? `
    <section class="section-block">
      <div class="section-header">
        <h3>Pending join requests</h3>
        <span class="tag">${totalPending} pending</span>
      </div>
      ${adminPendingByClub
        .map(
          ({ club, pending }) => `
        <div class="panel-card mb-2">
          <p class="mini-title">${escapeHtml(club.name)}</p>
          ${pending
            .map((m) => {
              const requester = state.usersById[m.user_id];
              return `
            <div class="pending-request-row">
              <span>${escapeHtml(requester?.name || "Athlete")}</span>
              <div class="d-flex gap-2">
                <button class="btn btn-sm btn-dark approve-member-btn" data-membership-id="${escapeHtml(String(m.membership_id))}">Approve</button>
                <button class="btn btn-sm btn-outline-secondary reject-member-btn" data-membership-id="${escapeHtml(String(m.membership_id))}">Reject</button>
              </div>
            </div>
          `;
            })
            .join("")}
        </div>
      `
        )
        .join("")}
    </section>
  `
    : "";

  app.innerHTML = renderLayout({
    active: "clubs",
    title: "Clubs",
    subtitle: "Find communities, create your own club, and grow your training circle.",
    actions: false,
    content: `
      ${adminPanel}
      <section class="section-block">
        <div class="section-header">
          <h3>Club directory</h3>
          <div class="d-flex gap-2 align-items-center">
            <input type="text" class="form-control form-control-sm" id="clubSearchInput" placeholder="Search clubs..." style="width:200px" />
            <button class="btn btn-dark" id="openClubModalBtn">Create Club</button>
          </div>
        </div>
        <div class="community-grid" id="clubGrid">
          ${
            state.clubs.length
              ? state.clubs.map((club) => renderClubCard(club)).join("")
              : renderInfoCard("No clubs yet", "Create the first club for your training community.")
          }
        </div>
      </section>
    `,
  });

  initLayoutActions();
  attachClubActions();
}

async function renderClubEvents(clubId) {
  await Promise.all([ensureUsersLoaded(), ensureClubsLoaded(), ensureEventsLoaded(), ensureClubMembershipsLoaded()]);

  const club = state.clubs.find((item) => item.club_id === clubId);
  if (!club) {
    app.innerHTML = renderLayout({
      active: "clubs",
      title: "Club Events",
      subtitle: "Every event belongs to a single club, so let's head back to the club directory.",
      actions: false,
      content: renderEmptyState("Club not found", "We could not find that club."),
    });
    initLayoutActions();
    return;
  }

  const sortedEvents = state.events
    .filter((event) => event.club_id === clubId)
    .sort((a, b) => new Date(a.event_date) - new Date(b.event_date));

  const canCreateEvent = isClubAdmin(clubId);

  app.innerHTML = renderLayout({
    active: "clubs",
    title: `${club.name} Events`,
    subtitle: "See what this club's admins have planned and keep the whole community in the loop.",
    actions: false,
    content: `
      <section class="section-block">
        <div class="section-header">
          <div>
            <h3>Club event board</h3>
            <p class="text-muted">${escapeHtml(club.description || "Club events posted by the admin team.")}</p>
          </div>
          <div class="community-actions">
            <button class="btn btn-outline-secondary" id="backToClubsBtn">Back to Clubs</button>
            ${
              canCreateEvent
                ? '<button class="btn btn-dark" id="openEventModalBtn">Create Event</button>'
                : ""
            }
          </div>
        </div>
        ${
          canCreateEvent
            ? ""
            : `
              <div class="mini-card mb-3">
                <p class="mini-title">Club admin posting only</p>
                <p class="mini-body">Members can view events here, while club admins are the ones who post them.</p>
              </div>
            `
        }
        <div class="community-grid">
          ${
            sortedEvents.length
              ? sortedEvents.map((event) => renderEventCard(event)).join("")
              : renderInfoCard("No events yet", "This club has not posted any events yet.")
          }
        </div>
      </section>
    `,
  });

  initLayoutActions();
  attachEventActions(clubId);
}

function renderClubCard(club) {
  const creator = state.usersById[club.created_by];
  const membership = getClubMembership(club.club_id);
  const isAdmin = isClubAdmin(club.club_id);
  const upcomingEvents = state.events.filter((event) => event.club_id === club.club_id).length;
  const membersCount = state.clubMemberships.filter(
    (item) => item.club_id === club.club_id && item.status === "approved"
  ).length;
  const buttonLabel = membership
    ? membership.status === "approved"
      ? "Joined"
      : membership.status === "pending"
        ? "Pending"
        : "Join Club"
    : "Join Club";

  return `
    <article class="community-card" data-club-id="${club.club_id}" data-club-name="${escapeHtml(club.name.toLowerCase())}">
      <div class="community-card-head" style="cursor:pointer">
        <div>
          <h4>${escapeHtml(club.name)}</h4>
          <p class="text-muted">Created by ${escapeHtml(creator?.name || "member")}</p>
        </div>
        <span class="tag">${membersCount} member${membersCount === 1 ? "" : "s"}</span>
      </div>
      <p class="text-muted">${escapeHtml(club.description || "No club description yet.")}</p>
      <p class="text-muted">${upcomingEvents} event${upcomingEvents === 1 ? "" : "s"} posted by club admins.</p>
      <div class="community-actions">
        <button class="btn btn-outline-secondary view-club-events-btn" data-club-id="${club.club_id}">View Events</button>
        <button class="btn btn-outline-secondary view-user-btn" data-user-id="${club.created_by}">View Creator</button>
        ${isAdmin
          ? `<span class="tag" style="align-self:center;font-size:12px">Admin</span>`
          : `<button class="btn ${membership?.status === "approved" ? "btn-dark" : "btn-outline-secondary"} club-join-btn">
              ${buttonLabel}
            </button>`}
      </div>
    </article>
  `;
}

function renderEventCard(event) {
  const club = state.clubs.find((item) => item.club_id === event.club_id);
  return `
    <article class="community-card" data-event-id="${event.event_id}">
      <div class="community-card-head">
        <div>
          <h4>${escapeHtml(event.name)}</h4>
          <p class="text-muted">${escapeHtml(club?.name || "Community club")} - ${escapeHtml(formatShortDate(event.event_date))}</p>
        </div>
        <span class="tag">Club event</span>
      </div>
      <p class="text-muted">${escapeHtml(event.description || "No event description yet.")}</p>
      <div class="community-actions">
        <button class="btn btn-outline-secondary view-club-btn" data-club-id="${event.club_id}">View club</button>
      </div>
    </article>
  `;
}

function renderLeaveClubModal() {
  return `
    <div class="modal-overlay" id="leaveClubModal">
      <div class="modal-card" style="max-width:380px">
        <div class="modal-header">
          <h4 class="modal-title" style="font-size:18px">Leave club</h4>
          <button class="modal-close" id="leaveClubClose">&times;</button>
        </div>
        <div class="modal-body">
          <p id="leaveClubMessage" style="margin:0">Are you sure you want to leave this club?</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="leaveClubCancelBtn">Cancel</button>
          <button class="btn btn-outline-danger" id="leaveClubConfirmBtn">Leave Club</button>
        </div>
      </div>
    </div>
  `;
}

function renderCancelRequestModal() {
  return `
    <div class="modal-overlay" id="cancelRequestModal">
      <div class="modal-card" style="max-width:380px">
        <div class="modal-header">
          <h4 class="modal-title" style="font-size:18px">Cancel join request</h4>
          <button class="modal-close" id="cancelRequestClose">&times;</button>
        </div>
        <div class="modal-body">
          <p id="cancelRequestMessage" style="margin:0">Are you sure you want to cancel your join request?</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="cancelRequestKeepBtn">Keep request</button>
          <button class="btn btn-outline-danger" id="cancelRequestConfirmBtn">Cancel request</button>
        </div>
      </div>
    </div>
  `;
}

function renderKickMemberModal() {
  return `
    <div class="modal-overlay" id="kickMemberModal">
      <div class="modal-card" style="max-width:420px">
        <div class="modal-header">
          <h4 class="modal-title" style="font-size:18px">Remove member</h4>
          <button class="modal-close" id="kickMemberClose">&times;</button>
        </div>
        <div class="modal-body">
          <p style="margin:0 0 12px">Remove <strong id="kickMemberName"></strong> from this club? This action will be reported to platform admins.</p>
          <label class="form-label">Reason <span style="color:var(--text-muted);font-size:11px;font-weight:400">(optional)</span></label>
          <textarea class="form-control" id="kickMemberReason" rows="3" placeholder="e.g. Violation of club rules…"></textarea>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="kickMemberCancelBtn">Cancel</button>
          <button class="btn btn-outline-danger" id="kickMemberConfirmBtn">Remove member</button>
        </div>
      </div>
    </div>
  `;
}

function renderClubModal() {
  return `
    <div class="modal-overlay" id="clubModal">
      <div class="modal-card plan-modal-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta">Community</p>
            <h2 class="modal-title">Create club</h2>
          </div>
          <button class="modal-close" id="clubModalClose">&times;</button>
        </div>
        <div class="modal-body">
          <div class="plan-form-grid">
            <div>
              <label class="form-label">Club name</label>
              <input class="form-control" id="clubNameInput" placeholder="Stride Beirut" />
            </div>
            <div>
              <label class="form-label">Description</label>
              <input class="form-control" id="clubDescriptionInput" placeholder="Weekly runners, rides, and meetups" />
            </div>
          </div>
          <div class="inline-error mt-3 d-none" id="clubError"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="clubCancelBtn">Cancel</button>
          <button class="btn btn-dark" id="clubSubmitBtn">Create Club</button>
        </div>
      </div>
    </div>
  `;
}

function renderClubDetailModal() {
  return `
    <div class="modal-overlay" id="clubDetailModal">
      <div class="modal-card">
        <div class="modal-header">
          <div style="flex:1;min-width:0">
            <p class="modal-meta">Community</p>
            <h2 class="modal-title" id="clubDetailTitle"></h2>
          </div>
          <button class="modal-close" id="clubDetailClose">&times;</button>
        </div>
        <div class="modal-body">
          <div class="modal-stats" id="clubDetailStats"></div>
          <div id="clubDetailInfo" style="margin-top:12px"></div>
          <div class="modal-tabs" style="margin-top:16px">
            <button class="modal-tab-btn active" data-tab="members">Members</button>
            <button class="modal-tab-btn" data-tab="leaderboard">Leaderboard</button>
          </div>
          <div id="clubDetailTabMembers"></div>
          <div id="clubDetailTabLeaderboard" style="display:none"></div>
        </div>
        <div class="modal-footer" id="clubDetailFooter"></div>
      </div>
    </div>
  `;
}

function renderEventModal() {
  const clubOptions = (state.clubs || [])
    .map((club) => `<option value="${club.club_id}">${escapeHtml(club.name)}</option>`)
    .join("");

  return `
    <div class="modal-overlay" id="eventModal">
      <div class="modal-card plan-modal-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta">Community</p>
            <h2 class="modal-title">Create event</h2>
          </div>
          <button class="modal-close" id="eventModalClose">&times;</button>
        </div>
        <div class="modal-body">
          <div class="plan-form-grid">
            <div>
              <label class="form-label">Club</label>
              <select class="form-select" id="eventClubSelect">
                ${clubOptions || '<option value="">No clubs yet</option>'}
              </select>
            </div>
            <div>
              <label class="form-label">Event date</label>
              <input class="form-control" id="eventDateInput" type="date" />
            </div>
            <div>
              <label class="form-label">Event name</label>
              <input class="form-control" id="eventNameInput" placeholder="Saturday Long Run" />
            </div>
            <div>
              <label class="form-label">Description</label>
              <input class="form-control" id="eventDescriptionInput" placeholder="Meet at the seafront at 7 AM" />
            </div>
          </div>
          <div class="inline-error mt-3 d-none" id="eventError"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline-secondary" id="eventCancelBtn">Cancel</button>
          <button class="btn btn-dark" id="eventSubmitBtn">Create Event</button>
        </div>
      </div>
    </div>
  `;
}

function attachClubActions() {
  const clubSearchInput = document.getElementById("clubSearchInput");
  clubSearchInput?.addEventListener("input", () => {
    const term = clubSearchInput.value.trim().toLowerCase();
    document.querySelectorAll("#clubGrid .community-card[data-club-name]").forEach((card) => {
      card.style.display = !term || card.dataset.clubName.includes(term) ? "" : "none";
    });
  });

  const openBtn = document.getElementById("openClubModalBtn");
  const modal = document.getElementById("clubModal");
  const closeBtn = document.getElementById("clubModalClose");
  const cancelBtn = document.getElementById("clubCancelBtn");
  const submitBtn = document.getElementById("clubSubmitBtn");
  const errorEl = document.getElementById("clubError");

  const closeModal = () => {
    modal?.classList.remove("open");
    errorEl?.classList.add("d-none");
  };

  openBtn?.addEventListener("click", () => modal?.classList.add("open"));
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  submitBtn?.addEventListener("click", async () => {
    errorEl.classList.add("d-none");
    const clubName = document.getElementById("clubNameInput").value.trim();
    if (!clubName) {
      errorEl.textContent = "Club name is required.";
      errorEl.classList.remove("d-none");
      return;
    }
    submitBtn.disabled = true;
    try {
      const club = await apiFetch("/clubs", {
        method: "POST",
        body: JSON.stringify({
          name: clubName,
          description: document.getElementById("clubDescriptionInput").value.trim(),
          created_by: state.userId,
        }),
      });
      await apiFetch("/club_memberships", {
        method: "POST",
        body: JSON.stringify({
          club_id: club.club_id,
          user_id: state.userId,
          role: "club_admin",
          status: "approved",
        }),
      });
      await Promise.all([ensureClubsLoaded(true), ensureClubMembershipsLoaded(true)]);
      closeModal();
      await renderClubs();
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
    } finally {
      submitBtn.disabled = false;
    }
  });

  Array.from(document.querySelectorAll(".club-join-btn")).forEach((button) => {
    const card = button.closest(".community-card");
    const clubId = card?.dataset.clubId;
    const membership = getClubMembership(clubId);
    button.addEventListener("click", async () => {
      if (!clubId) return;

      // Already a full member — offer to leave
      if (membership?.status === "approved") {
        const club = state.clubs.find((c) => c.club_id === clubId);
        openLeaveClubModal(clubId, membership.membership_id, club?.name || "this club");
        return;
      }

      // Request is pending — open cancel modal
      if (membership?.status === "pending") {
        const club = state.clubs.find((c) => c.club_id === clubId);
        openCancelRequestModal(clubId, membership.membership_id, club?.name || "this club");
        return;
      }

      // No membership — request to join (pending, awaiting admin approval)
      button.disabled = true;
      try {
        await apiFetch("/club_memberships", {
          method: "POST",
          body: JSON.stringify({
            club_id: clubId,
            user_id: state.userId,
            role: "member",
            status: "pending",
          }),
        });
        await ensureClubMembershipsLoaded(true);
        await renderClubs();
      } catch (error) {
        window.alert(`Club action failed: ${error.message}`);
        button.disabled = false;
      }
    });
  });

  // Admin: approve pending member
  Array.from(document.querySelectorAll(".approve-member-btn")).forEach((btn) => {
    btn.addEventListener("click", async () => {
      const membershipId = btn.dataset.membershipId;
      if (!membershipId) return;
      btn.disabled = true;
      try {
        await apiFetch(`/club_memberships/${membershipId}/approve`, { method: "POST" });
        await ensureClubMembershipsLoaded(true);
        await renderClubs();
      } catch (err) {
        window.alert(`Approve failed: ${err.message}`);
        btn.disabled = false;
      }
    });
  });

  // Admin: reject pending member
  Array.from(document.querySelectorAll(".reject-member-btn")).forEach((btn) => {
    btn.addEventListener("click", async () => {
      const membershipId = btn.dataset.membershipId;
      if (!membershipId) return;
      btn.disabled = true;
      try {
        await apiFetch(`/club_memberships/${membershipId}/reject`, { method: "POST" });
        await ensureClubMembershipsLoaded(true);
        await renderClubs();
      } catch (err) {
        window.alert(`Reject failed: ${err.message}`);
        btn.disabled = false;
      }
    });
  });

  Array.from(document.querySelectorAll(".view-club-events-btn")).forEach((button) => {
    button.addEventListener("click", () => {
      const clubId = button.dataset.clubId;
      if (clubId) {
        window.location.hash = `#/clubs/${clubId}/events`;
      }
    });
  });

  // Club detail modal: close on X or backdrop
  const clubDetailModal = document.getElementById("clubDetailModal");
  document.getElementById("clubDetailClose")?.addEventListener("click", () => clubDetailModal?.classList.remove("open"));
  clubDetailModal?.addEventListener("click", (e) => { if (e.target === clubDetailModal) clubDetailModal.classList.remove("open"); });

  // Club card click (not on buttons) → open detail modal
  Array.from(document.querySelectorAll("#clubGrid .community-card[data-club-id]")).forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      const club = state.clubs.find((c) => c.club_id === card.dataset.clubId);
      if (club) openClubDetailModal(club);
    });
  });

  // Leave club modal
  const leaveModal = document.getElementById("leaveClubModal");
  document.getElementById("leaveClubClose")?.addEventListener("click", () => leaveModal?.classList.remove("open"));
  document.getElementById("leaveClubCancelBtn")?.addEventListener("click", () => leaveModal?.classList.remove("open"));
  leaveModal?.addEventListener("click", (e) => { if (e.target === leaveModal) leaveModal.classList.remove("open"); });
  document.getElementById("leaveClubConfirmBtn")?.addEventListener("click", async () => {
    const membershipId = leaveModal?.dataset.membershipId;
    if (!membershipId) return;
    const btn = document.getElementById("leaveClubConfirmBtn");
    if (btn) btn.disabled = true;
    try {
      await apiFetch(`/club_memberships/${membershipId}`, { method: "DELETE" });
      leaveModal?.classList.remove("open");
      document.getElementById("clubDetailModal")?.classList.remove("open");
      await ensureClubMembershipsLoaded(true);
      await renderClubs();
    } catch (err) {
      window.alert(`Failed to leave club: ${err.message}`);
      if (btn) btn.disabled = false;
    }
  });

  // Cancel request modal
  const cancelModal = document.getElementById("cancelRequestModal");
  document.getElementById("cancelRequestClose")?.addEventListener("click", () => cancelModal?.classList.remove("open"));
  document.getElementById("cancelRequestKeepBtn")?.addEventListener("click", () => cancelModal?.classList.remove("open"));
  cancelModal?.addEventListener("click", (e) => { if (e.target === cancelModal) cancelModal.classList.remove("open"); });
  document.getElementById("cancelRequestConfirmBtn")?.addEventListener("click", async () => {
    const membershipId = cancelModal?.dataset.membershipId;
    if (!membershipId) return;
    const btn = document.getElementById("cancelRequestConfirmBtn");
    if (btn) btn.disabled = true;
    try {
      await apiFetch(`/club_memberships/${membershipId}`, { method: "DELETE" });
      cancelModal?.classList.remove("open");
      await ensureClubMembershipsLoaded(true);
      await renderClubs();
    } catch (err) {
      window.alert(`Failed to cancel request: ${err.message}`);
      if (btn) btn.disabled = false;
    }
  });

  // Kick member modal
  const kickModal = document.getElementById("kickMemberModal");
  document.getElementById("kickMemberClose")?.addEventListener("click", () => kickModal?.classList.remove("open"));
  document.getElementById("kickMemberCancelBtn")?.addEventListener("click", () => kickModal?.classList.remove("open"));
  kickModal?.addEventListener("click", (e) => { if (e.target === kickModal) kickModal.classList.remove("open"); });
  document.getElementById("kickMemberConfirmBtn")?.addEventListener("click", async () => {
    const membershipId = kickModal?.dataset.membershipId;
    if (!membershipId) return;
    const btn = document.getElementById("kickMemberConfirmBtn");
    if (btn) btn.disabled = true;
    const reason = document.getElementById("kickMemberReason")?.value.trim() || null;
    try {
      await apiFetch(`/club_memberships/${membershipId}/kick`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      kickModal?.classList.remove("open");
      document.getElementById("clubDetailModal")?.classList.remove("open");
      await ensureClubMembershipsLoaded(true);
      await renderClubs();
      showToast("Member removed from club.");
    } catch (err) {
      window.alert(`Failed to remove member: ${err.message}`);
      if (btn) btn.disabled = false;
    }
  });

  attachUserLinkActions();
}

function openLeaveClubModal(clubId, membershipId, clubName) {
  const modal = document.getElementById("leaveClubModal");
  if (!modal) return;
  const msg = document.getElementById("leaveClubMessage");
  if (msg) msg.textContent = `Are you sure you want to leave "${clubName}"?`;
  modal.dataset.clubId = clubId;
  modal.dataset.membershipId = membershipId;
  modal.classList.add("open");
}

function openCancelRequestModal(clubId, membershipId, clubName) {
  const modal = document.getElementById("cancelRequestModal");
  if (!modal) return;
  const msg = document.getElementById("cancelRequestMessage");
  if (msg) msg.textContent = `Cancel your join request for "${clubName}"? You will need to request again to join.`;
  modal.dataset.clubId = clubId;
  modal.dataset.membershipId = membershipId;
  modal.classList.add("open");
}

function openKickMemberModal(membershipId, userName) {
  const modal = document.getElementById("kickMemberModal");
  if (!modal) return;
  const nameEl = document.getElementById("kickMemberName");
  if (nameEl) nameEl.textContent = userName;
  const reasonEl = document.getElementById("kickMemberReason");
  if (reasonEl) reasonEl.value = "";
  modal.dataset.membershipId = membershipId;
  modal.classList.add("open");
}

function openClubDetailModal(club) {
  const modal = document.getElementById("clubDetailModal");
  if (!modal) return;

  const approvedMembers = state.clubMemberships.filter(
    (m) => m.club_id === club.club_id && m.status === "approved"
  );
  const clubEvents = state.events.filter((e) => e.club_id === club.club_id);
  const creator = state.usersById[club.created_by];
  const membership = getClubMembership(club.club_id);

  document.getElementById("clubDetailTitle").textContent = club.name;

  document.getElementById("clubDetailStats").innerHTML = `
    <div class="modal-stat">
      <span class="value">${approvedMembers.length}</span>
      <span class="label">Members</span>
    </div>
    <div class="modal-stat">
      <span class="value">${clubEvents.length}</span>
      <span class="label">Events</span>
    </div>
  `;

  document.getElementById("clubDetailInfo").innerHTML = `
    ${club.description ? `<p class="text-muted">${escapeHtml(club.description)}</p>` : ""}
    ${creator ? `<p class="text-muted" style="font-size:13px;margin-top:4px">Created by <span class="modal-user-name" data-user-id="${creator.user_id}" style="cursor:pointer">${escapeHtml(creator.name || creator.username || "member")}</span></p>` : ""}
  `;

  // Members tab
  const currentUserIsAdmin = isClubAdmin(club.club_id);
  const memberRows = approvedMembers.map((m) => {
    const user = state.usersById[m.user_id];
    if (!user) return "";
    const avatarHtml = user.profile_picture_url
      ? `<img src="${escapeHtml(API_BASE + user.profile_picture_url)}" alt="" />`
      : "";
    const isMemberAdmin = m.role === "club_admin";
    const isCurrentUser = m.user_id === state.userId;
    const showKick = currentUserIsAdmin && !isMemberAdmin && !isCurrentUser;
    return `
      <div class="follows-list-item" data-user-id="${user.user_id}" style="cursor:pointer">
        <div class="modal-user-avatar">${avatarHtml}</div>
        <span class="follows-user-name">${escapeHtml(user.name || user.username || "Athlete")}</span>
        ${isMemberAdmin ? `<span class="tag" style="margin-left:auto;font-size:11px">Admin</span>` : ""}
        ${showKick ? `<button class="btn btn-sm btn-outline-danger kick-member-btn" data-membership-id="${escapeHtml(String(m.membership_id))}" data-user-name="${escapeHtml(user.name || user.username || "Athlete")}" style="margin-left:${isMemberAdmin ? "4px" : "auto"}">Remove</button>` : ""}
      </div>
    `;
  }).filter(Boolean).join("");

  document.getElementById("clubDetailTabMembers").innerHTML = approvedMembers.length
    ? memberRows
    : `<p class="text-muted">No members yet.</p>`;

  if (currentUserIsAdmin) {
    modal.querySelectorAll(".kick-member-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openKickMemberModal(btn.dataset.membershipId, btn.dataset.userName);
      });
    });
  }

  // Leaderboard tab — rank members by distance this calendar month
  const monthStart = new Date();
  monthStart.setDate(1); monthStart.setHours(0, 0, 0, 0);

  const leaderboard = approvedMembers.map((m) => {
    const user = state.usersById[m.user_id];
    const memberActivities = state.activities.filter(
      (a) => a.user_id === m.user_id && new Date(a.timestamp) >= monthStart
    );
    const totalKm = memberActivities.reduce((s, a) => s + (a.distance || 0), 0);
    return { user, totalKm, sessions: memberActivities.length, role: m.role };
  }).sort((a, b) => b.totalKm - a.totalKm);

  const leaderboardRows = leaderboard.map((entry, i) => {
    if (!entry.user) return "";
    const avatarHtml = entry.user.profile_picture_url
      ? `<img src="${escapeHtml(API_BASE + entry.user.profile_picture_url)}" alt="" style="width:100%;height:100%;object-fit:cover;border-radius:50%"/>`
      : "";
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}`;
    return `
      <div class="leaderboard-row" data-user-id="${entry.user.user_id}" style="cursor:pointer">
        <span class="leaderboard-rank">${medal}</span>
        <div class="modal-user-avatar">${avatarHtml}</div>
        <div class="leaderboard-info">
          <div class="leaderboard-name">${escapeHtml(entry.user.name || entry.user.username || "Athlete")}</div>
        </div>
        <div class="leaderboard-stats">
          <div class="leaderboard-distance">${entry.totalKm.toFixed(1)} km</div>
          <div class="leaderboard-sessions">${entry.sessions} session${entry.sessions !== 1 ? "s" : ""}</div>
        </div>
      </div>
    `;
  }).filter(Boolean).join("");

  document.getElementById("clubDetailTabLeaderboard").innerHTML = leaderboard.length
    ? leaderboardRows
    : `<p class="text-muted">No activity data this month yet.</p>`;

  // Tab switching
  modal.querySelectorAll(".modal-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      modal.querySelectorAll(".modal-tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      document.getElementById("clubDetailTabMembers").style.display = tab === "members" ? "" : "none";
      document.getElementById("clubDetailTabLeaderboard").style.display = tab === "leaderboard" ? "" : "none";
    });
  });
  // Reset to members tab on open
  modal.querySelectorAll(".modal-tab-btn").forEach((b) => b.classList.remove("active"));
  modal.querySelector(".modal-tab-btn[data-tab='members']")?.classList.add("active");
  document.getElementById("clubDetailTabMembers").style.display = "";
  document.getElementById("clubDetailTabLeaderboard").style.display = "none";

  const joinLabel = membership?.status === "approved" ? "Joined" : membership?.status === "pending" ? "Pending" : "Join Club";
  const joinBtnClass = membership?.status === "approved" ? "btn-dark" : "btn-outline-secondary";

  document.getElementById("clubDetailFooter").innerHTML = `
    <button class="btn btn-outline-secondary" id="clubDetailEventsBtn">View Events</button>
    ${currentUserIsAdmin
      ? `<span class="tag" style="align-self:center">Admin</span>`
      : `<button class="btn ${joinBtnClass}" id="clubDetailJoinBtn">${joinLabel}</button>`}
  `;

  modal.classList.add("open");

  document.getElementById("clubDetailEventsBtn")?.addEventListener("click", () => {
    modal.classList.remove("open");
    window.location.hash = `#/clubs/${club.club_id}/events`;
  });

  const joinBtn = document.getElementById("clubDetailJoinBtn");
  joinBtn?.addEventListener("click", async () => {
    const current = getClubMembership(club.club_id);
    if (current?.status === "approved") {
      modal.classList.remove("open");
      openLeaveClubModal(club.club_id, current.membership_id, club.name);
      return;
    }
    if (current?.status === "pending") {
      modal.classList.remove("open");
      openCancelRequestModal(club.club_id, current.membership_id, club.name);
      return;
    }
    joinBtn.disabled = true;
    try {
      await apiFetch("/club_memberships", {
        method: "POST",
        body: JSON.stringify({ club_id: club.club_id, user_id: state.userId, role: "member", status: "pending" }),
      });
      await ensureClubMembershipsLoaded(true);
      modal.classList.remove("open");
      await renderClubs();
    } catch (err) {
      window.alert(`Failed: ${err.message}`);
      joinBtn.disabled = false;
    }
  });

  // Creator name + member/leaderboard row click → navigate to profile
  modal.querySelectorAll("[data-user-id]").forEach((el) => {
    el.addEventListener("click", (e) => {
      if (e.target.closest("button")) return;
      const uid = el.dataset.userId;
      modal.classList.remove("open");
      window.location.hash = uid === state.userId ? "#/profile" : `#/athlete/${uid}`;
    });
  });
}

function attachEventActions(clubId) {
  const openBtn = document.getElementById("openEventModalBtn");
  const modal = document.getElementById("eventModal");
  const closeBtn = document.getElementById("eventModalClose");
  const cancelBtn = document.getElementById("eventCancelBtn");
  const submitBtn = document.getElementById("eventSubmitBtn");
  const errorEl = document.getElementById("eventError");
  const clubSelect = document.getElementById("eventClubSelect");
  const backBtn = document.getElementById("backToClubsBtn");

  const closeModal = () => {
    modal?.classList.remove("open");
    errorEl?.classList.add("d-none");
  };

  const prepareModal = () => {
    if (!clubSelect) return;
    clubSelect.value = clubId || clubSelect.value;
    clubSelect.disabled = Boolean(clubId);
  };

  openBtn?.addEventListener("click", () => {
    prepareModal();
    modal?.classList.add("open");
  });
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);
  modal?.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });

  submitBtn?.addEventListener("click", async () => {
    errorEl.classList.add("d-none");
    submitBtn.disabled = true;
    try {
      await apiFetch("/events", {
        method: "POST",
        body: JSON.stringify({
          club_id: clubId || document.getElementById("eventClubSelect").value,
          created_by: state.userId,
          name: document.getElementById("eventNameInput").value.trim(),
          description: document.getElementById("eventDescriptionInput").value.trim(),
          event_date: document.getElementById("eventDateInput").value,
        }),
      });
      await ensureEventsLoaded(true);
      closeModal();
      await renderClubEvents(clubId);
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
    } finally {
      submitBtn.disabled = false;
    }
  });

  Array.from(document.querySelectorAll(".view-club-btn")).forEach((button) => {
    button.addEventListener("click", () => {
      const targetClubId = button.dataset.clubId;
      window.location.hash = targetClubId ? `#/clubs/${targetClubId}/events` : "#/clubs";
    });
  });

  backBtn?.addEventListener("click", () => {
    window.location.hash = "#/clubs";
  });
}