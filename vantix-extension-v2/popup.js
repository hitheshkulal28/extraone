// ─────────────────────────────────────────────────────────────
// Vantix Extension — Final popup.js
// Login + Google + GitHub + Settings + Logout
// ─────────────────────────────────────────────────────────────

console.log("[Vantix] popup.js module loaded");

const VANTIX_API_BASE = "http://localhost:5000/api";
// The dashboard URL where our robust ext-auth.html helper is hosted
const AUTH_HELPER_URL = "http://localhost:5173/ext-auth.html";


// ─────────────────────────────────────────────────────────────
// NAVIGATION & UI HELPERS
// ─────────────────────────────────────────────────────────────

function setupNavigation() {
  // Back buttons
  document.querySelectorAll(".back-btn").forEach(btn => {
    btn.onclick = () => {
      // If we are in login/register, go back to entry
      showView("entry-view");
    };
  });

  // Entry buttons
  const btnSingle = document.getElementById("btn-entry-single");
  if (btnSingle) {
    btnSingle.onclick = () => {
      chrome.storage.local.set({ vantixPendingUserType: "individual" }, () => {
        const title = document.getElementById("login-title");
        if (title) title.textContent = "Individual Login";
        const emailInput = document.getElementById("login-email");
        if (emailInput) emailInput.placeholder = "you@gmail.com";
        showView("login-view");
      });
    };
  }

  const btnOrg = document.getElementById("btn-entry-org");
  if (btnOrg) {
    btnOrg.onclick = () => {
      chrome.storage.local.set({ vantixPendingUserType: "company" }, () => {
        const title = document.getElementById("login-title");
        if (title) title.textContent = "Employee Login";
        const emailInput = document.getElementById("login-email");
        if (emailInput) emailInput.placeholder = "you@company.com";
        showView("org-role-view");
      });
    };
  }

  const btnOrgEmp = document.getElementById("btn-org-employee");
  if (btnOrgEmp) btnOrgEmp.onclick = () => showView("login-view");
}

function setupGlobalToggle() {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  const thumb = toggle.querySelector(".toggle-thumb");

  // Load initial state
  chrome.storage.local.get(["isProtectionEnabled"], (res) => {
    const enabled = res.isProtectionEnabled !== false;
    updateToggleUI(enabled);
  });

  toggle.onclick = () => {
    chrome.storage.local.get(["isProtectionEnabled"], (res) => {
      const newState = !(res.isProtectionEnabled !== false);
      chrome.storage.local.set({ isProtectionEnabled: newState }, () => {
        updateToggleUI(newState);
      });
    });
  };

  function updateToggleUI(enabled) {
    const root = document.documentElement;
    if (enabled) {
      // Protection ON -> Dark Mode
      root.classList.add("theme-dark");
      root.classList.remove("theme-light");
      if (thumb) thumb.style.transform = "translateX(22px)";
      toggle.style.opacity = "1";
    } else {
      // Protection OFF -> Light Mode
      root.classList.add("theme-light");
      root.classList.remove("theme-dark");
      if (thumb) thumb.style.transform = "translateX(0px)";
      toggle.style.opacity = "0.7";
    }
  }
}


// ─────────────────────────────────────────────────────────────
// VIEW SWITCHING
// ─────────────────────────────────────────────────────────────

function showView(viewId) {
  console.log(`[Vantix] Switching to view: ${viewId}`);
  const views = [
    "entry-view",
    "org-role-view",
    "login-view",
    "register-view",
    "main-view",
    "paywall-view"
  ];

  views.forEach(v => {
    const el = document.getElementById(v);
    if (el) el.classList.add("hidden");
  });

  const target = document.getElementById(viewId);
  if (target) target.classList.remove("hidden");
}


// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

function init() {
  console.log("[Vantix] Initializing popup UI...");

  setupEmailLogin();
  setupGoogleLogin();
  setupGithubLogin();
  setupLogout();
  setupNavigation();
  setupGlobalToggle();
  checkLoginState();
  
  // Listen for storage changes (to detect when the auth window finishes)
  chrome.storage.onChanged.addListener((changes) => {
    if (changes.vantixToken) {
      console.log("[Vantix] Auth change detected in storage, reloading...");
      window.location.reload();
    }
  });
}


// ─────────────────────────────────────────────────────────────
// EMAIL LOGIN
// ─────────────────────────────────────────────────────────────

