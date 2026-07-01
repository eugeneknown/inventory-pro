<div align="center">
  <img src="https://img.icons8.com/color/96/000000/box-important.png" alt="InventoryPro Logo" width="80" />
  <h1>InventoryPRO</h1>
  <p><strong>Next-Generation IT Asset & Inventory Management Desktop Application</strong></p>

  <p>
    <a href="#features">Features</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#integrations">Integrations</a> •
    <a href="#installation">Installation</a>
  </p>
</div>

---

## 🚀 Overview

**InventoryPRO** is a professional, high-performance desktop application designed for modern IT and Asset Management. Built with a sleek, responsive UI and an offline-first architecture, it ensures your hardware data is always accessible, lightning-fast, and safely backed up to the cloud.

This application was engineered from the ground up to solve the real-world pain points of equipment tracking—eliminating manual data entry with AI, handling offline networks seamlessly, and providing completely silent remote updates.

## ✨ Key Features

### 🧠 AI-Powered Data Entry (Gemini API)
Stop manually Googling computer specs. Simply type the laptop model (e.g., "ThinkPad T14 Gen 2"), and InventoryPRO's integrated **Google Gemini AI Pipeline** will automatically fetch, parse, and auto-fill the RAM, CPU, Storage, GPU, and descriptive metadata in seconds.

### 🔄 Offline-First Google Sheets Sync
Works completely offline. Uses a custom **bi-directional Sync Engine** powered by an SQLite backend. Changes are logged to a robust Audit Queue and pushed silently to a connected Google Spreadsheet in the background once network connectivity is restored.

### 🛡️ Discord Crash & Error Telemetry
Built for production. A custom global exception hook catches any runtime errors across the application (including Tkinter UI callbacks) and instantly delivers a rich diagnostic stack trace to a private **Discord Webhook** channel. 

### 📡 Invisible Auto-Updater
End-users never have to download a `.zip` file again. The app silently pings its parent GitHub repository on startup. If an update is detected, it offers a 1-click **"Update & Restart"** banner that fetches and hot-patches individual `.py` files without full extraction.

### 👥 Comprehensive Asset Lifecycle
- **Check-in / Check-out:** Fluidly assign equipment to employees and track full assignment history.
- **Audit Logs:** A "Recent Activity" timeline parses historical state-snapshots to provide human-readable tracking of who changed what, and when.
- **Role-Based Access Control:** Differentiates between 'Manager' and 'Admin' privileges (Admins get access to API Integrations and advanced configuration).

---

## 🏗️ Technical Architecture

- **Frontend UI:** Built with `customtkinter` for a deeply customized, modern dark-mode aesthetic. 
- **Local Database:** `sqlite3` configured with `PRAGMA journal_mode=WAL` for high-concurrency read/write operations without locking the UI thread.
- **Cloud Backend:** Google Workspace API (`gspread`, `oauth2client`) executing via dedicated background threads.
- **Language:** Python 3.12+

---

## 🛠️ Third-Party Integrations

| Integration | Purpose | Setup |
| :--- | :--- | :--- |
| **Google Sheets API** | Live Cloud Backup & Remote View | Requires Service Account JSON |
| **Google Gemini API** | AI-Powered Spec Autofill | Free API Key via Google AI Studio |
| **Discord Webhooks** | Real-time Error Telemetry | Standard Discord Channel Webhook |
| **GitHub API** | Remote File Hot-Patching | Public or Private Repository Auth |

---

## 💻 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/inventorypro.git
   cd inventorypro
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   # Use the provided batch script for easy execution
   .\run.bat
   ```

4. **Initial Login:**
   - **Username:** `admin`
   - **Password:** `admin123` *(You will be prompted to change this)*

---

<div align="center">
  <i>Designed and developed by Eugene.</i>
</div>
