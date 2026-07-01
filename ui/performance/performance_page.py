"""
InventoryPro - Computer Performance Page
Fleet-wide ranking with score badges and replacement alerts.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.repositories.specs_repo import SpecsRepository
from data.models import ComputerSpecs


TIER_COLORS = {
    "Excellent": "#22C55E",
    "Good":      "#3B82F6",
    "Fair":      "#F59E0B",
    "Poor":      "#EF4444",
    "Incomplete":"#64748B",
}


class PerformancePage(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._repo = SpecsRepository()
        self._build()
        self._load()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        header.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Performance",
                     font=get_font(22, "bold"),
                     text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(left, text="Computer fleet evaluation & ranking",
                     font=get_font(12),
                     text_color=COLORS["text_secondary"]).pack(anchor="w")

        ctk.CTkButton(
            header, text="↻  Refresh",
            font=get_font(12),
            fg_color=COLORS["bg_surface"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8, height=36, width=100,
            command=self._load
        ).grid(row=0, column=1, sticky="e")

        # Summary cards row
        self._summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._summary_frame.pack(fill="x", pady=(0, 20))

        # Alert + list
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True)

    # ── Load & Render ─────────────────────────────────────────────────────────
    def _load(self):
        for w in self._summary_frame.winfo_children():
            w.destroy()
        for w in self._body.winfo_children():
            w.destroy()

        all_specs = self._repo.get_all_scored()

        if not all_specs:
            ctk.CTkLabel(
                self._body,
                text="No computer specs found.\n\nAdd items with category 'Laptop' or 'Desktop'\nand fill in their specs to see the ranking.",
                font=get_font(14), text_color=COLORS["text_muted"],
                justify="center"
            ).pack(expand=True)
            return

        scored = [s for s in all_specs if s.perf_score and s.perf_score > 0]
        incomplete = [s for s in all_specs if not s.perf_score or s.perf_score == 0]

        self._render_summary(scored, incomplete)
        self._render_list(scored, incomplete)

    def _render_summary(self, scored: list, incomplete: list):
        """Top 3 stat cards: Best · Worst · Fleet Average."""
        cards_data = []

        if scored:
            best = scored[0]
            worst = scored[-1]
            avg = int(sum(s.perf_score for s in scored) / len(scored))
            cards_data = [
                ("🏆  Best Machine",
                 getattr(best, "item_name", "—"),
                 f"Score: {best.perf_score} — {best.tier}",
                 best.tier_color),
                ("⚠️  Needs Replacement",
                 getattr(worst, "item_name", "—"),
                 f"Score: {worst.perf_score} — {worst.tier}",
                 worst.tier_color),
                ("📊  Fleet Average",
                 f"{avg} / 100",
                 f"{len(scored)} scored · {len(incomplete)} incomplete",
                 COLORS["primary"]),
            ]
        else:
            cards_data = [
                ("📊  Fleet", f"{len(incomplete)} computers",
                 "All have incomplete specs", COLORS["text_muted"]),
            ]

        for title, value, subtitle, color in cards_data:
            card = ctk.CTkFrame(self._summary_frame, fg_color=COLORS["bg_card"],
                                corner_radius=12)
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))

            ctk.CTkLabel(card, text=title, font=get_font(11),
                         text_color=COLORS["text_secondary"]).pack(anchor="w", padx=16, pady=(14, 2))
            ctk.CTkLabel(card, text=value, font=get_font(17, "bold"),
                         text_color=color).pack(anchor="w", padx=16)
            ctk.CTkLabel(card, text=subtitle, font=get_font(10),
                         text_color=COLORS["text_muted"]).pack(anchor="w", padx=16, pady=(2, 14))

    def _render_list(self, scored: list, incomplete: list):
        """Full ranked list + incomplete section."""
        # Poor-scoring alert banner
        poor = [s for s in scored if s.perf_score and s.perf_score < 45]
        if poor:
            banner = ctk.CTkFrame(self._body, fg_color="#451A03", corner_radius=10)
            banner.pack(fill="x", pady=(0, 12))
            ctk.CTkLabel(
                banner,
                text=f"⚠  {len(poor)} computer(s) scored below 45 — consider replacement",
                font=get_font(12, "bold"), text_color="#F97316"
            ).pack(side="left", padx=16, pady=10)

        # Scored list
        if scored:
            ctk.CTkLabel(self._body, text="Ranked Computers",
                         font=get_font(13, "bold"),
                         text_color=COLORS["text_primary"]).pack(anchor="w", pady=(0, 8))

            scroll = ctk.CTkScrollableFrame(self._body, fg_color="transparent")
            scroll.pack(fill="both", expand=True)

            for rank, specs in enumerate(scored, start=1):
                self._render_computer_card(scroll, rank, specs)

        # Incomplete section
        if incomplete:
            ctk.CTkLabel(self._body, text="Incomplete Specs",
                         font=get_font(13, "bold"),
                         text_color=COLORS["text_muted"]).pack(anchor="w", pady=(16, 8))
            for specs in incomplete:
                self._render_incomplete_card(self._body, specs)

    def _render_computer_card(self, parent, rank: int, specs: ComputerSpecs):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_surface"], corner_radius=10)
        card.pack(fill="x", pady=4)

        # Rank badge
        rank_color = {1: "#F59E0B", 2: "#94A3B8", 3: "#B45309"}.get(rank, COLORS["text_muted"])
        rank_badge = ctk.CTkFrame(card, fg_color=rank_color if rank <= 3 else COLORS["bg_card"],
                                  width=44, corner_radius=0)
        rank_badge.pack(side="left", fill="y")
        rank_badge.pack_propagate(False)
        ctk.CTkLabel(rank_badge, text=f"#{rank}", font=get_font(13, "bold"),
                     text_color="white" if rank <= 3 else COLORS["text_muted"]).place(
            relx=0.5, rely=0.5, anchor="center"
        )

        # Main info
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        name = getattr(specs, "item_name", "Unknown")
        brand = getattr(specs, "item_brand", "") or ""
        model = getattr(specs, "item_model", "") or ""
        assigned = getattr(specs, "assigned_to", None)

        ctk.CTkLabel(info, text=name, font=get_font(13, "bold"),
                     text_color=COLORS["text_primary"]).pack(anchor="w")

        spec_str = "  ·  ".join(filter(None, [
            f"{specs.cpu_cores}c/{specs.cpu_ghz}GHz" if specs.cpu_cores else None,
            f"{specs.ram_gb}GB RAM" if specs.ram_gb else None,
            f"{specs.storage_gb}GB {specs.storage_type}" if specs.storage_gb else None,
            f"Year: {specs.purchase_year}" if specs.purchase_year else None,
        ]))
        ctk.CTkLabel(info, text=spec_str or "Specs not available",
                     font=get_font(10), text_color=COLORS["text_muted"]).pack(anchor="w")

        if assigned:
            ctk.CTkLabel(info, text=f"👤  {assigned}",
                         font=get_font(10), text_color=COLORS["text_secondary"]).pack(anchor="w")

        # Score badge (right side)
        score_frame = ctk.CTkFrame(card, fg_color="transparent")
        score_frame.pack(side="right", padx=16, pady=10)

        # Map tier to a safe dim background color
        tier_dim = {
            "Excellent": "#14532D",
            "Good":      "#1D3461",
            "Fair":      "#451A03",
            "Poor":      "#450A0A",
            "Incomplete":"#1E293B",
        }
        score_bg_color = tier_dim.get(specs.tier, "#1E293B")

        score_bg = ctk.CTkFrame(score_frame, fg_color=score_bg_color, corner_radius=8)
        score_bg.pack()

        ctk.CTkLabel(score_bg, text=str(specs.perf_score or 0),
                     font=get_font(22, "bold"),
                     text_color=specs.tier_color).pack(padx=14, pady=(6, 0))
        ctk.CTkLabel(score_bg, text=specs.tier,
                     font=get_font(9), text_color=specs.tier_color).pack(padx=14, pady=(0, 6))

        # Poor indicator
        if specs.perf_score and specs.perf_score < 45:
            ctk.CTkLabel(card, text="Replace",
                         font=get_font(9, "bold"),
                         text_color="#F97316").pack(side="right", padx=(0, 8))

    def _render_incomplete_card(self, parent, specs: ComputerSpecs):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_surface"], corner_radius=8, height=42)
        card.pack(fill="x", pady=2)
        card.pack_propagate(False)

        ctk.CTkLabel(card, text="●", font=get_font(10),
                     text_color=COLORS["text_muted"]).pack(side="left", padx=(12, 6))
        ctk.CTkLabel(card, text=getattr(specs, "item_name", "Unknown"),
                     font=get_font(12), text_color=COLORS["text_secondary"]).pack(side="left")
        ctk.CTkLabel(card, text="— Incomplete",
                     font=get_font(10), text_color=COLORS["text_muted"]).pack(side="left", padx=4)
        assigned = getattr(specs, "assigned_to", None)
        if assigned:
            ctk.CTkLabel(card, text=f"👤 {assigned}",
                         font=get_font(10), text_color=COLORS["text_muted"]).pack(side="right", padx=14)
