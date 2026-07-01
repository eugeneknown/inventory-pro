"""
InventoryPro - Data Models
Dataclasses for all core entities.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Department:
    id: str
    name: str
    created_at: str = ""


@dataclass
class Category:
    id: str
    name: str
    created_at: str = ""


@dataclass
class Status:
    id: str
    name: str
    color_hex: str = "#94A3B8"
    is_default: bool = False
    is_system: bool = False
    created_at: str = ""

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass
class Employee:
    id: str
    employee_id: str
    full_name: str
    department_id: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str = "active"
    notes: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    sync_status: str = "pending"
    # Joined fields
    department_name: Optional[str] = None
    assigned_count: int = 0


@dataclass
class Item:
    id: str
    serial_number: str
    name: str
    serial_source: str = "manual"
    brand: Optional[str] = None
    model: Optional[str] = None
    category_id: Optional[str] = None
    description: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_price: Optional[float] = None
    status_id: Optional[str] = None
    image_path: Optional[str] = None
    notes: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    sync_status: str = "pending"
    # Joined fields
    category_name: Optional[str] = None
    status_name: Optional[str] = None
    status_color: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_employee_id: Optional[str] = None


@dataclass
class Assignment:
    id: str
    item_id: str
    employee_id: str
    assigned_by: str
    assigned_at: str = ""
    returned_at: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    sync_status: str = "pending"
    # Joined fields
    item_name: Optional[str] = None
    item_serial: Optional[str] = None
    employee_name: Optional[str] = None
    employee_dept: Optional[str] = None


@dataclass
class AuditEntry:
    id: str
    action_type: str
    entity_type: str
    entity_id: str
    machine_id: str
    performed_by: str = "system"
    before_state: Optional[str] = None
    after_state: Optional[str] = None
    timestamp: str = ""
    is_reverted: bool = False
    revertible: bool = False
    sync_status: str = "pending"


@dataclass
class User:
    id: str
    username: str
    display_name: str
    role: str = "manager"
    department_id: Optional[str] = None
    is_active: bool = True
    created_at: str = ""


@dataclass
class SyncQueueItem:
    id: str
    table_name: str
    record_id: str
    action_type: str
    payload: str
    machine_id: str
    audit_id: Optional[str] = None
    timestamp: str = ""
    sync_status: str = "pending"
    conflict_data: Optional[str] = None
    retry_count: int = 0


@dataclass
class ComputerSpecs:
    id: str
    item_id: str
    cpu: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_ghz: Optional[float] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    storage_type: str = "SSD"
    gpu: Optional[str] = None
    purchase_year: Optional[int] = None
    perf_score: Optional[int] = None
    updated_at: str = ""

    @property
    def is_complete(self) -> bool:
        """True if enough data exists to calculate a score."""
        return all([self.ram_gb, self.cpu_cores, self.cpu_ghz,
                    self.storage_gb, self.storage_type])

    @property
    def tier(self) -> str:
        if self.perf_score is None:
            return "Incomplete"
        if self.perf_score >= 85:
            return "Excellent"
        if self.perf_score >= 65:
            return "Good"
        if self.perf_score >= 45:
            return "Fair"
        return "Poor"

    @property
    def tier_color(self) -> str:
        colors = {
            "Excellent": "#22C55E",
            "Good":      "#3B82F6",
            "Fair":      "#F59E0B",
            "Poor":      "#EF4444",
            "Incomplete":"#64748B",
        }
        return colors.get(self.tier, "#64748B")
