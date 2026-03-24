const app = document.getElementById('app');

const routes = {
  '': renderLogin,
  '#/login': renderLogin,
  '#/signup': renderSignup,
  '#/dashboard': renderDashboard,
  '#/activities': renderActivities,
  '#/training-plan': renderTrainingPlan,
  '#/coach': renderCoach,
  '#/profile': renderProfile,
  '#/admin': renderAdmin,
};

function renderLogo() {
  return `
    <div class="brand-row">
      <div class="logo-placeholder" aria-hidden="true">Logo</div>
      <div class="brand-mark">Stride</div>
    </div>
  `;
}

function renderLayout({ active, title, subtitle, content, actions = true }) {
  return `
    <div class="app-layout">
      <aside class="sidebar">
        ${renderLogo()}
        <nav class="nav-links">
          <a class="nav-link ${active === 'dashboard' ? 'active' : ''}" href="#/dashboard">Dashboard</a>
          <a class="nav-link ${active === 'activities' ? 'active' : ''}" href="#/activities">Activities</a>
          <a class="nav-link ${active === 'training-plan' ? 'active' : ''}" href="#/training-plan">Training Plan</a>
          <a class="nav-link ${active === 'coach' ? 'active' : ''}" href="#/coach">Coach</a>
          <a class="nav-link ${active === 'profile' ? 'active' : ''}" href="#/profile">Profile</a>
          <a class="nav-link ${active === 'admin' ? 'active' : ''}" href="#/admin">Admin</a>
        </nav>
      </aside>

      <div class="main-content">
        <header class="top-bar">
          <div>
            <h1 class="page-title">${title}</h1>
            <p class="text-muted">${subtitle}</p>
          </div>
          ${actions ? `
            <div class="quick-actions">
              <button class="btn btn-outline-secondary">Add Activity</button>
              <button class="btn btn-dark">Sync Strava</button>
            </div>
          ` : ''}
        </header>

        ${content}
      </div>
    </div>
  `;
}

function renderLogin() {
  app.innerHTML = `
    <main class="login-page">
      <section class="brand-panel">
        <div class="brand-content">
          ${renderLogo()}
          <p class="brand-tagline">Train smarter, reflect deeper, run stronger.</p>
          <ul class="brand-highlights">
            <li>AI training plans built for your goals</li>
            <li>Reflect after every run with your coach</li>
            <li>Follow friends and stay motivated</li>
          </ul>
        </div>
      </section>

      <section class="login-panel">
        <div class="login-card">
          <div class="card-header">
            ${renderLogo()}
            <h1>Welcome back</h1>
            <p class="text-muted">Sign in to continue your training.</p>
          </div>

          <div class="card-body">
            <label class="form-label">Email</label>
            <input type="email" class="form-control" placeholder="you@example.com" />

            <button class="btn btn-primary w-100 mt-3">Continue</button>

            <div class="divider"><span>or</span></div>

            <div class="oauth-buttons">
              <button class="btn btn-outline-secondary w-100">Continue with Google</button>
              <button class="btn btn-outline-dark w-100">Connect with Strava</button>
            </div>

            <div class="inline-error mt-3 d-none">Please enter a valid email.</div>
          </div>

          <div class="card-footer">
            <div class="dev-toggle">
              <input type="checkbox" id="devToggle" />
              <label for="devToggle">Use existing user</label>
            </div>

            <select class="form-select mt-2" disabled>
              <option>Select a user</option>
              <option>Test User 1</option>
              <option>Test User 2</option>
            </select>

            <p class="signup-link">Don&#39;t have an account? <a href="#/signup">Sign up</a></p>
          </div>
        </div>
      </section>
    </main>
  `;

  const devToggle = document.getElementById('devToggle');
  const select = app.querySelector('select');

  devToggle.addEventListener('change', () => {
    select.disabled = !devToggle.checked;
  });
}

