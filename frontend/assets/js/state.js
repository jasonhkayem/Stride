const app = document.getElementById("app");

const API_BASE = "";
const STORAGE_KEYS = {
  userId: "stride.userId",
  role: "stride.platformRole",
  token: "stride.token",
};

const DEFAULT_COACH_PROMPT = "You are a helpful running coach assistant.";

const STRAVA_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="15" height="15" style="vertical-align:middle;margin-right:6px;flex-shrink:0" aria-hidden="true"><path fill="#FC4C02" d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.581-5.858l2.514 4.917H6.51L12 2.06 17.487 12H14.97l-2.984-5.942z"/></svg>`;
const GOOGLE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" style="vertical-align:middle;margin-right:8px;flex-shrink:0" aria-hidden="true"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>`;

const state = {
  user: null,
  userId: localStorage.getItem(STORAGE_KEYS.userId) || null,
  platformRole: localStorage.getItem(STORAGE_KEYS.role) || null,
  token: localStorage.getItem(STORAGE_KEYS.token) || null,
  users: [],
  usersById: {},
  activities: [],
  clubs: [],
  events: [],
  clubMemberships: [],
  trainingTemplates: [],
  stravaStatus: null,
  following: [],
  followingMap: {},
  coachSessionId: null,
  coachSessions: [],
  coachMessages: [],
  trainingPlan: null,
  adminOverview: null,
  adminUsers: null,
  activityLikes: [],
  activityComments: [],
  eventRegistrations: [],
  personalRecords: {},
  completedPlanSessions: [],
  completedPlanSessionsMap: {},
  completedPlanSessionsVersionId: null,
};

const protectedRoutes = new Set([
  "#/dashboard",
  "#/activities",
  "#/training-plan",
  "#/coach",
  "#/profile",
  "#/clubs",
  "#/admin",
]);


function apiUrl(path) {
  return `${API_BASE}${path}`;
}

async function apiFetch(path, options = {}) {
  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(state.token ? { "Authorization": `Bearer ${state.token}` } : {}),
    ...(state.platformRole === "super_admin" && state.userId
      ? { "X-Admin-User-Id": state.userId }
      : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(apiUrl(path), { ...options, headers });
  } catch (_networkErr) {
    throw new Error("Cannot reach the server. Make sure the backend is running.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && state.token) {
      clearAuth();
      window.location.hash = "#/login";
      return;
    }
    const errorText = formatApiError(data);
    throw new Error(errorText);
  }
  return data;
}

function formatApiError(data) {
  let msg = "";
  if (typeof data?.error === "string" && data.error.trim()) msg = data.error;
  else if (typeof data?.detail === "string" && data.detail.trim()) msg = data.detail;
  else if (data?.errors && typeof data.errors === "object") {
    const firstField = Object.keys(data.errors)[0];
    const value = data.errors[firstField];
    if (Array.isArray(value) && value.length) msg = value[0];
    else if (typeof value === "string") msg = value;
  }
  if (!msg) msg = "Request failed";
  return msg.charAt(0).toUpperCase() + msg.slice(1);
}

function setAuth(user, token) {
  state.user = user;
  state.userId = user?.user_id || null;
  state.platformRole = user?.platform_role || "user";
  state.token = token || null;

  if (state.userId) {
    localStorage.setItem(STORAGE_KEYS.userId, state.userId);
    localStorage.setItem(STORAGE_KEYS.role, state.platformRole);
  }
  if (state.token) {
    localStorage.setItem(STORAGE_KEYS.token, state.token);
  }
}

function clearAuth() {
  state.user = null;
  state.userId = null;
  state.platformRole = null;
  state.token = null;
  state.coachSessionId = null;
  state.coachSessions = [];
  state.coachMessages = [];
  state.trainingPlan = null;
  state.stravaStatus = null;
  state.adminOverview = null;
  state.adminUsers = null;
  state.completedPlanSessions = [];
  state.completedPlanSessionsMap = {};
  state.completedPlanSessionsVersionId = null;
  localStorage.removeItem(STORAGE_KEYS.userId);
  localStorage.removeItem(STORAGE_KEYS.role);
  localStorage.removeItem(STORAGE_KEYS.token);
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `stride-toast stride-toast--${type}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span><button class="stride-toast__close" aria-label="Dismiss">&times;</button>`;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("stride-toast--visible"));
  const dismiss = () => {
    toast.classList.remove("stride-toast--visible");
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  };
  toast.querySelector(".stride-toast__close").addEventListener("click", dismiss);
  setTimeout(dismiss, 5000);
}

async function loadCurrentUser() {
  if (!state.userId) return null;
  const user = await apiFetch(`/auth/me/${state.userId}`);
  setAuth(user, state.token); // preserve the token already in state
  return user;
}


function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function ensureUsersLoaded() {
  if (state.users.length) return state.users;
  const users = await apiFetch("/users");
  state.users = Array.isArray(users) ? users : [];
  state.usersById = Object.fromEntries(state.users.map((user) => [user.user_id, user]));
  return state.users;
}

