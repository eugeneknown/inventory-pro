"""Full component validation after bug fixes."""
import sys
sys.path.insert(0, '.')
from data.database import init_db
init_db()

print('1. Theme / fonts...')
from utils.theme import COLORS, get_font
# Note: CTkFont requires a Tk root - just verify COLORS dict and function exist
assert 'primary' in COLORS
assert 'text_muted' in COLORS
assert callable(get_font)
print('   OK')

print('2. Components...')
from ui.components import DataTable, StatusBadge, Toast, SearchBar
from ui.components import FilterDropdown, ConfirmDialog, EmptyState
print('   OK')

print('3. Dashboard...')
from ui.dashboard import DashboardPage
print('   OK')

print('4. Employee pages...')
from ui.employees.employee_list import EmployeeListPage
from ui.employees.employee_detail import EmployeeDetailDialog
from ui.employees.employee_form import EmployeeFormDialog
print('   OK')

print('5. Inventory pages...')
from ui.inventory.item_list import ItemListPage
from ui.inventory.item_detail import ItemDetailDialog
from ui.inventory.item_form import ItemFormDialog
print('   OK')

print('6. Assignments...')
from ui.assignments.assignment_panel import AssignmentPanel, AssignDialog
print('   OK')

print('7. Performance page...')
from ui.performance.performance_page import PerformancePage
print('   OK')

print('8. Scoring + specs repo...')
from utils.performance_scorer import calculate_score
from data.repositories.specs_repo import SpecsRepository
from data.models import ComputerSpecs
s = ComputerSpecs(id='x', item_id='y', cpu_cores=4, cpu_ghz=2.8,
                  ram_gb=16, storage_gb=512, storage_type='SSD', purchase_year=2022)
s.perf_score = calculate_score(s)
print(f'   Score={s.perf_score} Tier={s.tier} Color={s.tier_color}  OK')

print('9. Lookup / spec parser...')
from barcodes.lookup import _extract_specs, _detect_category
specs = _extract_specs('Intel Core i7 quad-core 2.4GHz, 16GB RAM, 512GB SSD')
assert specs.get('ram_gb') == 16, f'ram_gb wrong: {specs}'
assert specs.get('storage_type') == 'SSD', f'storage_type wrong: {specs}'
print(f'   Parsed: {specs}  OK')

print('10. App window nav...')
from ui.app_window import NAV_ITEMS
assert len(NAV_ITEMS) == 7
print(f'   Nav items: {[n[0] for n in NAV_ITEMS]}  OK')

print()
print('========================================')
print('  ALL COMPONENTS VALIDATED - NO ERRORS')
print('========================================')
