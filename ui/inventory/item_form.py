"""
InventoryPro - Item Form Dialog
Add / Edit item with model-name lookup, serial generation,
and conditional Computer Specs section.
"""
import customtkinter as ctk
import threading
from tkinter import filedialog
from utils.theme import COLORS, get_font
from data.repositories.item_repo import ItemRepository
from data.repositories.audit_repo import AuditRepository
from data.repositories.specs_repo import SpecsRepository, is_computer_category
from data.models import Item
from ui.components import Toast
from typing import Optional, Callable

# Categories that show the specs panel
COMPUTER_CATS = {"laptop", "desktop", "computer"}


class ItemFormDialog(ctk.CTkToplevel):

    def __init__(self, parent, user: dict,
                 item: Optional[Item] = None,
                 prefill_serial: Optional[str] = None,
                 do_lookup: bool = False,
                 on_save: Optional[Callable] = None, **kwargs):
        super().__init__(parent)
        self._user = user
        self._item = item
        self._on_save = on_save
        self._repo = ItemRepository()
        self._audit = AuditRepository()
        self._specs_repo = SpecsRepository()
        self._is_edit = item is not None
        self._specs_frame_ref = None   # holds the Computer Specs frame widget

        title = "Edit Item" if self._is_edit else "Add Item"
        self.title(title)
        self.geometry("580x780")
        self.resizable(False, True)
        self.configure(fg_color=COLORS["bg_card"])
        self.grab_set()
        self.lift()

        self._build(title)
        if self._is_edit:
            self._populate()
        elif prefill_serial:
            self._fields["serial_number"].insert(0, prefill_serial)

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build(self, title: str):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_surface"],
                               corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text=title, font=get_font(16, "bold"),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=24, pady=16)

        self._form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._form.pack(fill="both", expand=True, padx=24, pady=16)

        self._fields = {}
        self._spec_fields = {}

        # ── Serial number row ─────────────────────────────────────────────────
        ctk.CTkLabel(self._form, text="Serial Number *", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 2))
        serial_row = ctk.CTkFrame(self._form, fg_color="transparent")
        serial_row.pack(fill="x", pady=(0, 12))

        serial_entry = ctk.CTkEntry(
            serial_row,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(family="Fira Code", size=13),
            corner_radius=8, height=38
        )
        serial_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._fields["serial_number"] = serial_entry

        ctk.CTkButton(
            serial_row, text="Generate",
            font=get_font(11), fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["secondary"],
            corner_radius=8, height=38, width=90,
            command=self._generate_serial
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            serial_row, text="Scan",
            font=get_font(11), fg_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["info"],
            corner_radius=8, height=38, width=60,
            command=self._scan_from_form
        ).pack(side="left")

        # ── Brand + Model row with 🔍 Look Up ────────────────────────────────
        ctk.CTkLabel(self._form, text="Item Name *", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
        self._fields["name"] = ctk.CTkEntry(
            self._form, fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(13),
            corner_radius=8, height=38
        )
        self._fields["name"].pack(fill="x")

        bm_row = ctk.CTkFrame(self._form, fg_color="transparent")
        bm_row.pack(fill="x", pady=(8, 0))
        bm_row.columnconfigure(0, weight=1)
        bm_row.columnconfigure(1, weight=1)

        ctk.CTkLabel(bm_row, text="Brand", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(bm_row, text="Model", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(8, 0))

        self._fields["brand"] = ctk.CTkEntry(
            bm_row, fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(13),
            corner_radius=8, height=38
        )
        self._fields["brand"].grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._fields["model"] = ctk.CTkEntry(
            bm_row, fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(13),
            corner_radius=8, height=38
        )
        self._fields["model"].grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))

        # Lookup button + status label
        lookup_row = ctk.CTkFrame(self._form, fg_color="transparent")
        lookup_row.pack(fill="x", pady=(8, 4))

        self._lookup_btn = ctk.CTkButton(
            lookup_row, text="✨ Auto-Fill Specs",
            font=get_font(12, "bold"),
            fg_color=COLORS["primary_dim"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["primary"],
            corner_radius=8, height=36,
            command=self._trigger_lookup
        )
        self._lookup_btn.pack(side="left")

        self._lookup_label = ctk.CTkLabel(
            lookup_row, text="", font=get_font(10),
            text_color=COLORS["info"]
        )
        self._lookup_label.pack(side="left", padx=(12, 0))

        # ── Category ──────────────────────────────────────────────────────────
        ctk.CTkLabel(self._form, text="Category", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
        cats = self._repo.get_categories()
        self._cat_ids = {c["name"]: c["id"] for c in cats}
        self._cat_var = ctk.StringVar(value="(None)")
        cat_options = ["(None)"] + [c["name"] for c in cats]
        self._cat_menu = ctk.CTkComboBox(
            self._form, values=cat_options,
            variable=self._cat_var,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["border"], button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=38, state="readonly"
        )
        self._cat_menu.pack(fill="x")
        from ui.components.ctk_scrollable_dropdown import CTkScrollableDropdown
        CTkScrollableDropdown(
            self._cat_menu, values=cat_options,
            command=lambda v: (self._cat_var.set(v), self._cat_menu.set(v), self._on_category_change(v)),
            autocomplete=True, justify="left", height=200,
            fg_color=COLORS["bg_card"], button_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["text_primary"],
            frame_border_color=COLORS["border"], scrollbar_button_color=COLORS["border"],
            font=get_font(12),
        )

        # ── Status ────────────────────────────────────────────────────────────
        ctk.CTkLabel(self._form, text="Status", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
        statuses = self._repo.get_statuses()
        self._status_ids = {s["name"]: s["id"] for s in statuses}
        self._status_var = ctk.StringVar(value="available")
        status_names = [s["name"] for s in statuses]
        self._status_combo = ctk.CTkComboBox(
            self._form, values=status_names,
            variable=self._status_var,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["border"], button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(12),
            corner_radius=8, height=38, state="readonly"
        )
        self._status_combo.pack(fill="x")
        CTkScrollableDropdown(
            self._status_combo, values=status_names,
            command=lambda v: (self._status_var.set(v), self._status_combo.set(v)),
            autocomplete=False, justify="left", height=200,
            fg_color=COLORS["bg_card"], button_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["text_primary"],
            frame_border_color=COLORS["border"], scrollbar_button_color=COLORS["border"],
            font=get_font(12),
        )

        # ── Other fields ──────────────────────────────────────────────────────
        for key, label, multiline in [
            ("purchase_date",  "Purchase Date (YYYY-MM-DD)", False),
            ("purchase_price", "Purchase Price",             False),
            ("description",    "Description",                True),
            ("notes",          "Notes",                      True),
        ]:
            ctk.CTkLabel(self._form, text=label, font=get_font(11),
                         text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(8, 2))
            if multiline:
                w = ctk.CTkTextbox(
                    self._form, height=60,
                    fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                    text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8
                )
            else:
                w = ctk.CTkEntry(
                    self._form,
                    fg_color=COLORS["bg_input"], border_color=COLORS["border"],
                    text_color=COLORS["text_primary"], font=get_font(13),
                    corner_radius=8, height=38
                )
            w.pack(fill="x")
            self._fields[key] = w

        # ── Computer Specs section (hidden by default) ────────────────────────
        self._specs_container = ctk.CTkFrame(self._form, fg_color="transparent")
        self._specs_container.pack(fill="x", pady=(4, 0))
        # Initially hidden; shown by _on_category_change

        # Error + buttons
        self._error = ctk.CTkLabel(self, text="", font=get_font(11),
                                   text_color=COLORS["danger"])
        self._error.pack(pady=(0, 4))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color=COLORS["bg_input"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"], font=get_font(12),
            corner_radius=8, height=40,
            command=self.destroy
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="Save Item",
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            font=get_font(12, "bold"), corner_radius=8, height=40,
            command=self._save
        ).pack(side="left", expand=True, fill="x")

    # ── Computer Specs Panel ──────────────────────────────────────────────────
    def _build_specs_panel(self):
        """Build the Computer Specs section inside _specs_container."""
        for w in self._specs_container.winfo_children():
            w.destroy()
        self._spec_fields = {}

        panel = ctk.CTkFrame(self._specs_container, fg_color=COLORS["bg_surface"],
                              corner_radius=12)
        panel.pack(fill="x", pady=(8, 0))

        # Header
        hdr = ctk.CTkFrame(panel, fg_color=COLORS["primary_dim"], corner_radius=0, height=36)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="💻  Computer Specs", font=get_font(12, "bold"),
                     text_color=COLORS["primary"]).pack(side="left", padx=14)
        ctk.CTkLabel(hdr, text="(used for performance scoring)",
                     font=get_font(10), text_color=COLORS["text_muted"]).pack(side="left")

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        # CPU row
        ctk.CTkLabel(inner, text="CPU Model", font=get_font(11),
                     text_color=COLORS["text_secondary"]).pack(anchor="w", pady=(0, 2))
        self._spec_fields["cpu"] = ctk.CTkEntry(
            inner, placeholder_text="e.g. Intel Core i7-1165G7",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["cpu"].pack(fill="x")

        # Cores + GHz row
        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        ctk.CTkLabel(row2, text="CPU Cores", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row2, text="Clock Speed (GHz)", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(8, 0))

        self._spec_fields["cpu_cores"] = ctk.CTkEntry(
            row2, placeholder_text="e.g. 4",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["cpu_cores"].grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._spec_fields["cpu_ghz"] = ctk.CTkEntry(
            row2, placeholder_text="e.g. 2.8",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["cpu_ghz"].grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))

        # RAM + Storage row
        row3 = ctk.CTkFrame(inner, fg_color="transparent")
        row3.pack(fill="x", pady=(8, 0))
        row3.columnconfigure(0, weight=1)
        row3.columnconfigure(1, weight=1)
        row3.columnconfigure(2, weight=0)

        ctk.CTkLabel(row3, text="RAM (GB)", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row3, text="Storage (GB)", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkLabel(row3, text="Type", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=2, sticky="w", padx=(8, 0))

        self._spec_fields["ram_gb"] = ctk.CTkEntry(
            row3, placeholder_text="e.g. 16",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["ram_gb"].grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._spec_fields["storage_gb"] = ctk.CTkEntry(
            row3, placeholder_text="e.g. 512",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["storage_gb"].grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))

        self._storage_type_var = ctk.StringVar(value="SSD")
        self._storage_type_combo = ctk.CTkComboBox(
            row3, values=["SSD", "HDD"],
            variable=self._storage_type_var,
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            button_color=COLORS["border"], button_hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_primary"], font=get_font(11),
            corner_radius=8, height=36, width=90, state="readonly"
        )
        self._storage_type_combo.grid(row=1, column=2, padx=(8, 0), pady=(2, 0))
        CTkScrollableDropdown(
            self._storage_type_combo, values=["SSD", "HDD"],
            command=lambda v: (self._storage_type_var.set(v), self._storage_type_combo.set(v)),
            autocomplete=False, justify="left", height=90,
            fg_color=COLORS["bg_card"], button_color=COLORS["bg_surface"],
            hover_color=COLORS["bg_hover"], text_color=COLORS["text_primary"],
            frame_border_color=COLORS["border"], scrollbar_button_color=COLORS["border"],
            font=get_font(11),
        )
        self._spec_fields["storage_type"] = self._storage_type_var

        # GPU + Year row
        row4 = ctk.CTkFrame(inner, fg_color="transparent")
        row4.pack(fill="x", pady=(8, 0))
        row4.columnconfigure(0, weight=2)
        row4.columnconfigure(1, weight=1)

        ctk.CTkLabel(row4, text="GPU (display only)", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row4, text="Purchase Year", font=get_font(11),
                     text_color=COLORS["text_secondary"]).grid(row=0, column=1, sticky="w", padx=(8, 0))

        self._spec_fields["gpu"] = ctk.CTkEntry(
            row4, placeholder_text="e.g. Intel Iris Xe",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["gpu"].grid(row=1, column=0, sticky="ew", pady=(2, 0))

        self._spec_fields["purchase_year"] = ctk.CTkEntry(
            row4, placeholder_text="e.g. 2022",
            fg_color=COLORS["bg_input"], border_color=COLORS["border"],
            text_color=COLORS["text_primary"], font=get_font(12), corner_radius=8, height=36
        )
        self._spec_fields["purchase_year"].grid(row=1, column=1, sticky="ew",
                                                padx=(8, 0), pady=(2, 0))

    def _on_category_change(self, value: str):
        """Show or hide the Computer Specs panel based on category."""
        if value.lower() in COMPUTER_CATS:
            self._build_specs_panel()
            # If editing, populate existing specs
            if self._is_edit:
                self._populate_specs()
        else:
            for w in self._specs_container.winfo_children():
                w.destroy()
            self._spec_fields = {}

    def _populate_specs(self):
        """Fill spec fields from DB when editing a computer item."""
        if not self._is_edit or not self._spec_fields:
            return
        specs = self._specs_repo.get_by_item(self._item.id)
        if not specs:
            return
        mapping = {
            "cpu": specs.cpu, "cpu_cores": specs.cpu_cores,
            "cpu_ghz": specs.cpu_ghz, "ram_gb": specs.ram_gb,
            "storage_gb": specs.storage_gb, "gpu": specs.gpu,
            "purchase_year": specs.purchase_year,
        }
        for key, val in mapping.items():
            if val is not None and key in self._spec_fields:
                w = self._spec_fields[key]
                if isinstance(w, ctk.CTkEntry):
                    w.insert(0, str(val))
        if "storage_type" in self._spec_fields and specs.storage_type:
            self._storage_type_var.set(specs.storage_type)

    # ── Actions ───────────────────────────────────────────────────────────────
    def _generate_serial(self):
        from barcodes.generator import generate_serial
        serial = generate_serial()
        self._fields["serial_number"].delete(0, "end")
        self._fields["serial_number"].insert(0, serial)

    def _scan_from_form(self):
        path = filedialog.askopenfilename(
            title="Select barcode image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not path:
            return
        from barcodes.scanner import decode_barcode_from_file
        serial = decode_barcode_from_file(path)
        if serial:
            self._fields["serial_number"].delete(0, "end")
            self._fields["serial_number"].insert(0, serial)
            Toast.show(self.master, f"Barcode decoded: {serial}", "success")
        else:
            Toast.show(self.master, "Could not decode barcode.", "error")

    def _trigger_lookup(self):
        brand = self._fields["brand"].get().strip()
        model = self._fields["model"].get().strip()
        if not brand and not model:
            self._lookup_label.configure(
                text="Enter at least Brand or Model first.",
                text_color=COLORS["warning"]
            )
            return
        self._lookup_btn.configure(state="disabled", text="⏳  Searching...")
        self._lookup_label.configure(text="Looking up product info...",
                                     text_color=COLORS["info"])

        def run():
            from barcodes.lookup import lookup_by_model
            result = lookup_by_model(brand, model)
            self.after(0, lambda: self._apply_lookup(result))

        threading.Thread(target=run, daemon=True).start()

    def _apply_lookup(self, result: Optional[dict]):
        self._lookup_btn.configure(state="normal", text="✨ Auto-Fill Specs")
        if not result:
            self._lookup_label.configure(
                text="Nothing found. Please fill in manually.",
                text_color=COLORS["warning"]
            )
            return

        self._lookup_label.configure(
            text=f"✓ Info found via {result.get('source', 'online')}",
            text_color=COLORS["success"]
        )

        # Fill main fields
        for key, val in [
            ("name",        result.get("name", "")),
            ("description", result.get("description", "")),
        ]:
            if val:
                w = self._fields[key]
                if isinstance(w, ctk.CTkTextbox):
                    w.delete("1.0", "end"); w.insert("1.0", val)
                else:
                    w.delete(0, "end"); w.insert(0, val)

        # Auto-select category if hint matches
        cat_hint = result.get("category_hint")
        if cat_hint and cat_hint in self._cat_ids:
            self._cat_var.set(cat_hint)
            self._on_category_change(cat_hint)

        # Fill spec fields if computer category and specs were parsed
        specs = result.get("specs", {})
        if specs and self._spec_fields:
            for key, val in specs.items():
                if val is not None and key in self._spec_fields:
                    w = self._spec_fields[key]
                    if isinstance(w, ctk.CTkEntry):
                        w.delete(0, "end")
                        w.insert(0, str(val))
                    elif isinstance(w, ctk.StringVar):
                        w.set(str(val))

    # ── Populate (edit mode) ──────────────────────────────────────────────────
    def _populate(self):
        i = self._item
        vals = {
            "serial_number":  i.serial_number,
            "name":           i.name,
            "brand":          i.brand or "",
            "model":          i.model or "",
            "purchase_date":  i.purchase_date or "",
            "purchase_price": str(i.purchase_price) if i.purchase_price else "",
            "description":    i.description or "",
            "notes":          i.notes or "",
        }
        for key, val in vals.items():
            w = self._fields[key]
            if isinstance(w, ctk.CTkTextbox):
                w.insert("1.0", val)
            else:
                w.insert(0, val)
        if i.category_name:
            self._cat_var.set(i.category_name)
            self._on_category_change(i.category_name)
        if i.status_name:
            self._status_var.set(i.status_name)

    # ── Save ──────────────────────────────────────────────────────────────────
    def _save(self):
        def get_val(key):
            w = self._fields[key]
            if isinstance(w, ctk.CTkTextbox):
                return w.get("1.0", "end").strip()
            return w.get().strip()

        def get_spec(key):
            w = self._spec_fields.get(key)
            if w is None:
                return None
            if isinstance(w, ctk.StringVar):
                return w.get().strip()
            return w.get().strip() or None

        serial = get_val("serial_number") or None
        name   = get_val("name")

        if not name:
            self._error.configure(text="Item Name is required.")
            return

        price_str = get_val("purchase_price")
        price = None
        if price_str:
            try:
                price = float(price_str)
            except ValueError:
                self._error.configure(text="Purchase price must be a number.")
                return

        cat_name   = self._cat_var.get()
        cat_id     = self._cat_ids.get(cat_name)
        status_name= self._status_var.get()
        status_id  = self._status_ids.get(status_name)

        data = {
            "serial_number":  serial,
            "serial_source":  "manual" if not self._is_edit else self._item.serial_source,
            "name":           name,
            "brand":          get_val("brand") or None,
            "model":          get_val("model") or None,
            "category_id":    cat_id,
            "description":    get_val("description") or None,
            "purchase_date":  get_val("purchase_date") or None,
            "purchase_price": price,
            "status_id":      status_id,
            "notes":          get_val("notes") or None,
        }

        try:
            if self._is_edit:
                before = {"name": self._item.name, "serial_number": self._item.serial_number}
                result = self._repo.update(self._item.id, data)
                self._audit.log("update", "item", self._item.id,
                                before=before, after=data,
                                performed_by=self._user.get("display_name", "admin"))
                item_id = self._item.id
                Toast.show(self.master, f"'{name}' updated.", "success")
            else:
                result = self._repo.create(data)
                self._audit.log("create", "item", result.id,
                                before=None, after=data,
                                performed_by=self._user.get("display_name", "admin"))
                item_id = result.id
                Toast.show(self.master, f"'{name}' added to inventory.", "success")

            # Save computer specs if the panel is visible
            if self._spec_fields and cat_name.lower() in COMPUTER_CATS:
                spec_data = {
                    "cpu":           get_spec("cpu"),
                    "cpu_cores":     get_spec("cpu_cores"),
                    "cpu_ghz":       get_spec("cpu_ghz"),
                    "ram_gb":        get_spec("ram_gb"),
                    "storage_gb":    get_spec("storage_gb"),
                    "storage_type":  get_spec("storage_type") or "SSD",
                    "gpu":           get_spec("gpu"),
                    "purchase_year": get_spec("purchase_year"),
                }
                self._specs_repo.upsert(item_id, spec_data)

            if self._on_save:
                self._on_save()
            self.after(10, self.destroy)

        except Exception as e:
            self._error.configure(text=str(e))