function renderSignup() {
  app.innerHTML = `
    <main class="signup-page">
      <section class="signup-panel">
        <div class="signup-card">
          <div class="card-header">
            ${renderLogo()}
            <h1>Create your account</h1>
            <p class="text-muted">Start building your training plan today.</p>
          </div>

          <div class="card-body">
            <label class="form-label">Name</label>
            <input type="text" class="form-control" placeholder="Your name" />

            <label class="form-label mt-3">Email</label>
            <input type="email" class="form-control" placeholder="you@example.com" />

            <label class="form-label mt-3">Password</label>
            <input type="password" class="form-control" placeholder="Create a password" />

            <button class="btn btn-primary w-100 mt-4">Create account</button>

            <div class="inline-success mt-3 d-none">Account created. Redirecting...</div>
            <div class="inline-error mt-2 d-none">Please fill in all fields.</div>
          </div>

          <div class="card-footer">
            <p class="signup-link">Already have an account? <a href="#/login">Sign in</a></p>
          </div>
        </div>
      </section>
    </main>
  `;
}

function renderDashboard() {
  const content = `
    <section class="kpi-grid">
      <div class="kpi-card">
        <p class="kpi-label">Weekly distance</p>
        <h2>42.3 km</h2>
        <span class="kpi-meta">+6% vs last week</span>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Sessions</p>
        <h2>4 / 5</h2>
        <span class="kpi-meta">1 remaining</span>
      </div>
      <div class="kpi-card">
        <p class="kpi-label">Plan status</p>
        <h2>On track</h2>
        <span class="kpi-meta">Next run: Tempo</span>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <h3>Recent activity</h3>
        <a href="#/activities">View all</a>
      </div>

      <div class="activity-feed">
        ${renderActivityCard('Morning Run', 'Today · Easy run', 'run', ['Easy Run', 'Road'], true, [
          { label: 'Distance', value: '8.2 km' },
          { label: 'Time', value: '48:12' },
          { label: 'Pace', value: '5:52 / km' },
          { label: 'Effort', value: 'Moderate' },
        ])}
        ${renderActivityCard('Intervals', 'Yesterday · Track', 'run', ['Intervals', 'Track'], true, [
          { label: 'Distance', value: '6.5 km' },
          { label: 'Time', value: '42:05' },
          { label: 'Pace', value: '6:28 / km' },
          { label: 'Effort', value: 'Hard' },
        ])}
        ${renderActivityCard('Long Run', 'Sun · Endurance', 'run', ['Long Run', 'Road'], true, [
          { label: 'Distance', value: '18.1 km' },
          { label: 'Time', value: '1:46:20' },
          { label: 'Pace', value: '5:52 / km' },
          { label: 'Effort', value: 'Moderate' },
        ])}
      </div>
    </section>
  `;

  app.innerHTML = renderLayout({
    active: 'dashboard',
    title: 'Dashboard',
    subtitle: 'Your training snapshot for the week.',
    content,
  });

  attachActivityCardHandlers();
}

