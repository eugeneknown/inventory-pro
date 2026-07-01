"""
InventoryPro - Full feature validation test
"""
import sys
sys.path.insert(0, '.')
from data.database import init_db, get_connection
init_db()

print('1. Imports...')
from data.models import ComputerSpecs
from data.repositories.specs_repo import SpecsRepository, is_computer_category
from utils.performance_scorer import calculate_score
from barcodes.lookup import lookup_by_model, _detect_category, _extract_specs
from ui.inventory.item_form import ItemFormDialog
from ui.performance.performance_page import PerformancePage
print('   OK')

print('2. Category detection...')
assert is_computer_category('Laptop') == True
assert is_computer_category('Desktop') == True
assert is_computer_category('Monitor') == False
assert is_computer_category(None) == False
print('   OK')

print('3. Scoring engine...')
s1 = ComputerSpecs(id='x', item_id='y', cpu_cores=4, cpu_ghz=2.8,
                   ram_gb=16, storage_gb=512, storage_type='SSD', purchase_year=2022)
score1 = calculate_score(s1)
s1.perf_score = score1
assert 60 <= score1 <= 100, f'Unexpected score: {score1}'
print(f'   16GB/4c/2.8GHz/512SSD/2022 => {score1} ({s1.tier})')

s2 = ComputerSpecs(id='x', item_id='y', cpu_cores=2, cpu_ghz=1.8,
                   ram_gb=4, storage_gb=320, storage_type='HDD', purchase_year=2016)
score2 = calculate_score(s2)
s2.perf_score = score2
assert score2 < 45, f'Should be Poor: {score2}'
print(f'   4GB/2c/1.8GHz/320HDD/2016 => {score2} ({s2.tier})')

print('4. Spec text extraction...')
text = 'Core i7 quad-core 2.4GHz, 16GB RAM, 512GB SSD, Intel Iris Xe graphics'
specs = _extract_specs(text)
print(f'   Parsed: {specs}')
assert specs.get('ram_gb') == 16
assert specs.get('storage_type') == 'SSD'

print('5. Category hint detection...')
assert _detect_category('notebook laptop ultrabook') == 'Laptop'
assert _detect_category('desktop workstation tower') == 'Desktop'
assert _detect_category('laser printer') == 'Printer'
print('   OK')

print('6. DB write/read...')
from data.repositories.item_repo import ItemRepository
from barcodes.generator import generate_serial

ir = ItemRepository()
cats = ir.get_categories()
laptop_id = next(c['id'] for c in cats if c['name'] == 'Laptop')
statuses = ir.get_statuses()
avail_id = next(s['id'] for s in statuses if s['name'] == 'available')

item = ir.create({
    'serial_number': generate_serial(), 'name': 'Test Laptop Pro',
    'brand': 'Dell', 'model': 'XPS 15', 'category_id': laptop_id,
    'status_id': avail_id, 'serial_source': 'generated'
})

sr = SpecsRepository()
spec = sr.upsert(item.id, {
    'cpu': 'Intel Core i7-11800H', 'cpu_cores': 8, 'cpu_ghz': 2.3,
    'ram_gb': 16, 'storage_gb': 512, 'storage_type': 'SSD',
    'gpu': 'NVIDIA RTX 3050', 'purchase_year': 2022
})
print(f'   Saved spec: score={spec.perf_score}, tier={spec.tier}')
assert spec.perf_score is not None and spec.perf_score > 0

all_scored = sr.get_all_scored()
assert len(all_scored) >= 1
print(f'   Fleet: {len(all_scored)} computer(s) ranked')

# Cleanup
iid = item.id
conn = get_connection()
conn.execute('PRAGMA foreign_keys=OFF')
conn.execute('DELETE FROM computer_specs WHERE item_id=?', (iid,))
conn.execute('DELETE FROM items WHERE id=?', (iid,))
conn.execute('PRAGMA foreign_keys=ON')
conn.commit()
conn.close()
print('   Cleanup: OK')

print()
print('=========================================')
print('  ALL FEATURES VALIDATED — READY TO RUN')
print('=========================================')
print()
print('  Run: python main.py')
print('  Login: admin / admin123')
