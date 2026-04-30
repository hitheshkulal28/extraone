"""
Vantix — Windows Clipboard Monitoring Agent
============================================
Monitors the system clipboard every second.

Detection tiers (merged into one unified popup):
  1. Company rules from DB  (employees/admins only)
  2. Critical patterns       (Aadhaar, PAN, API Keys, etc.)
  3. Moderate patterns       (Email, Phone)

ALL detections show a SINGLE interactive popup — user chooses to mask or allow.
Only one popup can be open at a time (threading.Lock enforced).

Install deps:
    pip install pyperclip requests win10toast
"""

import time
import re
import threading
import pyperclip
import requests
import json
import os
import math

# ── Desktop Guard ─────────────────────────────────────────────────────────────
try:
    import desktop_guard
    HAS_DESKTOP_GUARD = True
except ImportError:
    HAS_DESKTOP_GUARD = False

# ── Notifier ──────────────────────────────────────────────────────────────────
def _send_notification(title, message):
    """Send a system notification using plyer (works on all platforms/Python versions)."""
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=6)
    except Exception as e:
        print(f"[Vantix] Notification fallback: {title}: {message} (err: {e})")

# ── State ─────────────────────────────────────────────────────────────────────
last_clip   = ""
IS_AUTHORIZED = True
_popup_lock = threading.Lock()   # acquired while popup is visible; non-blocking try
BACKEND     = "http://localhost:5000/api"

# ─── Pattern Tiers ────────────────────────────────────────────────────────────
# IMPORTANT: every pattern lives here ONCE.
# mask_text, check_critical, check_moderate, and show_popup all use these dicts.

CRITICAL_PATTERNS = {
    "PAN Card":        r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
    "Aadhaar":         r'(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}(?!\d)',
    "Credit Card":     r'(?<!\d)(?:\d{4}[\s\-]?){3}\d{4}(?!\d)',
    "Bank Account":    r'(?<!\+)(?<!\d)\d{9,18}(?!\d)',
    "IFSC Code":       r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
    "OpenAI Key":      r'sk-[a-zA-Z0-9]{16,}',
    "OpenAI Proj Key": r'sk-proj-[a-zA-Z0-9_\-]{16,}',
    "AWS Key":         r'AKIA[0-9A-Z]{16}',
    "GitHub Token":    r'ghp_[a-zA-Z0-9]{36}',
    "Google API Key":  r'AIza[0-9A-Za-z\-_]{35}',
    "Stripe Key":      r'sk_live_[0-9a-zA-Z]{24,}',
    "JWT Token":       r'eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+',
    "DB String":       r'(mongodb|mysql|postgresql|redis):\/\/[^\s"\']+',
    "Private IP":      r'\b(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)\d+\.\d+\b',
    "ENV Secret":      r'[A-Z_]{3,}(?:KEY|SECRET|TOKEN|PASSWORD|PASS|PWD|API|APIKEY)\s*=\s*\S+',
    "Generic Secret":  r'(?:export\s+)?[A-Z_]{3,}=["\'`]?[a-zA-Z0-9+/=_\-]{20,}["\'`]?',
    "Slack Token":     r'xoxb-[0-9]{11}-[0-9]{13}-[a-zA-Z0-9]{24}',
}

MODERATE_PATTERNS = {
    "Email":           r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    "Email (hidden)":  r'[a-zA-Z0-9._%+\-]+\s*(?:\(at\)|\[at\]|\bat\b)\s*[a-zA-Z0-9.\-]+\s*(?:\(dot\)|\[dot\]|\bdot\b)\s*[a-zA-Z]{2,}',
    "Phone":           r'(?<!\d)(?:\+?\d{1,3}[\s\-]?)?(?:\d{10}|\d{3}[\s\-\.]?\d{3}[\s\-\.]?\d{4})(?!\d)',
}

# Unified lookup for masking — covers all tiers
ALL_PATTERNS = {**CRITICAL_PATTERNS, **MODERATE_PATTERNS}

