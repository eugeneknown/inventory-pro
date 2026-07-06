"""
InventoryPro - Item List Page
Filterable inventory table with barcode scan, add, edit, delete, print label.
"""
import customtkinter as ctk
from tkinter import filedialog
from utils.theme import COLORS, get_font
from data.repositories.item_repo import ItemRepository
from data.repositories.audit_repo import AuditRepository
from ui.components import (SectionHeader, SearchBar, FilterDropdown,
                            DataTable, ConfirmDialog, Toast, EmptyState)
import threading


class ItemListPage(ctk.CTkFrame):

    def __init__(self, parent, user: dict, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._user = user
        self._repo = ItemRepository()
        self._audit = AuditRepository()
        self._search_query = ""
        self._cat_filter = "All"
        self._status_filter = "All"
        self._fetch_id = 0
        self._build()
        self._load()

    def _build(self):
        # Header with two action buttons
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header_frame, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(left, text="Inventory", font=get_font(22, "bold"),
                     text_color=COLORS["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(left, text="Track and manage all equipment",
                     font=get_font(12), text_color=COLORS["text_secondary"]).pack(anchor="w")

        right = ctk.CTkFrame(header_frame, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            right, text="↑ Import CSV",
            font=get_font(12),
            fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8, height=36,
            command=self._import_csv
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right, text="↓ Export CSV",
            font=get_font(12),
            fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8, height=36,
            command=self._export_csv
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right, text="🖨  Print Labels",
            font=get_font(12),
            fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=8, height=36,
            command=self._print_selected_labels
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right, text="📷  Scan Barcode",
            font=get_font(12),
            fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["secondary"],
            corner_radius=8, height=36,
            command=self._scan_barcode
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            right, text="+ Add Item",
            font=get_font(13, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=8, height=36,
            command=self._open_add_form
        ).pack(side="left")

        # Filters
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", pady=(0, 16))

        SearchBar(
            filters, placeholder="Search by name, serial, brand...",
            on_change=self._on_search
        ).pack(side="left", fill="x", expand=True, padx=(0, 16))

        cats = self._repo.get_categories()
        FilterDropdown(
            filters, label="Category:",
            options=["All"] + [c["name"] for c in cats],
            on_change=self._on_cat_filter
        ).pack(side="left", padx=(0, 12))

        statuses = self._repo.get_statuses()
        FilterDropdown(
            filters, label="Status:",
            options=["All"] + [s["name"].replace("_", " ").title() for s in statuses],
            on_change=self._on_status_filter
        ).pack(side="left")

        # Table container
        self._table_container = ctk.CTkFrame(self, fg_color="transparent")
        self._table_container.pack(fill="both", expand=True)

    def _load(self):
        self._fetch_id += 1
        current_fetch = self._fetch_id

        for w in self._table_container.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self._table_container,
            text="Loading...",
            font=get_font(14),
            text_color=COLORS["text_secondary"]
        ).pack(expand=True)

        cat_filter = self._cat_filter
        status_filter = self._status_filter
        search_query = self._search_query

        def fetch():
            cat_id = None
            if cat_filter != "All":
                cats = self._repo.get_categories()
                cat_id = next((c["id"] for c in cats if c["name"] == cat_filter), None)

            status_id = None
            if status_filter != "All":
                statuses = self._repo.get_statuses()
                status_id = next(
                    (s["id"] for s in statuses
                     if s["name"].replace("_", " ").title() == status_filter), None
                )

            items = self._repo.get_all(
                category_id=cat_id,
                status_id=status_id,
                search=search_query or None
            )
            self.after(0, lambda: self._render(items, current_fetch))

        threading.Thread(target=fetch, daemon=True).start()

    def _render(self, items, fetch_id=None):
        if fetch_id is not None and fetch_id != self._fetch_id:
            return

        for w in self._table_container.winfo_children():
            w.destroy()

        if not items:
            EmptyState(
                self._table_container,
                icon="📦",
                title="No items found",
                subtitle="Add an item manually or scan a barcode."
            ).pack(fill="both", expand=True)
            return

        columns = [
            ("item_id",        "Item ID",       110),
            ("serial_number",  "Serial Number", 140),
            ("name",           "Name",          180),
            ("brand",          "Brand",         100),
            ("category_name",  "Category",      120),
            ("status_name",    "Status",        110),
            ("assigned_to",    "Assigned To",   150),
        ]

        rows = [
            {
                "item_id":        i.item_id,
                "serial_number":  i.serial_number or "—",
                "name":           i.name,
                "brand":          i.brand or "—",
                "category_name":  i.category_name or "—",
                "status_name":    i.status_name or "available",
                "status":         i.status_name or "available",
                "assigned_to":    i.assigned_to or "—",
                "_id":            i.id,
                "_obj":           i,
            }
            for i in items
        ]

        table = DataTable(
            self._table_container,
            columns=columns,
            on_row_click=self._open_detail,
            actions=[
                ("Edit",   COLORS["primary"], self._edit_row),
                ("Delete", COLORS["danger"],  self._delete_row),
            ]
        )
        table.pack(fill="both", expand=True)
        table.load(rows)

    def _scan_barcode(self):
        path = filedialog.askopenfilename(
            title="Select barcode image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")]
        )
        if not path:
            return

        from barcodes.scanner import decode_barcode_from_file
        serial = decode_barcode_from_file(path)

        if not serial:
            Toast.show(self, "Could not decode barcode from image. Try a clearer image.", "error")
            return

        # Check if already in DB
        existing = self._repo.get_by_serial(serial)
        if existing:
            Toast.show(self, f"Item with serial '{serial}' already exists.", "warning")
            return

        Toast.show(self, f"Barcode decoded: {serial}. Looking up product info...", "info")
        self._open_add_form(prefill_serial=serial, do_lookup=True)

    def _open_detail(self, row: dict):
        from ui.inventory.item_detail import ItemDetailDialog
        ItemDetailDialog(self, item=row["_obj"],
                         current_user=self._user, on_change=self._load)

    def _open_add_form(self, prefill_serial: str = None, do_lookup: bool = False):
        from ui.inventory.item_form import ItemFormDialog
        ItemFormDialog(
            self, user=self._user,
            prefill_serial=prefill_serial,
            do_lookup=do_lookup,
            on_save=self._load
        )

    def _edit_row(self, row: dict):
        from ui.inventory.item_form import ItemFormDialog
        ItemFormDialog(self, user=self._user, item=row["_obj"], on_save=self._load)

    def _delete_row(self, row: dict):
        def do_delete():
            try:
                before = {"name": row["name"], "serial_number": row["serial_number"]}
                self._repo.delete(row["_id"])
                self._audit.log(
                    "delete", "item", row["_id"],
                    before=before, after=None,
                    performed_by=self._user.get("display_name", "admin")
                )
                Toast.show(self, f"'{row['name']}' deleted.", "success")
                self._load()
            except ValueError as e:
                Toast.show(self, str(e), "error")

        ConfirmDialog(
            self, title="Delete Item",
            message=f"Delete '{row['name']}' ({row['serial_number']})?\nThis action is logged.",
            on_confirm=do_delete, danger=True
        )

    def _print_selected_labels(self):
        """Print labels for all currently shown items."""
        items = self._repo.get_all(search=self._search_query or None)
        if not items:
            Toast.show(self, "No items to print.", "warning")
            return

        from barcodes.label_printer import generate_label_pdf
        import subprocess
        label_items = [
            {"serial_number": i.serial_number, "name": i.name,
             "brand": i.brand, "model": i.model}
            for i in items[:50]  # Max 50 per print job
        ]
        pdf_path = generate_label_pdf(label_items)
        Toast.show(self, f"Labels generated: {pdf_path}", "success")
        subprocess.Popen(["start", "", pdf_path], shell=True)

    def _export_csv(self):
        import os, subprocess
        from utils.csv_io import export_items_csv
        path = export_items_csv(self._user.get("display_name", "admin"))
        if path:
            Toast.show(self, f"Exported: {os.path.basename(path)}", "success")
            subprocess.Popen(["explorer", "/select,", path])

    def _import_csv(self):
        from utils.csv_io import import_items_csv
        result = import_items_csv(self._user.get("display_name", "admin"))
        if result["imported"] > 0 or result["skipped"] > 0:
            msg = f"Imported: {result['imported']}  Skipped: {result['skipped']}"
            Toast.show(self, msg, "success" if result["imported"] > 0 else "warning")
            if result["errors"]:
                print("[Import] Errors:\n" + "\n".join(result["errors"]))
            self._load()

    def _on_search(self, q): 
        print(f"[DEBUG] Search triggered with query: '{q}'")
        self._search_query = q
        self._load()

    def _on_cat_filter(self, v): self._cat_filter = v; self._load()
    def _on_status_filter(self, v): self._status_filter = v; self._load()