function renderActivities() {
  const content = `
    <section class="section-block">
      <div class="activities-layout">
        <div class="activity-column">
          <div class="filters-bar">
            <div class="filters-group">
              <select class="form-select" id="activityTypeFilter">
                <option>All types</option>
                <option>Run</option>
                <option>Ride</option>
                <option>Swim</option>
                <option>Walk</option>
                <option>Weights</option>
                <option>Other</option>
              </select>
              <select class="form-select">
                <option>Last 7 days</option>
                <option>Last 30 days</option>
                <option>This year</option>
              </select>
            </div>
          </div>

          <div class="activity-feed">
            ${renderActivityCard('Evening Run', 'Amina · 2h ago', 'run', ['Outdoor', 'Road'], true, [
              { label: 'Distance', value: '10.4 km' },
              { label: 'Time', value: '58:42' },
              { label: 'Pace', value: '5:38 / km' },
              { label: 'Effort', value: 'Moderate' },
            ])}
            ${renderActivityCard('Trail Session', 'Marwan · Yesterday', 'run', ['Outdoor', 'Trail'], true, [
              { label: 'Distance', value: '12.2 km' },
              { label: 'Time', value: '1:09:03' },
              { label: 'Pace', value: '5:39 / km' },
              { label: 'Effort', value: 'Hard' },
            ])}
            ${renderActivityCard('Tempo Run', 'Sarah · Tue', 'run', ['Track'], true, [
              { label: 'Distance', value: '7.8 km' },
              { label: 'Time', value: '41:10' },
              { label: 'Pace', value: '5:17 / km' },
              { label: 'Effort', value: 'Hard' },
            ])}
            ${renderActivityCard('Swim Session', 'Hala · Mon', 'swim', ['Pool'], false, [
              { label: 'Distance', value: '1.4 km' },
              { label: 'Time', value: '32:20' },
              { label: 'Effort', value: 'Moderate' },
            ])}
            ${renderActivityCard('Strength Training', 'Nour · Sun', 'weights', ['Gym'], false, [
              { label: 'Duration', value: '45:00' },
              { label: 'Effort', value: 'Hard' },
            ])}
          </div>
        </div>

        <aside class="sidebar-column">
          <div class="sidebar-search">
            <label class="form-label">Search users</label>
            <div class="search-group">
              <input type="text" class="form-control" id="userSearchInput" placeholder="Search username" />
              <div class="search-dropdown" id="userSearchDropdown">
                <button class="search-item">@amina.runner</button>
                <button class="search-item">@stride.captain</button>
                <button class="search-item">@liftandrun</button>
              </div>
            </div>
          </div>
          <div class="suggestions-card">
            <h4>Who to follow</h4>
            <div class="suggestion-item">
              <div class="avatar"></div>
              <div>
                <p class="name">Tarek Saab</p>
                <span>@tarek.run</span>
              </div>
              <button class="btn btn-sm btn-outline-secondary">Follow</button>
            </div>
            <div class="suggestion-item">
              <div class="avatar"></div>
              <div>
                <p class="name">Maya Al</p>
                <span>@maya.moves</span>
              </div>
              <button class="btn btn-sm btn-outline-secondary">Follow</button>
            </div>
            <div class="suggestion-item">
              <div class="avatar"></div>
              <div>
                <p class="name">Rami Khoury</p>
                <span>@rami.run</span>
              </div>
              <button class="btn btn-sm btn-outline-secondary">Follow</button>
            </div>
          </div>
        </aside>
      </div>
    </section>

    ${renderActivityModal()}
  `;

  app.innerHTML = renderLayout({
    active: 'activities',
    title: 'Activities',
    subtitle: 'Recent activities from athletes you follow.',
    content,
  });

  const typeFilter = document.getElementById('activityTypeFilter');
  const cards = Array.from(app.querySelectorAll('.activity-card'));

  typeFilter.addEventListener('change', () => {
    const selected = typeFilter.value.toLowerCase();
    cards.forEach((card) => {
      const type = card.dataset.type || 'other';
      if (selected === 'all types') {
        card.classList.remove('d-none');
      } else if (type === selected) {
        card.classList.remove('d-none');
      } else {
        card.classList.add('d-none');
      }
    });
  });

  const searchInput = document.getElementById('userSearchInput');
  const searchDropdown = document.getElementById('userSearchDropdown');

  const updateSearchDropdown = () => {
    const value = searchInput.value.trim();
    if (value.length > 0) {
      searchDropdown.classList.add('open');
    } else {
      searchDropdown.classList.remove('open');
    }
  };

  searchInput.addEventListener('input', updateSearchDropdown);
  searchInput.addEventListener('focus', updateSearchDropdown);
  searchInput.addEventListener('blur', () => {
    setTimeout(() => searchDropdown.classList.remove('open'), 150);
  });

  attachActivityCardHandlers();
}