function setupEmailLogin() {
  const btnNext = document.getElementById("btn-login-next");

  if (btnNext) {
    btnNext.onclick = () => {
      const emailInput = document.getElementById("login-email");
      const email = emailInput ? emailInput.value.trim() : "";

      if (!email) {
        alert("Enter email");
        return;
      }

      document.getElementById("grp-password").classList.remove("hidden");
      btnNext.classList.add("hidden");
      document.getElementById("btn-login-submit").classList.remove("hidden");
    };
  }

  const btnSubmit = document.getElementById("btn-login-submit");

  if (btnSubmit) {
    btnSubmit.onclick = async () => {
      const email = document.getElementById("login-email").value.trim();
      const password = document.getElementById("login-password").value;

      if (!password) {
        alert("Enter password");
        return;
      }

      btnSubmit.textContent = "Logging in...";

      try {
        const res = await fetch(`${VANTIX_API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (data.success) {
          chrome.storage.local.set(
            { vantixToken: data.token, vantixEmail: email },
            () => { window.location.reload(); }
          );
        } else {
          alert(data.error || "Login failed");
        }
      } catch (err) {
        console.error("[Vantix] Login error:", err);
        alert("Backend not reachable at localhost:5000");
      } finally {
        btnSubmit.textContent = "Login";
      }
    };
  }
}


// ─────────────────────────────────────────────────────────────
// GOOGLE LOGIN (Robust Web-Based Flow)
// ─────────────────────────────────────────────────────────────

function setupGoogleLogin() {
  const btn = document.getElementById("btn-google-login");
  if (!btn) return;

  btn.onclick = () => {
    chrome.storage.local.get(["vantixPendingUserType"], (res) => {
      const type = res.vantixPendingUserType || "company";
      console.log(`[Vantix] Google login (${type}) via web helper`);
      window.open(`${AUTH_HELPER_URL}?provider=google&userType=${type}`, "Vantix Login", "width=500,height=600");
    });
  };
}


// ─────────────────────────────────────────────────────────────
// GITHUB LOGIN (Robust Web-Based Flow)
// ─────────────────────────────────────────────────────────────

function setupGithubLogin() {
  const btn = document.getElementById("btn-github-login");
  if (!btn) return;

  btn.onclick = () => {
    chrome.storage.local.get(["vantixPendingUserType"], (res) => {
      const type = res.vantixPendingUserType || "company";
      console.log(`[Vantix] GitHub login (${type}) via web helper`);
      window.open(`${AUTH_HELPER_URL}?provider=github&userType=${type}`, "Vantix Login", "width=500,height=600");
    });
  };
}


// ─────────────────────────────────────────────────────────────
// LOGOUT
// ─────────────────────────────────────────────────────────────

function setupLogout() {
  const btn = document.getElementById("btn-logout");
  if (!btn) return;

  btn.onclick = () => {
    chrome.storage.local.clear(() => {
      console.log("[Vantix] Logged out");
      window.location.reload();
    });
  };
}


// ─────────────────────────────────────────────────────────────
// CHECK LOGIN STATE
// ─────────────────────────────────────────────────────────────

function checkLoginState() {
  chrome.storage.local.get(["vantixToken"], (res) => {
    if (res.vantixToken) {
      console.log("[Vantix] User is logged in");
      showView("main-view");
      loadSettings();
    } else {
      console.log("[Vantix] User is not logged in");
      showView("entry-view");
    }
  });
}


// ─────────────────────────────────────────────────────────────
// SETTINGS
// ─────────────────────────────────────────────────────────────

function loadSettings() {
  const toggles = ["email", "apikey", "cc", "phone", "aadhaar", "pan"];
  const keys = toggles.map(t => `enable${t.charAt(0).toUpperCase() + t.slice(1)}Detection`);

  chrome.storage.local.get(keys, (res) => {
    toggles.forEach(t => {
      const key = `enable${t.charAt(0).toUpperCase() + t.slice(1)}Detection`;
      const el = document.getElementById(`toggle-${t}`);
      if (!el) return;

      el.checked = res[key] !== false;
      el.onchange = e => chrome.storage.local.set({ [key]: e.target.checked });
    });
  });
}


// ─────────────────────────────────────────────────────────────
// START
// ─────────────────────────────────────────────────────────────

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}