"""
InventoryPro - Login Screen
"""
import customtkinter as ctk
import hashlib
from utils.theme import COLORS, get_font
from data.database import get_connection


class LoginScreen(ctk.CTkFrame):
    """Full-screen login with username/password and role selection."""

    def __init__(self, parent, on_login_success, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_app"], **kwargs)
        self._on_success = on_login_success
        self._build()

    def _build(self):
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.columnconfigure(0, weight=0)   # brand panel
        self.columnconfigure(1, weight=1)   # form panel
        self.rowconfigure(0, weight=1)

        # ── Left brand panel ──────────────────────────────────────────────────
        brand = ctk.CTkFrame(self, fg_color=COLORS["primary_dim"],
                             width=320, corner_radius=0)
        brand.grid(row=0, column=0, sticky="nsew")
        brand.grid_propagate(False)
        brand.rowconfigure(0, weight=1)
        brand.columnconfigure(0, weight=1)

        brand_inner = ctk.CTkFrame(brand, fg_color="transparent")
        brand_inner.grid(row=0, column=0)

        ctk.CTkLabel(
            brand_inner, text="Inventory",
            font=ctk.CTkFont(family="Fira Code", size=30, weight="bold"),
            text_color=COLORS["primary"]
        ).pack()
        ctk.CTkLabel(
            brand_inner, text="PRO",
            font=ctk.CTkFont(family="Fira Code", size=12),
            text_color=COLORS["text_muted"]
        ).pack(pady=(0, 20))

        ctk.CTkFrame(brand_inner, fg_color=COLORS["border"],
                     height=1, width=160).pack(pady=(0, 20))

        for line in ["Track. Assign.", "Manage. Sync."]:
            ctk.CTkLabel(
                brand_inner, text=line,
                font=ctk.CTkFont(family="Fira Code", size=11),
                text_color=COLORS["text_secondary"]
            ).pack(pady=3)

        # ── Right login form ──────────────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color=COLORS["bg_app"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        # Card is centered via grid row/col weights
        card = ctk.CTkFrame(right, fg_color=COLORS["bg_card"], corner_radius=20)
        card.grid(row=0, column=0)  # no sticky → naturally centered

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=48, pady=48)

        # Heading
        ctk.CTkLabel(
            inner, text="Welcome back",
            font=get_font(24, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner, text="Sign in to access your inventory",
            font=get_font(12),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(4, 28))

        # Username
        ctk.CTkLabel(inner, text="Username", font=get_font(12),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        self._username = ctk.CTkEntry(
            inner,
            placeholder_text="Enter your username",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=2,
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
            font=get_font(14),
            corner_radius=10,
            height=48,
            width=380,
        )
        self._username.pack(anchor="w", pady=(6, 18))

        # Password
        ctk.CTkLabel(inner, text="Password", font=get_font(12),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")
        self._password = ctk.CTkEntry(
            inner,
            placeholder_text="Enter your password",
            show="•",
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=2,
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_muted"],
            font=get_font(14),
            corner_radius=10,
            height=48,
            width=380,
        )
        self._password.pack(anchor="w", pady=(6, 6))

        # Error label
        self._error = ctk.CTkLabel(
            inner, text="",
            font=get_font(11),
            text_color=COLORS["danger"],
            width=380, anchor="w"
        )
        self._error.pack(anchor="w", pady=(4, 18))

        # Sign In button
        self._login_btn = ctk.CTkButton(
            inner,
            text="Sign In  →",
            font=get_font(14, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=10,
            height=50,
            width=380,
            command=self._attempt_login
        )
        self._login_btn.pack(anchor="w")

        # Hint
        ctk.CTkLabel(
            inner,
            text="Default: admin  /  admin123",
            font=get_font(10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(16, 0))

        # Keybinds
        self._password.bind("<Return>", lambda e: self._attempt_login())
        self._username.bind("<Return>", lambda e: self._password.focus())
        self._username.focus()

    def _attempt_login(self):
        username = self._username.get().strip()
        password = self._password.get().strip()

        if not username or not password:
            self._error.configure(text="Please enter username and password.")
            return

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=? AND is_active=1",
            (username, pw_hash)
        )
        user = c.fetchone()
        conn.close()

        if user:
            self._error.configure(text="")
            user_dict = dict(user)
            self.place_forget()
            self._on_success(user_dict)
        else:
            self._error.configure(text="Invalid username or password.")
            self._password.delete(0, "end")