function renderTrainingPlan() {
  const content = `
    <section class="section-block">
      <div class="page-grid">
        <div class="panel-card">
          <div class="section-header">
            <h3>Weekly plan</h3>
            <span class="tag">Goal: 10K • 6 weeks</span>
          </div>
          <div class="plan-list">
            ${renderPlanItem('Mon', 'Recovery Run', '6 km • Easy pace', 'Completed')}
            ${renderPlanItem('Tue', 'Intervals', '5 × 800m • Track', 'Completed')}
            ${renderPlanItem('Wed', 'Strength', '30 min • Mobility + Core', 'Today')}
            ${renderPlanItem('Thu', 'Tempo Run', '7 km • Goal pace', 'Upcoming')}
            ${renderPlanItem('Sat', 'Long Run', '16 km • Endurance', 'Upcoming')}
          </div>
        </div>

        <aside class="panel-card">
          <h3>Plan progress</h3>
          <div class="stat-list">
            <div class="stat-row">
              <span>Weeks completed</span>
              <strong>4 / 6</strong>
            </div>
            <div class="stat-row">
              <span>Completion rate</span>
              <strong>78%</strong>
            </div>
            <div class="stat-row">
              <span>Next race</span>
              <strong>Beirut 10K</strong>
            </div>
          </div>
          <div class="progress-track">
            <div class="progress-bar" style="width: 68%"></div>
          </div>
          <div class="mini-card">
            <p class="mini-title">Coach focus</p>
            <p class="mini-body">Prioritize recovery this week. Two easy days before tempo.</p>
          </div>
        </aside>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <h3>Phase overview</h3>
        <span class="tag">Build block</span>
      </div>
      <div class="phase-grid">
        <div class="phase-card">
          <h4>Week 4</h4>
          <p class="text-muted">Speed endurance + long run</p>
          <ul class="phase-list">
            <li>Intervals (5 × 800m)</li>
            <li>Tempo (7 km)</li>
            <li>Long run (16 km)</li>
          </ul>
        </div>
        <div class="phase-card">
          <h4>Week 5</h4>
          <p class="text-muted">Peak volume</p>
          <ul class="phase-list">
            <li>Hills + strides</li>
            <li>Tempo (8 km)</li>
            <li>Long run (18 km)</li>
          </ul>
        </div>
        <div class="phase-card">
          <h4>Week 6</h4>
          <p class="text-muted">Taper</p>
          <ul class="phase-list">
            <li>Short intervals</li>
            <li>Easy runs only</li>
            <li>Race week</li>
          </ul>
        </div>
      </div>
    </section>
  `;

  app.innerHTML = renderLayout({
    active: 'training-plan',
    title: 'Training Plan',
    subtitle: 'Your personalized 10K build.',
    content,
  });
}

function renderCoach() {
  const content = `
    <section class="section-block">
      <div class="coach-center">
        <div class="panel-card coach-thread">
          <div class="message coach">
            <p class="message-meta">Coach • 2h ago</p>
            <p>How did yesterday’s intervals feel? Any tightness or soreness?</p>
          </div>
          <div class="message user">
            <p class="message-meta">You • 1h ago</p>
            <p>Legs felt heavy in the last two reps. HR was high.</p>
          </div>
          <div class="message coach">
            <p class="message-meta">Coach • 45m ago</p>
            <p>Let’s keep today light. Do 30 min easy + mobility.</p>
          </div>
          <div class="message-input">
            <input type="text" class="form-control" placeholder="Share how you feel..." />
            <button class="btn btn-dark">Send</button>
          </div>
        </div>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <h3>Check-in prompts</h3>
        <a href="#/training-plan">View plan</a>
      </div>
      <div class="prompt-grid">
        <div class="prompt-card">
          <h4>Post-run reflection</h4>
          <p class="text-muted">What felt strong today? What would you change?</p>
          <button class="btn btn-outline-secondary">Start reflection</button>
        </div>
        <div class="prompt-card">
          <h4>Fueling check</h4>
          <p class="text-muted">Did you hydrate and eat within 60 minutes?</p>
          <button class="btn btn-outline-secondary">Log intake</button>
        </div>
        <div class="prompt-card">
          <h4>Sleep tracker</h4>
          <p class="text-muted">How many hours did you sleep last night?</p>
          <button class="btn btn-outline-secondary">Log sleep</button>
        </div>
      </div>
    </section>
  `;

  app.innerHTML = renderLayout({
    active: 'coach',
    title: 'Coach',
    subtitle: 'Insights and feedback tailored to your training.',
    content,
    actions: false,
  });
}

