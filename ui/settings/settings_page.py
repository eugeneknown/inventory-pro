"""
InventoryPro - Settings Page
Manage departments, categories, statuses, users, and Google auth setup.
"""
import customtkinter as ctk
import hashlib
from utils.theme import COLORS, get_font
from data.database import get_connection
from ui.components import Toast, ConfirmDialog
import uuid


class SettingsPage(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Settings",
            font=get_font(22, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            self, text="Configure departments, categories, statuses, users, and Google Sync",
            font=get_font(12),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 20))

        # Tab view
        tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS["bg_card"],
            segmented_button_fg_color=COLORS["bg_surface"],
            segmented_button_selected_color=COLORS["primary"],
            segmented_button_unselected_color=COLORS["bg_surface"],
            text_color=COLORS["text_primary"],
            corner_radius=12
        )
        tabs.pack(fill="both", expand=True)

        # Add tabs
        tabs.add("Departments")
        tabs.add("Categories")
        tabs.add("Statuses")
        tabs.add("Users")
        tabs.add("Google Sync")
        tabs.add("Organization")
        if self._user.get("role") == "admin":
            tabs.add("Integrations")
            tabs.add("System Logs")

        self._build_list_tab(tabs.tab("Departments"), "departments", "name")
        self._build_list_tab(tabs.tab("Categories"), "categories", "name")
        self._build_status_tab(tabs.tab("Statuses"))
        self._build_users_tab(tabs.tab("Users"))
        self._build_google_tab(tabs.tab("Google Sync"))
        self._build_org_tab(tabs.tab("Organization"))
        if self._user.get("role") == "admin":
            self._build_integrations_tab(tabs.tab("Integrations"))
            self._build_logs_tab(tabs.tab("System Logs"))

    # ── Generic list tab (Departments / Categories) ───────────────────────────
    def _build_list_tab(self, parent, table: str, col: str):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        add_row.pack(fill="x", pady=(0, 16))

        entry = ctk.CTkEntry(
            add_row, placeholder_text=f"New {table[:-1]} name...",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(13),
            corner_radius=8, height=38
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        list_frame = ctk.CTkScrollableFrame(frame, fg_color=COLORS["bg_surface"], corner_radius=10)
        list_frame.pack(fill="both", expand=True)

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            conn = get_connection()
            c = conn.cursor()
            c.execute(f"SELECT id, {col} FROM {table} ORDER BY {col}")
            rows = c.fetchall()
            conn.close()
            for row in rows:
                self._build_list_item(list_frame, table, col, dict(row), refresh)

        def add_item():
            name = entry.get().strip()
            if not name:
                return
            conn = get_connection()
            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO {table} (id, {col}) VALUES (?, ?)",
                    (str(uuid.uuid4()), name)
                )
                conn.commit()
                conn.close()
                entry.delete(0, "end")
                refresh()
                Toast.show(self, f"'{name}' added.", "success")
            except Exception as e:
                conn.close()
                Toast.show(self, str(e), "error")

        ctk.CTkButton(
            add_row, text="+ Add",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=38, width=80,
            command=add_item
        ).pack(side="left")
        entry.bind("<Return>", lambda e: add_item())
        refresh()

    def _build_list_item(self, parent, table: str, col: str, row: dict, refresh):
        item_frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8, height=42)
        item_frame.pack(fill="x", pady=2)
        item_frame.pack_propagate(False)

        ctk.CTkLabel(
            item_frame, text=row[col],
            font=get_font(13),
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=14, pady=10)

        def delete():
            def do():
                conn = get_connection()
                conn.execute(f"DELETE FROM {table} WHERE id=?", (row["id"],))
                conn.commit()
                conn.close()
                refresh()
                Toast.show(self, f"'{row[col]}' deleted.", "success")

            ConfirmDialog(
                self, title="Delete",
                message=f"Delete '{row[col]}'? Items using it will lose this reference.",
                on_confirm=do, danger=True
            )

        ctk.CTkButton(
            item_frame, text="Delete",
            font=get_font(10),
            fg_color=COLORS["danger_dim"], hover_color=COLORS["danger"],
            text_color=COLORS["danger"], corner_radius=6,
            height=26, width=60,
            command=delete
        ).pack(side="right", padx=10, pady=8)

    # ── Status Tab ────────────────────────────────────────────────────────────
    def _build_status_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Add row
        add_row = ctk.CTkFrame(frame, fg_color="transparent")
        add_row.pack(fill="x", pady=(0, 8))

        name_entry = ctk.CTkEntry(
            add_row, placeholder_text="Status name (e.g. In Storage)...",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(13),
            corner_radius=8, height=38
        )
        name_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        color_var = ctk.StringVar(value="#94A3B8")
        color_entry = ctk.CTkEntry(
            add_row, textvariable=color_var,
            placeholder_text="#HEX",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=ctk.CTkFont(family="Fira Code", size=12),
            corner_radius=8, height=38, width=90
        )
        color_entry.pack(side="left", padx=(0, 8))

        list_frame = ctk.CTkScrollableFrame(frame, fg_color=COLORS["bg_surface"], corner_radius=10)
        list_frame.pack(fill="both", expand=True)

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM statuses ORDER BY is_system DESC, name")
            rows = c.fetchall()
            conn.close()
            for row in rows:
                self._build_status_item(list_frame, dict(row), refresh)

        def add_status():
            name = name_entry.get().strip()
            color = color_var.get().strip() or "#94A3B8"
            if not name:
                return
            conn = get_connection()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO statuses (id, name, color_hex) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), name.lower().replace(" ", "_"), color)
                )
                conn.commit()
                conn.close()
                name_entry.delete(0, "end")
                refresh()
                Toast.show(self, f"Status '{name}' added.", "success")
            except Exception as e:
                conn.close()
                Toast.show(self, str(e), "error")

        ctk.CTkButton(
            add_row, text="+ Add",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=38, width=80,
            command=add_status
        ).pack(side="left")
        refresh()

    def _build_status_item(self, parent, row: dict, refresh):
        item_frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8, height=44)
        item_frame.pack(fill="x", pady=2)
        item_frame.pack_propagate(False)

        # Color swatch
        color = row.get("color_hex", "#94A3B8")
        ctk.CTkFrame(item_frame, fg_color=color, width=12, corner_radius=6).pack(
            side="left", padx=(12, 8), pady=12, fill="y"
        )

        ctk.CTkLabel(
            item_frame,
            text=row["name"].replace("_", " ").title(),
            font=get_font(13), text_color=COLORS["text_primary"]
        ).pack(side="left")

        if row.get("is_system"):
            ctk.CTkLabel(
                item_frame, text="System",
                font=get_font(9), text_color=COLORS["text_muted"]
            ).pack(side="right", padx=12)
        else:
            def delete(r=row):
                def do():
                    conn = get_connection()
                    conn.execute("DELETE FROM statuses WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                    refresh()
                ConfirmDialog(
                    self, title="Delete Status",
                    message=f"Delete '{r['name']}'? Items with this status will lose it.",
                    on_confirm=do, danger=True
                )

            ctk.CTkButton(
                item_frame, text="Delete",
                font=get_font(10),
                fg_color=COLORS["danger_dim"], hover_color=COLORS["danger"],
                text_color=COLORS["danger"], corner_radius=6,
                height=26, width=60, command=delete
            ).pack(side="right", padx=10, pady=8)

    # ── Users Tab ─────────────────────────────────────────────────────────────
    def _build_users_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Only admins can manage users
        if self._user.get("role") != "admin":
            ctk.CTkLabel(
                frame, text="Admin access required to manage users.",
                font=get_font(13), text_color=COLORS["text_muted"]
            ).pack(pady=40)
            return

        list_frame = ctk.CTkScrollableFrame(frame, fg_color=COLORS["bg_surface"], corner_radius=10)
        list_frame.pack(fill="both", expand=True, pady=(0, 16))

        def refresh():
            for w in list_frame.winfo_children():
                w.destroy()
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM users ORDER BY role, username")
            rows = c.fetchall()
            conn.close()
            for row in rows:
                self._build_user_item(list_frame, dict(row), refresh)

        refresh()

        # Add user button
        ctk.CTkButton(
            frame, text="+ Add User",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=38,
            command=lambda: AddUserDialog(self, on_save=refresh)
        ).pack(anchor="e")

    def _build_user_item(self, parent, row: dict, refresh):
        item_frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8, height=50)
        item_frame.pack(fill="x", pady=2)
        item_frame.pack_propagate(False)

        ctk.CTkLabel(
            item_frame, text=row["display_name"],
            font=get_font(13, "bold"), text_color=COLORS["text_primary"]
        ).pack(side="left", padx=14)
        ctk.CTkLabel(
            item_frame, text=f"@{row['username']}",
            font=get_font(11), text_color=COLORS["text_muted"]
        ).pack(side="left")
        ctk.CTkLabel(
            item_frame, text=row["role"].upper(),
            font=get_font(10, "bold"), text_color=COLORS["primary"]
        ).pack(side="left", padx=8)

        if row["username"] != "admin":
            def delete(r=row):
                def do():
                    conn = get_connection()
                    conn.execute("DELETE FROM users WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                    refresh()
                ConfirmDialog(
                    self, title="Delete User",
                    message=f"Delete user '{r['username']}'?",
                    on_confirm=do, danger=True
                )

            ctk.CTkButton(
                item_frame, text="Delete",
                font=get_font(10),
                fg_color=COLORS["danger_dim"], hover_color=COLORS["danger"],
                text_color=COLORS["danger"], corner_radius=6,
                height=26, width=60, command=delete
            ).pack(side="right", padx=10, pady=10)

    # ── Google Sync Tab ───────────────────────────────────────────────────────
    def _build_google_tab(self, parent):
        import os
        from config import CREDENTIALS_PATH

        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            frame, text="Google Sheets Sync Setup",
            font=get_font(16, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 16))

        # Status
        exists = os.path.exists(CREDENTIALS_PATH)
        status_text = "✓ Credentials configured" if exists else "✗ No credentials found"
        status_color = COLORS["success"] if exists else COLORS["danger"]
        ctk.CTkLabel(
            frame, text=status_text,
            font=get_font(13, "bold"), text_color=status_color
        ).pack(anchor="w", pady=(0, 20))

        # Step-by-step guide
        steps = [
            ("Step 1 — Go to Google Cloud Console",
             "Visit: https://console.cloud.google.com\nCreate a new project or select an existing one."),
            ("Step 2 — Enable APIs",
             "Enable both:\n• Google Sheets API\n• Google Drive API\n\nSearch for them in 'APIs & Services > Library'."),
            ("Step 3 — Create a Service Account",
             "Go to: IAM & Admin > Service Accounts\nClick 'Create Service Account'\nGive it any name (e.g. 'inventorypro-sync')\nRole: 'Editor' is sufficient."),
            ("Step 4 — Download JSON Key",
             "In the Service Account, go to the 'Keys' tab.\nClick 'Add Key > Create New Key > JSON'.\nSave the downloaded file."),
            ("Step 5 — Share your Google Sheet",
             "Open your Google Sheet (or let the app create one).\nClick Share and add the Service Account email\n(shown in the JSON file as 'client_email').\nGive it 'Editor' access."),
            ("Step 6 — Place the credentials file",
             f"Rename the downloaded JSON file to:\n  google_credentials.json\n\nPlace it at:\n  {CREDENTIALS_PATH}"),
        ]

        for title, body in steps:
            step_card = ctk.CTkFrame(frame, fg_color=COLORS["bg_surface"], corner_radius=10)
            step_card.pack(fill="x", pady=6)

            ctk.CTkLabel(
                step_card, text=title,
                font=get_font(12, "bold"), text_color=COLORS["primary"]
            ).pack(anchor="w", padx=16, pady=(12, 4))

            ctk.CTkLabel(
                step_card, text=body,
                font=ctk.CTkFont(family="Fira Code", size=11),
                text_color=COLORS["text_secondary"],
                justify="left", wraplength=600
            ).pack(anchor="w", padx=16, pady=(0, 12))

        def browse_credentials():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="Select Google Service Account JSON",
                filetypes=[("JSON files", "*.json")]
            )
            if path:
                import shutil
                try:
                    shutil.copy(path, CREDENTIALS_PATH)
                except shutil.SameFileError:
                    pass # Already the same file, nothing to copy
                Toast.show(self, "Credentials saved! Sync will start on next check.", "success")
                # Rebuild tab to update status
                for w in parent.winfo_children():
                    w.destroy()
                self._build_google_tab(parent)

        ctk.CTkButton(
            frame, text="Browse & Set Credentials File",
            font=get_font(13, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=42,
            command=browse_credentials
        ).pack(anchor="w", pady=16)

    # ── Organization Tab ──────────────────────────────────────────────────────
    def _build_org_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM app_settings WHERE key='org_name'")
        row = c.fetchone()
        org_name = row["value"] if row else "My Organization"
        conn.close()

        ctk.CTkLabel(
            frame, text="Organization Name",
            font=get_font(11), text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 4))

        org_entry = ctk.CTkEntry(
            frame, fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=get_font(13), corner_radius=8, height=40
        )
        org_entry.insert(0, org_name)
        org_entry.pack(fill="x", pady=(0, 16))

        def save_org():
            name = org_entry.get().strip()
            if not name:
                return
            conn = get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('org_name', ?)",
                (name,)
            )
            conn.commit()
            conn.close()
            Toast.show(self, "Organization name saved.", "success")

        ctk.CTkButton(
            frame, text="Save",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=38, width=100,
            command=save_org
        ).pack(anchor="w")

        # Change password section
        ctk.CTkFrame(frame, fg_color=COLORS["border"], height=1).pack(fill="x", pady=20)

        ctk.CTkLabel(
            frame, text="Change Password",
            font=get_font(14, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 12))

        self._old_pw = ctk.CTkEntry(
            frame, placeholder_text="Current password",
            show="•", fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=get_font(13), corner_radius=8, height=38
        )
        self._old_pw.pack(fill="x", pady=(0, 8))

        self._new_pw = ctk.CTkEntry(
            frame, placeholder_text="New password",
            show="•", fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=get_font(13), corner_radius=8, height=38
        )
        self._new_pw.pack(fill="x", pady=(0, 8))

        self._pw_error = ctk.CTkLabel(
            frame, text="", font=get_font(11), text_color=COLORS["danger"]
        )
        self._pw_error.pack(anchor="w")

        def change_password():
            old = self._old_pw.get()
            new = self._new_pw.get()
            if not old or not new:
                self._pw_error.configure(text="Both fields required.")
                return
            if len(new) < 6:
                self._pw_error.configure(text="New password must be at least 6 characters.")
                return
            old_hash = hashlib.sha256(old.encode()).hexdigest()
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT id FROM users WHERE id=? AND password_hash=?",
                (self._user["id"], old_hash)
            )
            if not c.fetchone():
                conn.close()
                self._pw_error.configure(text="Current password incorrect.")
                return
            new_hash = hashlib.sha256(new.encode()).hexdigest()
            conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                         (new_hash, self._user["id"]))
            conn.commit()
            conn.close()
            self._pw_error.configure(text="")
            self._old_pw.delete(0, "end")
            self._new_pw.delete(0, "end")
            Toast.show(self, "Password changed successfully.", "success")

        ctk.CTkButton(
            frame, text="Change Password",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=38,
            command=change_password
        ).pack(anchor="w", pady=8)


    # ── Integrations Tab ───────────────────────────────────────────────────────
    def _build_integrations_tab(self, parent):
        frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # Load saved values
        conn = get_connection()
        c = conn.cursor()
        settings = {}
        for key in ("discord_webhook_url", "github_repo", "github_token", "gemini_api_key", "gemini_model"):
            c.execute("SELECT value FROM app_settings WHERE key=?", (key,))
            row = c.fetchone()
            settings[key] = row["value"] if row else ""
        conn.close()

        def _make_section(title: str, subtitle: str):
            ctk.CTkLabel(frame, text=title, font=get_font(14, "bold"),
                         text_color=COLORS["text_primary"]).pack(anchor="w", pady=(16, 2))
            ctk.CTkLabel(frame, text=subtitle, font=get_font(11),
                         text_color=COLORS["text_secondary"], wraplength=620,
                         justify="left").pack(anchor="w", pady=(0, 10))

        def _make_field(label: str, placeholder: str, value: str, show: str = "") -> ctk.CTkEntry:
            ctk.CTkLabel(frame, text=label, font=get_font(11),
                         text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(6, 2))
            e = ctk.CTkEntry(frame, placeholder_text=placeholder,
                             fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                             text_color=COLORS["text_primary"], font=get_font(13),
                             corner_radius=8, height=40, show=show)
            e.insert(0, value)
            e.pack(fill="x", pady=(0, 4))
            return e

        def _divider():
            ctk.CTkFrame(frame, fg_color=COLORS["border"], height=1).pack(fill="x", pady=16)

        # ── Discord Error Reporting ──────────────────────────────────────────
        _make_section(
            "🔔  Discord Error Reporting",
            "Any crash or exception in the app will be automatically sent to your Discord channel. "
            "Get your Webhook URL from: Server Settings → Integrations → Webhooks → New Webhook."
        )
        discord_entry = _make_field(
            "Webhook URL",
            "https://discord.com/api/webhooks/...",
            settings["discord_webhook_url"]
        )

        def test_discord():
            url = discord_entry.get().strip()
            if not url:
                Toast.show(self, "Please enter a Webhook URL first.", "error")
                return
            
            # Auto-save the URL since they are testing it
            conn = get_connection()
            conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", 
                         ("discord_webhook_url", url))
            conn.commit()
            conn.close()

            from utils.error_reporter import configure, report_message
            configure(url)
            report_message(
                "✅ InventoryPro Connected",
                "Error reporting is now active! You will receive crash notifications here.",
                color=0x22C55E
            )
            Toast.show(self, "Test message sent & Webhook URL saved!", "success")

        test_btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        test_btn_row.pack(fill="x", pady=(0, 4))
        ctk.CTkButton(test_btn_row, text="Send Test Message",
                      font=get_font(11), fg_color=COLORS["bg_surface"],
                      hover_color=COLORS["bg_hover"], text_color=COLORS["text_primary"],
                      corner_radius=8, height=34, width=160,
                      command=test_discord).pack(side="left", padx=(0, 8))

        _divider()

        # ── Auto-Updater ─────────────────────────────────────────────────────
        _make_section(
            "🚀  Auto-Updater (GitHub)",
            "Enter your GitHub repository so the app can check for updates automatically on startup. "
            "Format: username/repository-name  (e.g. eugenedev/inventorypro)."
        )
        repo_entry  = _make_field("GitHub Repository", "username/inventorypro", settings["github_repo"])
        token_entry = _make_field("GitHub Token (optional, for private repos)",
                                  "ghp_...", settings["github_token"], show="•")

        from updater.core import get_local_version
        ctk.CTkLabel(frame, text=f"Current app version:  v{get_local_version()}",
                     font=get_font(11), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(4, 0))

        _divider()

        # ── Gemini API Settings ──────────────────────────────────────────────
        _make_section(
            "✨  AI Auto-Fill Setup (Gemini API)",
            "Get a free key from aistudio.google.com to enable auto-filling computer and item specs automatically."
        )
        gemini_entry = _make_field("Gemini API Key", "Paste your Gemini API Key here", settings["gemini_api_key"], show="•")
        gemini_model_entry = _make_field("Gemini Model Version", "e.g. gemini-2.5-flash", settings["gemini_model"] or "gemini-2.5-flash")

        _divider()

        # ── Save all ─────────────────────────────────────────────────────────
        def save_all():
            data = {
                "discord_webhook_url": discord_entry.get().strip(),
                "github_repo":         repo_entry.get().strip(),
                "github_token":        token_entry.get().strip(),
                "gemini_api_key":      gemini_entry.get().strip(),
                "gemini_model":        gemini_model_entry.get().strip() or "gemini-2.5-flash",
            }
            conn = get_connection()
            for key, value in data.items():
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                    (key, value)
                )
            conn.commit()
            conn.close()

            # Apply immediately without restart
            from utils.error_reporter import configure as cfg_err
            cfg_err(webhook_url=data["discord_webhook_url"])
            from updater.core import set_config as cfg_upd
            cfg_upd(github_repo=data["github_repo"], github_token=data["github_token"])

            Toast.show(self, "Integration settings saved.", "success")

        ctk.CTkButton(
            frame, text="Save Integration Settings",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            corner_radius=8, height=42,
            command=save_all
        ).pack(fill="x", pady=(8, 20))


    # ── System Logs Tab ────────────────────────────────────────────────────────
    def _build_logs_tab(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            frame, text="Local Error & Event Logs", 
            font=get_font(14, "bold"), text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 8))

        # Textbox for logs
        log_box = ctk.CTkTextbox(
            frame, fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_secondary"], font=("Consolas", 11),
            corner_radius=8, wrap="word"
        )
        log_box.pack(fill="both", expand=True, pady=(0, 16))

        def refresh_logs():
            import os
            from config import DATA_DIR
            log_file = os.path.join(DATA_DIR, "system_errors.log")
            log_box.delete("1.0", "end")
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    if not content.strip():
                        log_box.insert("end", "Log file is empty.")
                    else:
                        log_box.insert("end", content)
                except Exception as e:
                    log_box.insert("end", f"Could not read logs: {e}")
            else:
                log_box.insert("end", "No logs recorded yet.")
            log_box.see("end")

        def clear_logs():
            import os
            from config import DATA_DIR
            log_file = os.path.join(DATA_DIR, "system_errors.log")
            if os.path.exists(log_file):
                try:
                    os.remove(log_file)
                except Exception:
                    pass
            refresh_logs()
            Toast.show(self, "Logs cleared.", "success")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text="Refresh Logs",
            fg_color=COLORS["bg_surface"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(11),
            corner_radius=8, height=34,
            command=refresh_logs
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Clear Logs",
            fg_color=COLORS["danger"], hover_color=COLORS.get("danger_hover", "#B91C1C"),
            font=get_font(11, "bold"), corner_radius=8, height=34,
            command=clear_logs
        ).pack(side="left")

        # Initial load
        refresh_logs()

    # ── User Dialog ───────────────────────────────────────────────────────────
