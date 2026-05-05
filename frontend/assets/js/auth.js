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
            <h1 id="loginCardTitle">Welcome back</h1>
            <p class="text-muted" id="loginCardSubtitle">Sign in to continue your training.</p>
          </div>

          <div class="card-body">

            <!-- ── Normal login fields ── -->
            <div id="loginFields">
              <label class="form-label">Email</label>
              <input type="email" class="form-control" id="loginEmail" placeholder="Enter your email" />

              <label class="form-label mt-3">Password</label>
              <input type="password" class="form-control" id="loginPassword" placeholder="Enter your password" />

              <div class="d-flex justify-content-end mt-1">
                <button class="btn-link-muted" type="button" id="forgotPasswordLink">Forgot password?</button>
              </div>

              <button class="btn btn-primary w-100 mt-3" id="loginSubmit">Continue</button>

              <div class="divider"><span>or</span></div>

              <div class="oauth-buttons">
                <button class="btn btn-outline-secondary w-100" id="googleSignIn" style="display:inline-flex;align-items:center;justify-content:center;">${GOOGLE_SVG}Continue with Google</button>
                <button class="btn btn-outline-dark w-100" id="stravaConnect" style="display:inline-flex;align-items:center;justify-content:center;">${STRAVA_SVG}Connect with Strava</button>
              </div>

              <div class="inline-error mt-3 d-none" id="loginError"></div>
            </div>

            <!-- ── Forgot password panel ── -->
            <div id="forgotPanel" class="d-none">

              <!-- Step 1: email request -->
              <div id="forgotStep1">
                <p class="text-muted" style="font-size:14px;margin-bottom:16px;">Enter your account email and we'll generate a reset code.</p>
                <label class="form-label">Email</label>
                <input type="email" class="form-control" id="forgotEmail" placeholder="you@example.com" />
                <button class="btn btn-primary w-100 mt-3" id="forgotSendBtn">Send reset code</button>
                <div class="inline-error mt-2 d-none" id="forgotError"></div>
              </div>

              <!-- Step 2: token + new password -->
              <div id="forgotStep2" class="d-none">
                <div class="demo-notice">
                  <strong>Demo mode</strong> — in a production app this code would arrive by email. Your one-time reset code is:
                  <code id="demoTokenDisplay"></code>
                </div>
                <label class="form-label mt-3">Reset code</label>
                <input class="form-control" id="resetTokenInput" placeholder="Paste your reset code" />
                <label class="form-label mt-3">New password</label>
                <input type="password" class="form-control" id="resetNewPwd" placeholder="At least 8 characters" />
                <label class="form-label mt-3">Confirm password</label>
                <input type="password" class="form-control" id="resetConfirmPwd" placeholder="Re-enter new password" />
                <button class="btn btn-primary w-100 mt-3" id="resetSubmitBtn">Reset password</button>
                <div class="inline-error mt-2 d-none" id="resetError"></div>
                <div class="inline-success mt-2 d-none" id="resetSuccess">Password reset — redirecting to sign in…</div>
              </div>

              <div class="mt-3">
                <button class="btn-link-muted" type="button" id="backToLoginBtn">← Back to sign in</button>
              </div>
            </div>

          </div>

          <div class="card-footer">
            <p class="signup-link">Don't have an account? <a href="#/signup">Sign up</a></p>
          </div>
        </div>
      </section>
    </main>
  `;

  const loginError = document.getElementById("loginError");
  const emailInput = document.getElementById("loginEmail");
  const passwordInput = document.getElementById("loginPassword");
  const loginCardTitle = document.getElementById("loginCardTitle");
  const loginCardSubtitle = document.getElementById("loginCardSubtitle");
  const loginFields = document.getElementById("loginFields");
  const forgotPanel = document.getElementById("forgotPanel");

  const showForgotPanel = () => {
    loginFields.classList.add("d-none");
    forgotPanel.classList.remove("d-none");
    loginCardTitle.textContent = "Reset password";
    loginCardSubtitle.textContent = "We'll send you a one-time reset code.";
    document.getElementById("forgotEmail").focus();
  };

  const showLoginFields = () => {
    forgotPanel.classList.add("d-none");
    loginFields.classList.remove("d-none");
    loginCardTitle.textContent = "Welcome back";
    loginCardSubtitle.textContent = "Sign in to continue your training.";
    document.getElementById("forgotStep1").classList.remove("d-none");
    document.getElementById("forgotStep2").classList.add("d-none");
    document.getElementById("forgotError").classList.add("d-none");
  };

  // ── Login submit ──
  document.getElementById("loginSubmit").addEventListener("click", async () => {
    loginError.classList.add("d-none");
    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: emailInput.value.trim(),
          password: passwordInput.value,
        }),
      });
      setAuth(data.user, data.token);
      window.location.hash = "#/dashboard";
    } catch (error) {
      loginError.textContent = error.message;
      loginError.classList.remove("d-none");
    }
  });

  // ── Forgot password toggle ──
  document.getElementById("forgotPasswordLink").addEventListener("click", showForgotPanel);
  document.getElementById("backToLoginBtn").addEventListener("click", showLoginFields);

  // ── Step 1: request reset code ──
  document.getElementById("forgotSendBtn").addEventListener("click", async () => {
    const forgotError = document.getElementById("forgotError");
    forgotError.classList.add("d-none");
    const email = document.getElementById("forgotEmail").value.trim();
    if (!email) {
      forgotError.textContent = "Please enter your email address.";
      forgotError.classList.remove("d-none");
      return;
    }
    const btn = document.getElementById("forgotSendBtn");
    btn.disabled = true;
    btn.textContent = "Sending…";
    try {
      const result = await apiFetch("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      document.getElementById("forgotStep1").classList.add("d-none");
      document.getElementById("forgotStep2").classList.remove("d-none");
      const tokenDisplay = document.getElementById("demoTokenDisplay");
      const tokenInput = document.getElementById("resetTokenInput");
      if (result.reset_token) {
        tokenDisplay.textContent = result.reset_token;
        tokenInput.value = result.reset_token;
      }
      loginCardSubtitle.textContent = "Enter the reset code and choose a new password.";
    } catch (err) {
      forgotError.textContent = err.message;
      forgotError.classList.remove("d-none");
      btn.disabled = false;
      btn.textContent = "Send reset code";
    }
  });

  // ── Step 2: submit new password ──
  document.getElementById("resetSubmitBtn").addEventListener("click", async () => {
    const resetError = document.getElementById("resetError");
    const resetSuccess = document.getElementById("resetSuccess");
    resetError.classList.add("d-none");
    resetSuccess.classList.add("d-none");

    const token = document.getElementById("resetTokenInput").value.trim();
    const newPwd = document.getElementById("resetNewPwd").value;
    const confirmPwd = document.getElementById("resetConfirmPwd").value;

    if (!token) {
      resetError.textContent = "Please enter the reset code.";
      resetError.classList.remove("d-none");
      return;
    }
    if (!newPwd || newPwd.length < 8) {
      resetError.textContent = "Password must be at least 8 characters.";
      resetError.classList.remove("d-none");
      return;
    }
    if (newPwd !== confirmPwd) {
      resetError.textContent = "Passwords do not match.";
      resetError.classList.remove("d-none");
      return;
    }

    const btn = document.getElementById("resetSubmitBtn");
    btn.disabled = true;
    btn.textContent = "Resetting…";
    try {
      await apiFetch("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPwd }),
      });
      resetSuccess.classList.remove("d-none");
      const savedEmail = document.getElementById("forgotEmail")?.value || "";
      setTimeout(() => {
        showLoginFields();
        if (savedEmail) emailInput.value = savedEmail;
        emailInput.focus();
      }, 2000);
    } catch (err) {
      resetError.textContent = err.message;
      resetError.classList.remove("d-none");
      btn.disabled = false;
      btn.textContent = "Reset password";
    }
  });

  // ── OAuth buttons ──
  document.getElementById("stravaConnect").addEventListener("click", async () => {
    loginError.classList.add("d-none");
    const targetUserId = state.userId;
    if (!targetUserId) {
      loginError.textContent = "Pick a user first, then connect Strava.";
      loginError.classList.remove("d-none");
      return;
    }
    try {
      const result = await apiFetch(`/users/${targetUserId}/strava/oauth/start`);
      if (result.authorize_url) {
        window.open(result.authorize_url, "_blank", "noopener,noreferrer");
      }
    } catch (error) {
      loginError.textContent = error.message;
      loginError.classList.remove("d-none");
    }
  });

  document.getElementById("googleSignIn").addEventListener("click", () => {
    loginError.textContent = "Google sign-in is not wired yet.";
    loginError.classList.remove("d-none");
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
            <input type="text" class="form-control" id="signupName" placeholder="Your name" />

            <label class="form-label mt-3">Email</label>
            <input type="email" class="form-control" id="signupEmail" placeholder="you@example.com" />

            <label class="form-label mt-3">Password</label>
            <input type="password" class="form-control" id="signupPassword" placeholder="Create a password" />

            <button class="btn btn-primary w-100 mt-4" id="signupSubmit">Create account</button>

            <div class="inline-success mt-3 d-none" id="signupSuccess">Account created. Redirecting...</div>
            <div class="inline-error mt-2 d-none" id="signupError"></div>
          </div>

          <div class="card-footer">
            <p class="signup-link">Already have an account? <a href="#/login">Sign in</a></p>
          </div>
        </div>
      </section>
    </main>
  `;

  document.getElementById("signupSubmit").addEventListener("click", async () => {
    const errorEl = document.getElementById("signupError");
    const successEl = document.getElementById("signupSuccess");
    errorEl.classList.add("d-none");
    successEl.classList.add("d-none");

    try {
      const data = await apiFetch("/auth/signup", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("signupName").value.trim(),
          email: document.getElementById("signupEmail").value.trim(),
          password: document.getElementById("signupPassword").value,
          platform_role: "user",
        }),
      });
      setAuth(data.user, data.token);
      successEl.classList.remove("d-none");
      setTimeout(() => {
        window.location.hash = "#/dashboard";
      }, 500);
    } catch (error) {
      errorEl.textContent = error.message;
      errorEl.classList.remove("d-none");
    }
  });
}