function renderProfile() {
  const content = `
    <section class="section-block">
      <div class="profile-hero">
        <div class="profile-avatar profile-avatar-lg"></div>
        <div class="profile-identity">
          <h2>Jason Hkayem</h2>
          <p class="text-muted">@jason.hkayem • Beirut</p>
          <div class="profile-stats">
            <div class="profile-stat">
              <span class="stat-value">2.4K</span>
              <span class="stat-label">Followers</span>
            </div>
            <div class="profile-stat">
              <span class="stat-value">418</span>
              <span class="stat-label">Following</span>
            </div>
            <div class="profile-stat">
              <span class="stat-value">Runs</span>
              <span class="stat-label">Top activity</span>
            </div>
          </div>
        </div>
        <div class="profile-actions">
          <button class="btn btn-dark">Edit profile</button>
          <button class="btn btn-outline-secondary">Share</button>
        </div>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <h3>Recent activities</h3>
        <span class="tag">Last 6</span>
      </div>
      <div class="activity-grid">
        ${renderProfileActivity('Morning Run', 'Run', '8.1 km • 5:32 / km', true)}
        ${renderProfileActivity('Lunch Strength', 'Strength', '45 min • Upper body', false, [
          { label: 'Duration', value: '45 min' },
          { label: 'Avg HR', value: '132 bpm' },
          { label: 'Sets', value: '18' },
        ])}
        ${renderProfileActivity('Afternoon Swim', 'Swim', '1.6 km • 36:10', false, [
          { label: 'Avg HR', value: '128 bpm' },
          { label: 'Pace /100m', value: '2:15' },
          { label: 'Strokes', value: '1,540' },
        ])}
        ${renderProfileActivity('Evening Ride', 'Ride', '22.4 km • 48:22', true)}
        ${renderProfileActivity('Morning Walk', 'Walk', '3.4 km • 34:08', true)}
        ${renderProfileActivity('Evening Mobility', 'Mobility', '25 min • Full body', false, [
          { label: 'Duration', value: '25 min' },
          { label: 'Focus', value: 'Hips' },
          { label: 'Intensity', value: 'Easy' },
        ])}
      </div>
    </section>

    ${renderActivityModal()}
  `;

  app.innerHTML = renderLayout({
    active: 'profile',
    title: 'Profile',
    subtitle: 'Your public training snapshot.',
    content,
    actions: false,
  });

  attachProfileActivityHandlers();
}

function renderProfileActivity(title, type, meta, hasMap, kpis = []) {
  const mapPreview = hasMap
    ? `<span class="map-placeholder">Map preview</span>`
    : renderActivityKpis(kpis);
  return `
    <article class="activity-tile" data-title="${title}" data-type="${type}" data-meta="${meta}" data-has-map="${hasMap}">
      <div class="activity-tile-media">
        ${mapPreview}
        <span class="activity-type-badge">${type}</span>
      </div>
      <div class="activity-tile-body">
        <h4>${title}</h4>
        <p class="text-muted">${meta}</p>
      </div>
    </article>
  `;
}