# Badge colour map for the popup UI
BADGE_COLORS = {
    "Email":           ("#6c63ff", "#ffffff"),
    "Email (hidden)":  ("#6c63ff", "#ffffff"),
    "Phone":           ("#0099ff", "#ffffff"),
    "PAN Card":        ("#ffaa00", "#000000"),
    "Aadhaar":         ("#ffaa00", "#000000"),
    "Credit Card":     ("#ff4444", "#ffffff"),
    "Bank Account":    ("#ffaa00", "#000000"),
    "IFSC Code":       ("#ffaa00", "#000000"),
    "OpenAI Key":      ("#00d4aa", "#000000"),
    "OpenAI Proj Key": ("#00d4aa", "#000000"),
    "AWS Key":         ("#ff9900", "#000000"),
    "GitHub Token":    ("#24292e", "#ffffff"),
    "Google API Key":  ("#4285f4", "#ffffff"),
    "Stripe Key":      ("#635bff", "#ffffff"),
    "JWT Token":       ("#00d4aa", "#000000"),
    "DB String":       ("#e53935", "#ffffff"),
    "Private IP":      ("#78909c", "#ffffff"),
    "ENV Secret":      ("#00d4aa", "#000000"),
    "Generic Secret":  ("#00d4aa", "#000000"),
    "Slack Token":     ("#4a154b", "#ffffff"),
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_token():
    """Read token from local file or config saved by extension."""
    # Check for local override first
    if os.path.exists("token.txt"):
        try:
            with open("token.txt") as f:
                return f.read().strip()
        except Exception:
            pass

    config_path = os.path.expanduser("~/.vantix/config.json")
    try:
        with open(config_path) as f:
            return json.load(f).get("token", "")
    except Exception:
        return ""


def get_user_info():
    token = get_token()
    if not token:
        return {"role": "general", "company_id": None, "rules": []}

    try:
        import base64
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        role   = payload.get("role", "employee")
        org_id = payload.get("orgId", "")
    except Exception:
        return {"role": "general", "company_id": None, "rules": []}

    rules = []
    monitored_apps = ["ChatGPT", "Notepad"]
    try:
        res = requests.get(
            f"{BACKEND}/rules",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=3,
        )
        if res.status_code == 200:
            data = res.json()
            for src in ("companyRules", "generalRules"):
                for p in data.get(src, {}).get("customPatterns", []):
                    if p.get("label") and p.get("pattern"):
                        rules.append({"name": p["label"], "pattern": p["pattern"], "source": src})
            for kw in data.get("companyRules", {}).get("keywords", []):
                if kw:
                    rules.append({"name": f"Keyword: {kw}", "pattern": re.escape(kw), "source": "company"})
                    
            monitored_apps = data.get("companyRules", {}).get("monitoredApps", monitored_apps)
    except Exception:
        pass

    return {"role": role, "company_id": org_id, "rules": rules, "monitored_apps": monitored_apps}


def log_violation(types):
    """Log the violation to the backend (best-effort)."""
    token = get_token()
    if not token:
        return
    try:
        requests.post(
            f"{BACKEND}/violations",
            json={"url": "clipboard", "matches": [{"type": t} for t in types]},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            timeout=2,
        )
    except Exception:
        pass


def mask_value(val):
    """Partially mask a single value for display."""
    val = str(val).strip()
    if len(val) <= 4:
        return '*' * len(val)
    return val[:2] + '•' * (len(val) - 4) + val[-2:]


def mask_text(text):
    """
    Replace every sensitive pattern in text with a partially masked version.
    Uses ALL_PATTERNS so it's always in sync with the detection engine.
    """
    masked = text
    for name, pattern in ALL_PATTERNS.items():
        def replacer(m, n=name):
            v = m.group()
            if len(v) <= 4:
                return '*' * len(v)
            return v[:2] + '•' * (len(v) - 4) + v[-2:]
        try:
            masked = re.sub(pattern, replacer, masked)
        except re.error:
            pass
    return masked


# ─── Detection helpers ────────────────────────────────────────────────────────

def check_company_rules(text, rules):
    matched = []
    for rule in rules:
        try:
            if re.search(rule["pattern"], text):
                matched.append(rule["name"])
        except re.error:
            pass
    return matched


def check_critical(text):
    """Returns list of matched critical pattern names."""
    return [name for name, pat in CRITICAL_PATTERNS.items() if re.search(pat, text)]


def check_moderate(text):
    """
    Returns list of dicts: [{"type": "Email", "value": "found@text.com"}, ...]
    De-duplicates by (type, value) so the same email only appears once.
    """
    seen      = set()
    detections = []
    for name, pattern in MODERATE_PATTERNS.items():
        for m in re.finditer(pattern, text):
            key = (name, m.group())
            if key not in seen:
                seen.add(key)
                detections.append({"type": name, "value": m.group()})
    return detections


def get_context_words(text, start, end, window=5):
    """Extracts nearby words for contextual proximity analysis."""
    words_before = re.findall(r'\b\w+\b', text[:start])[-window:]
    words_after = re.findall(r'\b\w+\b', text[end:])[:window]
    return [w.lower() for w in words_before + words_after]

def shannon_entropy(data):
    """Calculates entropy to dynamically detect high-randomness secrets."""
    if not data: return 0
    entropy = 0
    for x in set(data):
        p_x = float(data.count(x))/len(data)
        entropy += - p_x * math.log(p_x, 2)
    return entropy

def luhn_checksum(card_number):
    """Validates credit card numbers mathematically."""
    digits = [int(d) for d in str(card_number) if d.isdigit()]
    if len(digits) < 13: return False
    checksum = 0
    is_even = False
    for i in range(len(digits) - 1, -1, -1):
        d = digits[i]
        if is_even:
            d = d * 2
        checksum += d // 10 + d % 10
        is_even = not is_even
    return checksum % 10 == 0

def check_all(text):
    """
    Unified scan — returns a single de-duplicated list of detection dicts
    covering BOTH critical and moderate patterns, with dynamic validation.
    """
    seen       = set()
    detections = []

    for name, pattern in ALL_PATTERNS.items():
        try:
            for m in re.finditer(pattern, text):
                key = (name, m.group())
                if key not in seen:
                    seen.add(key)
                    detections.append({
                        "type": name, 
                        "value": m.group(),
                        "start": m.start(),
                        "end": m.end()
                    })
        except re.error:
            pass

    # Post-processing: Dynamic Validation & Proximity Analysis
    final_detections = []
    value_types = {}
    for d in detections:
        val = d["value"]
        if val not in value_types:
            value_types[val] = set()
        value_types[val].add(d["type"])
        
    for d in detections:
        val = d["value"]
        t = d["type"]
        
        # 1. Mathematical Validation (Checksum)
        if t == "Credit Card":
            if not luhn_checksum(val):
                continue  # Drop invalid card numbers
                
        # 2. Entropy Analysis (Randomness)
        if t in ["Generic Secret", "ENV Secret"]:
            secret_part = val.split("=")[-1].strip("'\"") if "=" in val else val
            if shannon_entropy(secret_part) < 3.2:
                continue  # Drop if it's just a normal word like "PASSWORD=hello"

        # 3. Contextual Proximity Weighting (Bank vs Phone)
        context_words = get_context_words(text, d["start"], d["end"])
        phone_keywords = {"call", "phone", "mobile", "ph", "tel", "contact", "no", "number"}
        bank_keywords = {"bank", "account", "acct", "transfer", "ifsc", "branch", "a/c", "saving"}
        
        has_phone_context = any(w in phone_keywords for w in context_words)
        has_bank_context = any(w in bank_keywords for w in context_words)
        
        overlap_types = {"Phone (IN)", "Phone (US)", "Phone (Intl)", "Aadhaar", "Credit Card"}
        
        if t == "Bank Account":
            # If it looks like a Phone/Aadhaar/CC too
            if not value_types[val].isdisjoint(overlap_types):
                # Only keep "Bank Account" if the surrounding text talks about banks
                if has_bank_context and not has_phone_context:
                    pass
                else:
                    continue # Otherwise drop it and let it be recognized as Phone/Aadhaar
                    
        if "Phone" in t:
            # If it's a 10-digit number but the text is explicitly talking about banks
            if "Bank Account" in value_types[val]:
                if has_bank_context and not has_phone_context:
                    continue # Drop Phone label, it's actually a bank account
            
        final_detections.append(d)

    return final_detections


# ─── Tkinter popup ────────────────────────────────────────────────────────────

def show_popup(detections, original_clip, token=None):
    """
    Show ONE unified tkinter popup for ALL detected sensitive items.
    Thread-safe: uses _popup_lock so only one popup can exist at a time.
    """
    # Non-blocking acquire — if already showing, drop this event
    if not _popup_lock.acquire(blocking=False):
        print("[Vantix] Popup already open — skipping duplicate alert.")
        return

    try:
        import tkinter as tk
    except ImportError:
        print("[Vantix] tkinter not available — auto-masking instead")
        masked = mask_text(original_clip)
        pyperclip.copy(masked)
        _popup_lock.release()
        return

    # ── Theme ────────────────────────────────────────────────────────────────
    BG        = "#0d1117"
    ROW_BG    = "#0f1520"
    ROW_ALT   = "#111820"
    BORDER    = "#1e2530"
    TEAL      = "#00d4aa"
    TEXT      = "#f0f6ff"
    SUBTLE    = "#4a5568"
    MUTED     = "#8899aa"
    DARK_NOTE = "#2d3a4a"

    def get_badge_color(type_name):
        return BADGE_COLORS.get(type_name, ("#6c63ff", "#ffffff"))

    root = tk.Tk()
    root.title("Vantix — Sensitive Data Detected")
    root.configure(bg=BG)
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.overrideredirect(False)

    w, h = 520, 580
    x = (root.winfo_screenwidth()  // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    def on_close():
        _popup_lock.release()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # ── Header ───────────────────────────────────────────────────────────────
    header = tk.Frame(root, bg=BG)
    header.pack(fill="x", padx=24, pady=(18, 0))

    tk.Label(header, text="\U0001f6e1", bg=BG, fg=TEAL,
             font=("Segoe UI", 20)).pack(anchor="w")
    tk.Label(header, text="Warning: Sensitive data detected",
             bg=BG, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(4, 0))
    tk.Label(header, text="Review items below. Check those you want masked before pasting.",
             bg=BG, fg=SUBTLE, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(12, 0))

    # ── Item count + Select All ───────────────────────────────────────────────
    count_row = tk.Frame(root, bg=BG)
    count_row.pack(fill="x", padx=24, pady=(10, 6))
    tk.Label(count_row, text=f"{len(detections)} item(s) found",
             bg=BG, fg=SUBTLE, font=("Segoe UI", 10)).pack(side="left")

    # ── Scrollable list ───────────────────────────────────────────────────────
    list_container = tk.Frame(root, bg=BG)
    list_container.pack(fill="both", expand=True, padx=24)

    canvas    = tk.Canvas(list_container, bg=BG, highlightthickness=0, bd=0)
    scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
    inner     = tk.Frame(canvas, bg=BG)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    cf = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _resize(e):
        canvas.itemconfig(cf, width=e.width)
    canvas.bind("<Configure>", _resize)

    def _update_scrollbar(*args):
        scrollbar.set(*args)
        if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
            scrollbar.pack_forget()
        else:
            scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=_update_scrollbar)
    canvas.pack(side="left", fill="both", expand=True)

    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    checkboxes = []
    for idx, item in enumerate(detections):
        row_color = ROW_BG if idx % 2 == 0 else ROW_ALT
        row = tk.Frame(inner, bg=row_color, pady=8)
        row.pack(fill="x")

        var = tk.BooleanVar(value=True)
        tk.Checkbutton(row, variable=var, bg=row_color,
                       activebackground=row_color, selectcolor=BG,
                       fg="#ffffff", highlightthickness=0, bd=0,
                       ).pack(side="left", padx=(10, 6))

        badge_bg, badge_fg = get_badge_color(item["type"])
        tk.Label(row, text=item["type"], bg=badge_bg, fg=badge_fg,
                 font=("Segoe UI", 9, "bold"), padx=10, pady=3,
                 ).pack(side="left", padx=(0, 8))

        tk.Label(row, text=mask_value(item["value"]),
                 bg=row_color, fg=MUTED,
                 font=("Courier New", 11),
                 ).pack(side="left", padx=(0, 10))

        checkboxes.append((var, item))

        if idx < len(detections) - 1:
            tk.Frame(inner, bg="#1a2030", height=1).pack(fill="x")

    # Select All (placed after checkboxes exist)
    def select_all():
        for v, _ in checkboxes:
            v.set(True)

    tk.Button(count_row, text="Select all", bg=BG, fg=TEAL,
              font=("Segoe UI", 10), relief="flat", bd=0,
              activebackground=BG, activeforeground=TEAL,
              cursor="hand2", command=select_all,
              ).pack(side="right")

    # ── Action buttons ────────────────────────────────────────────────────────
    def mask_selected():
        masked = original_clip
        for var, item in checkboxes:
            if var.get():
                masked = masked.replace(item["value"], mask_value(item["value"]))
        pyperclip.copy(masked)
        if token:
            log_violation([i["type"] for i in detections])
        print("[Vantix] Popup: MASK SELECTED")
        on_close()

    def redact_all():
        masked = original_clip
        for _, item in checkboxes:
            masked = masked.replace(item["value"], "[REDACTED]")
        pyperclip.copy(masked)
        if token:
            log_violation([i["type"] for i in detections])
        print("[Vantix] Popup: REDACT ALL")
        on_close()

    def send_anyway():
        if token:
            log_violation([i["type"] for i in detections])
        print("[Vantix] Popup: SEND ANYWAY (logged)")
        on_close()

    tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(8, 0))
    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(fill="x", padx=24, pady=(14, 0))

    mask_btn = tk.Button(btn_frame, text="Mask selected",
                         bg=TEAL, fg="#021a14", font=("Segoe UI", 10, "bold"),
                         command=mask_selected, relief="flat", padx=16, pady=8,
                         activebackground="#00f0c0", activeforeground="#021a14",
                         cursor="hand2")
    mask_btn.pack(side="left", padx=(0, 6))
    mask_btn.bind("<Enter>", lambda e: mask_btn.configure(bg="#00f0c0"))
    mask_btn.bind("<Leave>", lambda e: mask_btn.configure(bg=TEAL))

    redact_btn = tk.Button(btn_frame, text="Redact all",
                           bg=BORDER, fg="#c8d6e8", font=("Segoe UI", 10),
                           command=redact_all, relief="flat", padx=16, pady=8,
                           activebackground="#2a3540", activeforeground="#c8d6e8",
                           cursor="hand2")
    redact_btn.pack(side="left", padx=(0, 6))
    redact_btn.bind("<Enter>", lambda e: redact_btn.configure(bg="#2a3540"))
    redact_btn.bind("<Leave>", lambda e: redact_btn.configure(bg=BORDER))

    send_btn = tk.Button(btn_frame, text="Send anyway",
                         bg=BG, fg="#ff4444", font=("Segoe UI", 10, "underline"),
                         command=send_anyway, relief="flat", padx=16, pady=8,
                         activebackground="#161b22", activeforeground="#ff6666",
                         cursor="hand2")
    send_btn.pack(side="left")
    send_btn.bind("<Enter>", lambda e: send_btn.configure(bg="#161b22", fg="#ff6666"))
    send_btn.bind("<Leave>", lambda e: send_btn.configure(bg=BG, fg="#ff4444"))

    tk.Label(root, text="'Send anyway' will log this as a violation in the admin dashboard",
             bg=BG, fg=DARK_NOTE, font=("Segoe UI", 9),
             ).pack(padx=24, pady=(6, 14), anchor="w")

    root.mainloop()


