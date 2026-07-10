"""
InventoryPro - Dashboard Page
Summary cards + recent activity feed.
"""
import customtkinter as ctk
from utils.theme import COLORS, get_font
from data.database import get_connection
from ui.components import StatusBadge


class DashboardPage(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._build()

    def _build(self):
        # Header
        ctk.CTkLabel(
            self, text="Dashboard",
            font=get_font(24, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(
            self, text=f"Welcome back, {self._user.get('display_name', 'Admin')}",
            font=get_font(13),
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(0, 24))

        # Summary cards row
        stats = self._get_stats()
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 20))

        card_data = [
            ("Total Items",    stats["total_items"],    COLORS["primary"],  "📦"),
            ("Assigned",       stats["assigned"],       COLORS["info"],     "🔗"),
            ("Available",      stats["available"],      COLORS["success"],  "✅"),
            ("Total Employees",stats["employees"],      COLORS["secondary"],"👥"),
        ]
        for i, (label, value, color, icon) in enumerate(card_data):
            cards_frame.columnconfigure(i, weight=1)
            self._build_stat_card(cards_frame, label, value, color, icon, i)

        # Bottom section: recent activity + items by status
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, pady=(4, 0))
        bottom.columnconfigure(0, weight=2)
        bottom.columnconfigure(1, weight=1)
        bottom.rowconfigure(0, weight=1)

        self._build_recent_activity(bottom)
        self._build_status_summary(bottom, stats)

    def _build_stat_card(self, parent, label, value, color, icon, col):
        card = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"],
            corner_radius=12
        )
        card.grid(row=0, column=col, padx=(0 if col == 0 else 10, 0), sticky="ew")

        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=28)).pack(padx=20, pady=(20, 4), anchor="w")
        ctk.CTkLabel(
            card, text=str(value),
            font=ctk.CTkFont(family="Fira Code", size=32, weight="bold"),
            text_color=color
        ).pack(padx=20, anchor="w")
        ctk.CTkLabel(
            card, text=label,
            font=get_font(12),
            text_color=COLORS["text_secondary"]
        ).pack(padx=20, pady=(2, 20), anchor="w")

    def _build_recent_activity(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12)
        frame.grid(row=0, column=0, padx=(0, 12), sticky="nsew", pady=0)

        ctk.CTkLabel(
            frame, text="Recent Activity",
            font=get_font(15, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=20, pady=(20, 12))

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT action_type, entity_type, entity_id, performed_by, timestamp, before_state, after_state
            FROM audit_log ORDER BY timestamp DESC LIMIT 12
        """)
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(
                frame, text="No activity yet.",
                font=get_font(12),
                text_color=COLORS["text_muted"]
            ).pack(padx=20, pady=20)
            return

        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent", height=260)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        action_colors = {
            "create": COLORS["success"],
            "update": COLORS["primary"],
            "delete": COLORS["danger"],
            "assign": COLORS["info"],
            "return": COLORS["warning"],
            "status_change": COLORS["secondary"],
        }

        for row in rows:
            action = row["action_type"]
            color = action_colors.get(action, COLORS["text_muted"])
            ts = row["timestamp"][:16].replace("T", " ") if row["timestamp"] else ""

            item_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_surface"], corner_radius=8)
            item_frame.pack(fill="x", pady=3)

            dot = ctk.CTkLabel(item_frame, text="●", font=get_font(10), text_color=color)
            dot.pack(side="left", padx=(12, 8), pady=10)

            # Extract human-readable name from state JSON or repositories
            display_name = row["entity_type"].title()
            
            def get_item_name(i_id):
                if not i_id: return "Item"
                if not hasattr(self, "_item_cache"): 
                    from data.repositories.item_repo import ItemRepository
                    self._item_repo = ItemRepository()
                    self._item_cache = {}
                if i_id not in self._item_cache:
                    i = self._item_repo.get_by_id(i_id)
                    self._item_cache[i_id] = i.name if i else "Unknown Item"
                return self._item_cache[i_id]

            def get_emp_name(e_id):
                if not e_id: return "Employee"
                if not hasattr(self, "_emp_cache"):
                    from data.repositories.employee_repo import EmployeeRepository
                    self._emp_repo = EmployeeRepository()
                    self._emp_cache = {}
                if e_id not in self._emp_cache:
                    emp = self._emp_repo.get_by_id(e_id)
                    self._emp_cache[e_id] = emp.full_name if emp else "Unknown Employee"
                return self._emp_cache[e_id]

            try:
                state_str = row["after_state"] or row["before_state"]
                if state_str:
                    import json
                    state = json.loads(state_str)
                    
                    if action == "assign":
                        i_name = get_item_name(state.get("item_id"))
                        e_name = get_emp_name(state.get("employee_id"))
                        display_name = f"'{i_name}' to {e_name}"
                    elif action == "return":
                        i_name = get_item_name(state.get("item_id"))
                        e_name = get_emp_name(state.get("employee_id"))
                        display_name = f"'{i_name}' from {e_name}"
                    elif action == "status_change":
                        i_name = get_item_name(row["entity_id"])
                        display_name = f"'{i_name}' status"
                    elif row["entity_type"] == "employee":
                        display_name = state.get("full_name") or display_name
                    elif row["entity_type"] == "item":
                        display_name = state.get("name") or state.get("model") or display_name
            except Exception:
                pass

            ctk.CTkLabel(
                item_frame,
                text=f"{action.replace('_', ' ').title()} {display_name}",
                font=get_font(11, "bold"),
                text_color=COLORS["text_primary"]
            ).pack(side="left")

            ctk.CTkLabel(
                item_frame, text=ts,
                font=get_font(10),
                text_color=COLORS["text_muted"]
            ).pack(side="right", padx=12)

    def _build_status_summary(self, parent, stats):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12)
        frame.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            frame, text="Items by Status",
            font=get_font(15, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=20, pady=(20, 12))

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT s.name, s.color_hex, COUNT(i.id) as count
            FROM statuses s
            LEFT JOIN items i ON i.status_id = s.id
            GROUP BY s.id
            ORDER BY count DESC
        """)
        rows = c.fetchall()
        conn.close()

        for row in rows:
            count = row["count"]
            if count == 0:
                continue
            status_name = row["name"].replace("_", " ").title()
            color = row["color_hex"]
            total = max(stats["total_items"], 1)
            pct = count / total

            row_frame = ctk.CTkFrame(frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=16, pady=4)

            ctk.CTkLabel(
                row_frame, text=status_name,
                font=get_font(11),
                text_color=COLORS["text_secondary"],
                width=100, anchor="w"
            ).pack(side="left")

            bar_bg = ctk.CTkFrame(row_frame, fg_color=COLORS["border"],
                                  corner_radius=4, height=8, width=100)
            bar_bg.pack(side="left", padx=8)
            bar_fill = ctk.CTkFrame(bar_bg, fg_color=color,
                                    corner_radius=4, height=8,
                                    width=max(int(100 * pct), 4))
            bar_fill.place(x=0, y=0)

            ctk.CTkLabel(
                row_frame, text=str(count),
                font=get_font(11, "bold"),
                text_color=COLORS["text_primary"]
            ).pack(side="left")

    def _get_stats(self) -> dict:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM items")
        total_items = c.fetchone()[0]
        c.execute("""
            SELECT COUNT(*) FROM items i
            JOIN statuses s ON i.status_id = s.id WHERE s.name = 'assigned'
        """)
        assigned = c.fetchone()[0]
        c.execute("""
            SELECT COUNT(*) FROM items i
            JOIN statuses s ON i.status_id = s.id WHERE s.name = 'available'
        """)
        available = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM employees WHERE status='active'")
        employees = c.fetchone()[0]
        conn.close()
        return {"total_items": total_items, "assigned": assigned,
                "available": available, "employees": employees}