function renderActivityKpis(kpis) {
  if (!kpis.length) {
    return `<span class="map-placeholder map-placeholder-muted">Indoor activity</span>`;
  }
  return `
    <div class="activity-kpi-grid">
      ${kpis
        .map(
          (kpi) => `
        <div class="activity-kpi-card">
          <span class="kpi-label">${kpi.label}</span>
          <span class="kpi-value">${kpi.value}</span>
        </div>`
        )
        .join('')}
    </div>
  `;
}

function attachProfileActivityHandlers() {
  const modal = document.getElementById('activityModal');
  const modalClose = document.getElementById('modalClose');
  if (!modal) return;

  const tiles = Array.from(app.querySelectorAll('.activity-tile'));
  const modalTitle = modal.querySelector('.modal-title');
  const modalMeta = modal.querySelector('.modal-meta');
  const modalStats = modal.querySelector('#modalStats');
  const modalChips = modal.querySelector('#modalChips');
  const modalMap = modal.querySelector('#modalMap');
  const modalCharts = modal.querySelector('#modalCharts');

  tiles.forEach((tile) => {
    tile.addEventListener('click', () => {
      const title = tile.dataset.title || 'Activity';
      const type = tile.dataset.type || 'Activity';
      const meta = tile.dataset.meta || '';
      const hasMap = tile.dataset.hasMap === 'true';

      modalTitle.textContent = title;
      modalMeta.textContent = meta;
      modalStats.innerHTML = `
        <div class="modal-stat">
          <span class="label">Type</span>
          <span class="value">${type}</span>
        </div>
        <div class="modal-stat">
          <span class="label">Summary</span>
          <span class="value">${meta}</span>
        </div>
      `;
      modalChips.innerHTML = `<span class="chip">${type}</span><span class="chip">Recent</span>`;

      modalMap.style.display = hasMap ? 'flex' : 'none';
      modalCharts.style.display = hasMap ? 'block' : 'none';
      modal.classList.add('open');
    });
  });

  modalClose?.addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      modal.classList.remove('open');
    }
  });
}

function renderAdmin() {
  const content = `
    <section class="section-block">
      <div class="kpi-grid">
        <div class="kpi-card">
          <p class="kpi-label">Active users</p>
          <h2>1,284</h2>
          <span class="kpi-meta">+4% this week</span>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">New signups</p>
          <h2>96</h2>
          <span class="kpi-meta">+12% vs last week</span>
        </div>
        <div class="kpi-card">
          <p class="kpi-label">Plan adjustments</p>
          <h2>211</h2>
          <span class="kpi-meta">Avg response 3h</span>
        </div>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <h3>User oversight</h3>
        <span class="tag">Needs review: 6</span>
      </div>
      <div class="panel-card">
        <table class="admin-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Status</th>
              <th>Plan</th>
              <th>Last activity</th>
              <th>Flags</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Rami Khoury</td>
              <td><span class="badge success">Active</span></td>
              <td>Half Marathon</td>
              <td>2h ago</td>
              <td><span class="badge warning">Low compliance</span></td>
            </tr>
            <tr>
              <td>Lea Haddad</td>
              <td><span class="badge success">Active</span></td>
              <td>10K</td>
              <td>Yesterday</td>
              <td><span class="badge neutral">No flags</span></td>
            </tr>
            <tr>
              <td>Mina Saab</td>
              <td><span class="badge muted">Paused</span></td>
              <td>5K</td>
              <td>5 days ago</td>
              <td><span class="badge warning">Injury</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  `;

  app.innerHTML = renderLayout({
    active: 'admin',
    title: 'Admin',
    subtitle: 'Monitor platform health and users.',
    content,
    actions: false,
  });
}

function renderPlanItem(day, title, detail, status) {
  return `
    <div class="plan-item">
      <div class="plan-day">${day}</div>
      <div class="plan-details">
        <p class="plan-title">${title}</p>
        <span class="text-muted">${detail}</span>
      </div>
      <span class="plan-status ${status.toLowerCase()}">${status}</span>
    </div>
  `;
}