# ─── Desktop violation handler ────────────────────────────────────────────────

def _desktop_violation_handler(hits, text, source):
    """Called by desktop_guard when a violation is found while typing."""
    if not IS_AUTHORIZED: return
    types = list({h['type'] for h in hits})
    print(f"[Vantix] Desktop Guard detected: {types} in '{source}'")

    # Build detections in the same format show_popup expects
    detections = [{"type": h["type"], "value": h["value"]} for h in hits]

    # Show the full interactive tkinter popup (non-blocking — runs in this thread which is already a daemon thread)
    if not _popup_lock.locked():
        try:
            show_popup(detections, text, get_token())
        except Exception as e:
            print(f"[Vantix] Popup error: {e}")
            _send_notification(
                "Vantix — Typing Violation",
                f"{', '.join(types[:3])} detected while typing!"
            )
    else:
        # Popup already open — just send a notification reminder
        _send_notification(
            "Vantix — Typing Violation",
            f"{', '.join(types[:3])} detected while typing!"
        )

    try:
        log_violation(types)
    except Exception:
        pass


def status_thread_loop():
    """Background thread sending active app to admin dashboard."""
    global IS_AUTHORIZED
    try:
        import pygetwindow as gw
    except ImportError:
        gw = None

    while True:
        token = get_token()
        if token:
            try:
                active_app = ""
                if gw:
                    active_window = gw.getActiveWindow()
                    if active_window:
                        active_app = active_window.title

                res = requests.put(
                    f"{BACKEND}/users/status",
                    json={"currentApp": active_app},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    timeout=3
                )
                if res.status_code == 200:
                    data = res.json()
                    IS_AUTHORIZED = data.get("isAuthorized", True)
                elif res.status_code in [401, 403, 404]:
                    IS_AUTHORIZED = False
            except Exception:
                pass
        time.sleep(15)


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    global last_clip

    print("=" * 45)
    print("  Vantix Clipboard Agent — v2 (Unified)")
    print("  Monitoring clipboard for sensitive data...")
    print("=" * 45)

    if HAS_DESKTOP_GUARD:
        desktop_guard.init_desktop_guard(_desktop_violation_handler)
    else:
        print("[Vantix] Desktop Guard unavailable (install pynput pygetwindow)")

    user_info = get_user_info()
    role      = user_info["role"]
    print(f"  Role : {role}")
    if role in ("employee", "admin"):
        print(f"  Rules: {len(user_info['rules'])} company rule(s) loaded")
        if HAS_DESKTOP_GUARD:
            desktop_guard.set_watchlist(user_info.get("monitored_apps", []))
    print("=" * 45)

    # Start status heartbeat
    threading.Thread(target=status_thread_loop, daemon=True).start()

    last_refresh     = 0  # Force immediate refresh on start
    REFRESH_INTERVAL = 10 # Check for new rules and watchlist every 10 seconds

    while True:
        try:
            if not IS_AUTHORIZED:
                time.sleep(5)
                continue

            now = time.time()
            if now - last_refresh >= REFRESH_INTERVAL:
                user_info    = get_user_info()
                role         = user_info["role"]
                last_refresh = now
                if role in ("employee", "admin") and HAS_DESKTOP_GUARD:
                    desktop_guard.set_watchlist(user_info.get("monitored_apps", []))
                print(f"[Vantix] Refreshed user — role: {role}, rules: {len(user_info['rules'])}")

            clip = pyperclip.paste()

            # Skip if clipboard hasn't changed or is too short
            if not clip or clip == last_clip or len(clip.strip()) <= 5:
                time.sleep(0.5)
                continue

            # Skip if popup is already open (lock is held)
            if _popup_lock.locked():
                time.sleep(0.5)
                continue

            last_clip = clip
            token     = get_token()

            # ── Company rules (employee / admin only) ──────────────────────
            if role in ("employee", "admin") and user_info["rules"]:
                company_matches = check_company_rules(clip, user_info["rules"])
                if company_matches:
                    # Company rules → silent auto-mask + toast
                    masked = mask_text(clip)
                    pyperclip.copy(masked)
                    last_clip = masked
                    _send_notification(
                        "Vantix — Clipboard Masked",
                        f"{', '.join(company_matches[:3])} auto-masked (company policy)"
                    )
                    log_violation(company_matches)
                    print(f"[Vantix] MASKED (company rule): {company_matches}")
                    time.sleep(0.5)
                    continue

            # ── Unified detection across ALL patterns ──────────────────────
            detections = check_all(clip)

            if detections:
                types = [d["type"] for d in detections]
                print(f"[Vantix] Detected: {types}")

                # Launch the single interactive popup in a background thread
                popup_thread = threading.Thread(
                    target=show_popup,
                    args=(detections, clip, token),
                    daemon=True,
                )
                popup_thread.start()
                time.sleep(0.5)
                continue

            print(f"[Vantix] Clipboard OK ({len(clip)} chars)")

        except Exception as e:
            print(f"[Vantix] Error: {e}")

        time.sleep(0.5)


if __name__ == "__main__":
    main()