class AddUserDialog(ctk.CTkToplevel):

    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self._on_save = on_save
        self.title("Add User")
        self.geometry("400x480")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_card"])
        self.grab_set()
        self.lift()
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_surface"], corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="Add User", font=get_font(15, "bold"),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=20, pady=14)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=16)

        fields = [
            ("username",     "Username *"),
            ("display_name", "Display Name *"),
            ("password",     "Password *"),
        ]
        self._fields = {}
        for key, label in fields:
            ctk.CTkLabel(form, text=label, font=get_font(11),
                         text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
            entry = ctk.CTkEntry(
                form,
                show="•" if key == "password" else "",
                fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                text_color=COLORS["text_primary"], font=get_font(13),
                corner_radius=8, height=38
            )
            entry.pack(fill="x")
            self._fields[key] = entry

        ctk.CTkLabel(form, text="Role", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
        self._role_var = ctk.StringVar(value="manager")
        self._role_combo = ctk.CTkComboBox(
            form, values=["admin", "manager"],
            variable=self._role_var,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["border"], button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=38, state="readonly"
        )
        self._role_combo.pack(fill="x")
        from ui.components.ctk_scrollable_dropdown import CTkScrollableDropdown
        CTkScrollableDropdown(
            self._role_combo, values=["admin", "manager"],
            command=lambda v: (self._role_var.set(v), self._role_combo.set(v)),
            autocomplete=False, justify="left", height=100,
            fg_color=COLORS["bg_card"], button_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["text_primary"],
            frame_border_color=COLORS["border"], scrollbar_button_color=COLORS["border"],
            font=get_font(12),
        )

        self._error = ctk.CTkLabel(self, text="", font=get_font(11),
                                   text_color=COLORS["danger"])
        self._error.pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=12)

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color=COLORS["bg_input"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"], font=get_font(12),
            corner_radius=8, height=38, command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Create User",
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            font=get_font(12, "bold"), corner_radius=8, height=38,
            command=self._save
        ).pack(side="left", expand=True, fill="x")

    def _save(self):
        username = self._fields["username"].get().strip()
        display_name = self._fields["display_name"].get().strip()
        password = self._fields["password"].get().strip()

        if not username or not display_name or not password:
            self._error.configure(text="All fields required.")
            return
        if len(password) < 6:
            self._error.configure(text="Password must be at least 6 characters.")
            return

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO users (id, username, display_name, role, password_hash) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()), username, display_name, self._role_var.get(), pw_hash)
            )
            conn.commit()
            conn.close()
            if self._on_save:
                self._on_save()
            self.after(10, self.destroy)
        except Exception as e:
            conn.close()
            self._error.configure(text=str(e))