function renderActivityCard(title, meta, type = 'run', chips = [], hasMap = false, stats = []) {
  const chipHtml = chips.length
    ? chips.map((chip) => `<span class="chip">${chip}</span>`).join('')
    : `<span class="chip">Activity</span>`;
  const mapHtml = hasMap
    ? `
      <div class="activity-map" aria-hidden="true">
        <div class="map-placeholder">Map preview</div>
      </div>
`
    : '';
  const statsHtml = stats.length
    ? stats
        .map(
          (stat) => `
        <div class="activity-stat">
          <span class="label">${stat.label}</span>
          <span class="value">${stat.value}</span>
        </div>`
        )
        .join('')
    : '';

  return `
    <article class="activity-card" data-type="${type}" data-has-map="${hasMap}">
      <div class="activity-header">
        <div class="activity-avatar" aria-hidden="true"></div>
        <div class="activity-title">
          <div class="activity-meta">${meta}</div>
          <h4>${title}</h4>
        </div>
      </div>
      <div class="activity-body">${statsHtml}
      </div>
      ${mapHtml}
      <div class="activity-footer">
        ${chipHtml}
      </div>
    </article>
  `;
}

function renderActivityModal() {
  return `
    <div class="modal-overlay" id="activityModal">
      <div class="modal-card">
        <div class="modal-header">
          <div>
            <p class="modal-meta" id="modalMeta"></p>
            <h2 class="modal-title" id="modalTitle"></h2>
          </div>
          <button class="modal-close" id="modalClose">×</button>
        </div>
        <div class="modal-body">
          <div class="modal-stats" id="modalStats"></div>
          <div class="modal-map" id="modalMap">
            <div class="map-placeholder">Map preview</div>
          </div>
          <div class="modal-charts" id="modalCharts">
            <p>Charts (Strava)</p>
            <div class="chart-placeholder">Pace · HR · Elevation</div>
          </div>
        </div>
        <div class="modal-footer" id="modalChips"></div>
      </div>
    </div>
  `;
}

function attachActivityCardHandlers() {
  const modal = document.getElementById('activityModal');
  const modalClose = document.getElementById('modalClose');
  if (!modal) return;

  const cards = Array.from(app.querySelectorAll('.activity-card'));
  const modalTitle = modal.querySelector('.modal-title');
  const modalMeta = modal.querySelector('.modal-meta');
  const modalStats = modal.querySelector('#modalStats');
  const modalChips = modal.querySelector('#modalChips');
  const modalMap = modal.querySelector('#modalMap');
  const modalCharts = modal.querySelector('#modalCharts');

  const buildStats = (card) =>
    Array.from(card.querySelectorAll('.activity-stat')).map((stat) => {
      const label = stat.querySelector('.label')?.textContent || '';
      const value = stat.querySelector('.value')?.textContent || '';
      return `
        <div class="modal-stat">
          <span class="label">${label}</span>
          <span class="value">${value}</span>
        </div>`;
    });

  const buildChips = (card) =>
    Array.from(card.querySelectorAll('.chip')).map((chip) => `<span class="chip">${chip.textContent}</span>`);

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      modalTitle.textContent = card.querySelector('h4')?.textContent || 'Activity';
      modalMeta.textContent = card.querySelector('.activity-meta')?.textContent || '';
      modalStats.innerHTML = buildStats(card).join('');
      modalChips.innerHTML = buildChips(card).join('');

      const hasMap = card.dataset.hasMap === 'true';
      modalMap.style.display = hasMap ? 'flex' : 'none';
      modalCharts.style.display = hasMap ? 'block' : 'none';

      modal.classList.add('open');
    });
  });

  modalClose?.addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      modal.classList.remove('open');
    }
  });
}

function handleRoute() {
  const hash = window.location.hash || '';
  const route = routes[hash] || routes[''];
  route();
}

window.addEventListener('hashchange', handleRoute);
window.addEventListener('load', handleRoute);
