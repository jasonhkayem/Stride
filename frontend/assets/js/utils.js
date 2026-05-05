function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

const DISTANCE_ACTIVITY_TYPES = new Set(["run", "bike", "swim", "walk", "hike"]);

function formatActivityType(value) {
  const mapping = {
    run: "Run",
    bike: "Ride",
    swim: "Swim",
    walk: "Walk",
    hike: "Hike",
    weights: "Strength",
    mobility: "Mobility",
    yoga: "Yoga",
    other: "Other",
  };
  return mapping[value] || "Activity";
}

function formatDistance(distance) {
  if (typeof distance !== "number") return "--";
  return `${distance.toFixed(1)} km`;
}

function formatDuration(durationSeconds) {
  if (typeof durationSeconds !== "number") return "--";
  const hours = Math.floor(durationSeconds / 3600);
  const minutes = Math.floor((durationSeconds % 3600) / 60);
  const seconds = durationSeconds % 60;
  if (hours > 0) return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function formatPace(activity) {
  if (!activity || typeof activity.distance !== "number" || typeof activity.duration !== "number") {
    return "--";
  }
  if (activity.distance <= 0 || activity.duration <= 0) return "--";

  if (activity.activity_type === "swim") {
    const secondsPer100m = activity.duration / (activity.distance * 10);
    const minutes = Math.floor(secondsPer100m / 60);
    const seconds = Math.round(secondsPer100m % 60);
    return `${minutes}:${String(seconds).padStart(2, "0")} / 100m`;
  }

  const secondsPerKm = activity.duration / activity.distance;
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.round(secondsPerKm % 60);
  return `${minutes}:${String(seconds).padStart(2, "0")} / km`;
}

function formatShortDate(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "Unknown";

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diffDays = Math.round((today - target) / 86400000);

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatTiming(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "Morning";
  const hour = date.getHours();
  if (hour >= 5 && hour < 12) return "Morning";
  if (hour >= 12 && hour < 14) return "Lunch";
  if (hour >= 14 && hour < 18) return "Afternoon";
  return "Evening";
}

function formatTimeAgo(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "recently";

  const diffMinutes = Math.round((Date.now() - date.getTime()) / 60000);
  if (diffMinutes < 60) return `${Math.max(diffMinutes, 1)}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

function buildActivityMeta(activity) {
  const user = state.usersById[activity.user_id];
  const actor = user ? user.name : "Athlete";
  return `${actor} - ${formatTimeAgo(activity.timestamp)}`;
}

function computeTopActivityLabel(activities) {
  const counts = {};
  for (const activity of activities) {
    counts[activity.activity_type] = (counts[activity.activity_type] || 0) + 1;
  }
  const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
  return top ? formatActivityType(top[0]) : "--";
}

function isFollowingUser(userId) {
  return Boolean(state.followingMap[userId]);
}

function getClubMembership(clubId) {
  return state.clubMemberships.find(
    (membership) => membership.club_id === clubId && membership.user_id === state.userId
  );
}

function isClubAdmin(clubId) {
  const membership = getClubMembership(clubId);
  return membership?.status === "approved" && membership?.role === "club_admin";
}

function normalizeCoachMessages(messages) {
  return messages.map((message) => ({
    sender: message.sender,
    content: message.content,
    created_at: message.created_at,
  }));
}


function decodePolyline(encoded) {
  const coords = [];
  let index = 0, lat = 0, lng = 0;
  while (index < encoded.length) {
    let shift = 0, val = 0, byte;
    do { byte = encoded.charCodeAt(index++) - 63; val |= (byte & 0x1f) << shift; shift += 5; } while (byte >= 0x20);
    lat += val & 1 ? ~(val >> 1) : val >> 1;
    shift = 0; val = 0;
    do { byte = encoded.charCodeAt(index++) - 63; val |= (byte & 0x1f) << shift; shift += 5; } while (byte >= 0x20);
    lng += val & 1 ? ~(val >> 1) : val >> 1;
    coords.push([lat / 1e5, lng / 1e5]);
  }
  return coords;
}

function computePersonalRecords() {
  const mine = state.activities.filter((a) => a.user_id === state.userId);
  const records = {};
  const add = (id, label) => {
    if (!id) return;
    const key = String(id);
    records[key] = records[key] ? [...records[key], label] : [label];
  };

  for (const type of ["run", "bike", "swim", "walk", "hike"]) {
    const typed = mine.filter((a) => a.activity_type === type && a.distance > 0);
    if (typed.length) {
      const best = typed.reduce((a, b) => (a.distance > b.distance ? a : b));
      add(best.activity_id, `Longest ${formatActivityType(type)}`);
    }
  }

  const runs = mine.filter((a) => a.activity_type === "run" && a.distance >= 2 && a.duration > 0);
  if (runs.length) {
    const fastest = runs.reduce((a, b) => a.duration / a.distance < b.duration / b.distance ? a : b);
    add(fastest.activity_id, "Best Pace");
  }

  state.personalRecords = records;
}

function getPersonalRecordsSummary() {
  const mine = state.activities.filter((a) => a.user_id === state.userId);
  const summary = [];

  for (const type of ["run", "bike", "swim", "walk", "hike"]) {
    const typed = mine.filter((a) => a.activity_type === type && a.distance > 0);
    if (!typed.length) continue;
    const best = typed.reduce((a, b) => (a.distance > b.distance ? a : b));
    summary.push({
      label: `Longest ${formatActivityType(type)}`,
      value: `${best.distance.toFixed(1)} km`,
      date: best.timestamp,
    });
  }

  const runs = mine.filter((a) => a.activity_type === "run" && a.distance >= 2 && a.duration > 0);
  if (runs.length) {
    const fastest = runs.reduce((a, b) => a.duration / a.distance < b.duration / b.distance ? a : b);
    const secPerKm = fastest.duration / fastest.distance;
    const pMin = Math.floor(secPerKm / 60);
    const pSec = String(Math.round(secPerKm % 60)).padStart(2, "0");
    summary.push({ label: "Best Run Pace", value: `${pMin}:${pSec} /km`, date: fastest.timestamp });
  }

  return summary;
}