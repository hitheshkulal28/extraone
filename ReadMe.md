# 🛡️ Vantix — Sensitive Data Guard

Vantix is a powerful Data Loss Prevention (DLP) solution designed to protect sensitive information from leaking into third-party AI platforms like ChatGPT, Google Gemini, and Claude. 

**Built for Everyone**: Whether you are an enterprise seeking to enforce corporate data policies or an individual user looking to protect your personal privacy, Vantix operates through a real-time Chrome extension that actively monitors user input. It identifies and auto-masks generic Personally Identifiable Information (PII) alongside custom keywords before the data ever leaves the browser.

## 🚀 Key Features

* **Real-time AI Platform Monitoring**: Silently runs on AI interfaces (ChatGPT, Claude, Gemini) scanning for violations on the fly.
* **Dual Modes of Operation**:
  * **Enterprise Mode**: Multi-tenant architecture for organizations. Configure custom domains, keywords, and rule bypasses via an Admin Dashboard. Features automated auto-masking for company secrets.
  * **Individual Mode**: Perfect for personal safety. Protects everyday users from accidentally pasting credit cards, SSNs, API keys, or personal emails into AI models. Includes a generous free tier (up to 50 scans).
* **Smart Auto-Masking**: Automatically replaces custom company keywords with inline asterisks (`***`), ensuring context is retained while protecting sensitive variables.
* **General PII Protection**: Built-in detection for standard sensitive data (Credit Cards, SSNs, API Keys, Emails, Phone Numbers).
* **Admin Dashboard Analytics (Enterprise)**: A modern, dark-mode React Dashboard featuring rich charts, timeline views, Top Offender lists, and platform usage metrics.
* **Active User Heartbeats**: Tracks active employee usage daily. Includes an automated chron job that emails administrators and users if they disable or abandon the protection extension.

## 📂 Project Structure

This repository contains the complete Vantix ecosystem, divided into three main applications:

1. **`vantix-admin/` (Frontend Dashboard)**
   * A responsive, beautifully crafted Vite + React frontend dashboard.
   * Allows organization admins to track violations, manage rules, invite employees, and view rich data visualizations (Recharts).

2. **`vantix-backend/` (Node.js API)**
   * An Express & MongoDB backend handling authentication, rule delivery, and logging.
   * Multi-tenancy enabled via organizational scoping (`orgId`).
   * Includes automated cron jobs (`inactivityChecker.js`) using Nodemailer to alert inactive employees.

3. **`vantix-extension-v2/` (Chrome Extension)**
   * A Manifest V3 Chrome Extension.
   * Communicates seamlessly with the backend via `background.js` and uses a localized algorithm in `content.js`/`detector.js` to execute real-time regex matching and UI interceptions (blocking the send button, showing warning modals).

## 🛠️ Tech Stack

* **Frontend**: React, Vite, CSS Modules, Recharts
* **Backend**: Node.js, Express, MongoDB, Mongoose, JWT Authentication
* **Extension**: Vanilla JavaScript, Chrome Extension API (Manifest V3)
* **Utilities**: Nodemailer (SMTP alerting), Dotenv
* **Agent**: Python 3, pyperclip, win10toast, requests, pynput, pygetwindow, phonenumbers

## 🤖 Vantix Agent — What's Detected

### Clipboard Guard (always-on)
| Type | Examples |
|---|---|
| PAN Card | ABCDE1234F |
| Aadhaar | 1234 5678 9012 or 1234-5678-9012 |
| Credit Card | 4111 1111 1111 1111 |
| API Keys | OpenAI `sk-...`, AWS `AKIA...`, GitHub `ghp_...`, Stripe `sk_live_...`, Google `AIza...`, OpenAI Project `sk-proj-...`, Slack `xoxb-...` |
| JWT Token | `eyJ...` |
| DB Connection String | `mongodb://`, `mysql://`, `postgresql://` |
| Private IP | 192.168.x.x, 10.x.x.x, 172.16-31.x.x |
| IFSC Code | HDFC0001234 |
| Bank Account | 9–18 digit numbers |
| ENV Secrets | `API_KEY=abc123`, `export SECRET=xyz` |
| Email (standard) | user@gmail.com |
| Email (obfuscated) | user (at) gmail (dot) com |
| Phone (Indian) | +91 9876543210, 9876543210 |
| Phone (International) | +1 415-555-0100 |
| Phone (US) | (415) 555-0100 |

### Desktop Guard (new — monitors typing in selected apps)
* **What it does**: Watches your **keystrokes** inside selected desktop applications (ChatGPT, Claude, Slack, etc.) and alerts you if you type sensitive data.
* **How to configure**: On first run, a popup asks which apps to monitor. Settings are saved to `~/.vantix/desktop_guard.json`.
* **Libraries used**:
  * `pynput` — low-level keyboard hook
  * `pygetwindow` — detects active window title
  * `phonenumbers` — validates phone numbers using Google's library


## 🚦 Getting Started

### Prerequisites
* Node.js (v18+ recommended)
* MongoDB Database (Local or MongoDB Atlas)

### 1. Setup the Backend
```bash
cd vantix-backend
npm install
```
Create a `.env` file in the `vantix-backend` directory:
```env
MONGO_URI=mongodb://127.0.0.1:27017/vantix
PORT=5000
JWT_SECRET=your_jwt_secret
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM=your_email@gmail.com
INACTIVITY_DAYS=3
```
Run the server:
```bash
npm run dev
```

### 2. Setup the Admin Dashboard
```bash
cd vantix-admin
npm install
```
Run the development server:
```bash
npm run dev
```

### 3. Setup the Clipboard Agent (Python)
```bash
cd vantix-agent
python -m pip install pyperclip requests win10toast
python agent.py
```

### 4. Setup Custom Presidio Service (Python)
```bash
python -m pip install flask presidio-analyzer
python presidio_custom.py
```

### 5. Load the Chrome Extension
1. Open Google Chrome and navigate to `chrome://extensions/`
2. Enable **"Developer mode"** in the top right corner.
3. Click **"Load unpacked"** and select the `vantix-extension-v2` folder.
4. Click the Vantix puzzle piece icon in your browser to sign in to your Employee or Admin account.

## 🔒 Security & Privacy First

Vantix's detection runs entirely inside the user's browser via the extension's content scripts. Keystrokes are **never** logged to the server. The backend only receives metadata when a violation policy is breached (e.g., the platform used and the type of data matched), ensuring maximum user privacy.

---
*Developed for robust data compliance and enterprise AI safety.*