async function ensureActivitiesLoaded(force = false) {
  if (!force && state.activities.length) return state.activities;
  const activities = await apiFetch("/activities");
  state.activities = (Array.isArray(activities) ? activities : []).sort(
    (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
  );
  computePersonalRecords();
  return state.activities;
}

async function ensureClubsLoaded(force = false) {
  if (!force && state.clubs.length) return state.clubs;
  const clubs = await apiFetch("/clubs");
  state.clubs = Array.isArray(clubs) ? clubs : [];
  return state.clubs;
}

async function ensureEventsLoaded(force = false) {
  if (!force && state.events.length) return state.events;
  const events = await apiFetch("/events");
  state.events = Array.isArray(events) ? events : [];
  return state.events;
}

async function ensureClubMembershipsLoaded(force = false) {
  if (!force && state.clubMemberships.length) return state.clubMemberships;
  const memberships = await apiFetch("/club_memberships");
  state.clubMemberships = Array.isArray(memberships) ? memberships : [];
  return state.clubMemberships;
}

async function ensureActivityLikesLoaded(force = false) {
  if (!force && state.activityLikes.length) return state.activityLikes;
  const likes = await apiFetch("/activity_likes");
  state.activityLikes = Array.isArray(likes) ? likes : [];
  return state.activityLikes;
}

async function ensureActivityCommentsLoaded(force = false) {
  if (!force && state.activityComments.length) return state.activityComments;
  const comments = await apiFetch("/activity_comments");
  state.activityComments = Array.isArray(comments) ? comments : [];
  return state.activityComments;
}

async function ensureEventRegistrationsLoaded(force = false) {
  if (!force && state.eventRegistrations.length) return state.eventRegistrations;
  const regs = await apiFetch("/event_registrations");
  state.eventRegistrations = Array.isArray(regs) ? regs : [];
  return state.eventRegistrations;
}

async function ensureTrainingTemplatesLoaded(force = false) {
  if (!force && state.trainingTemplates.length) return state.trainingTemplates;
  const templates = await apiFetch("/training_plan_templates");
  state.trainingTemplates = Array.isArray(templates) ? templates : [];
  return state.trainingTemplates;
}

async function ensureStravaStatusLoaded(force = false) {
  if (!state.userId) return null;
  if (!force && state.stravaStatus) return state.stravaStatus;
  const status = await apiFetch(`/users/${state.userId}/strava`);
  state.stravaStatus = status;
  return status;
}

async function ensureFollowingLoaded(force = false) {
  if (!state.userId) return [];
  if (!force && state.following.length) return state.following;
  const following = await apiFetch(`/user_follows/following/${state.userId}`);
  state.following = Array.isArray(following) ? following : [];
  state.followingMap = Object.fromEntries(
    state.following.map((relation) => [relation.following_id, relation])
  );
  return state.following;
}

async function ensureTrainingPlanLoaded(force = false) {
  if (!state.userId) return null;
  if (!force && state.trainingPlan) return state.trainingPlan;

  const profile = await apiFetch(`/users/${state.userId}/full`);
  const plans = profile.user_training_plans || [];
  if (!plans.length) {
    state.trainingPlan = null;
    return null;
  }

  const plan = await apiFetch(`/user_training_plans/${plans[0].user_plan_id}/full`);
  state.trainingPlan = plan;
  return plan;
}

async function ensureCompletedPlanSessionsLoaded(versionId, force = false) {
  if (!state.userId || !versionId) return [];
  if (!force && state.completedPlanSessionsVersionId === String(versionId)) {
    return state.completedPlanSessions;
  }
  const sessions = await apiFetch(`/completed_plan_sessions?version_id=${versionId}`);
  state.completedPlanSessions = Array.isArray(sessions) ? sessions : [];
  state.completedPlanSessionsVersionId = String(versionId);
  state.completedPlanSessionsMap = Object.fromEntries(
    state.completedPlanSessions.map((s) => [
      `${s.version_id}_${s.week_index}_${s.session_index}`,
      s,
    ])
  );
  return state.completedPlanSessions;
}

async function ensureCoachLoaded(force = false) {
  if (!state.userId) return null;

  // Reload session list if empty or forced
  if (!state.coachSessions.length || force) {
    const sessions = await apiFetch("/chatbot_sessions");
    state.coachSessions = (Array.isArray(sessions) ? sessions : [])
      .filter((s) => s.user_id === state.userId && s.session_type === "coach")
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  }

  // If active session ID is set but not in the list (e.g. stale localStorage), clear it
  if (
    state.coachSessionId &&
    !state.coachSessions.some((s) => s.chatbot_id === state.coachSessionId)
  ) {
    state.coachSessionId = null;
  }

  // Load messages for active session if not cached
  if (state.coachSessionId && (!state.coachMessages.length || force)) {
    const messages = await apiFetch(`/chatbot_sessions/${state.coachSessionId}/messages?limit=50`);
    state.coachMessages = Array.isArray(messages) ? messages : [];
  }
  return state.coachMessages;
}

async function ensureAdminLoaded(force = false) {
  if (state.platformRole !== "super_admin") return null;
  if (!force && state.adminOverview && state.adminUsers) {
    return { overview: state.adminOverview, users: state.adminUsers };
  }

  const [overview, users] = await Promise.all([
    apiFetch("/admin/overview?days=30"),
    apiFetch("/admin/users?page=1&page_size=10"),
  ]);
  state.adminOverview = overview;
  state.adminUsers = users;
  return { overview, users };
}


function getCurrentUserActivities() {
  return state.activities.filter((activity) => activity.user_id === state.userId);
}

function getCurrentPlanVersion() {
  if (!state.trainingPlan) return null;
  const versions = state.trainingPlan.versions || [];
  const currentVersionId = state.trainingPlan.current_version_id;
  return (
    versions.find((version) => version.version_id === currentVersionId) ||
    versions[versions.length - 1] ||
    null
  );
}