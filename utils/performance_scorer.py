"""
InventoryPro - Performance Scorer
Pure Python, fully offline scoring engine for computer items.
Score: 0–100 based on RAM, CPU, Storage Type, and Purchase Year.
"""
from typing import Optional
from data.models import ComputerSpecs


# ── Scoring Tables ────────────────────────────────────────────────────────────

def _score_ram(ram_gb: Optional[int]) -> int:
    """RAM contributes up to 30 points."""
    if not ram_gb:
        return 0
    if ram_gb >= 32:  return 30
    if ram_gb >= 16:  return 25
    if ram_gb >= 12:  return 20
    if ram_gb >= 8:   return 15
    if ram_gb >= 4:   return 8
    return 3


def _score_cpu(cores: Optional[int], ghz: Optional[float]) -> int:
    """CPU contributes up to 30 points — cores × speed normalized."""
    if not cores or not ghz:
        return 0
    raw = cores * ghz           # e.g. 4 × 2.8 = 11.2
    if raw >= 24:   return 30   # e.g. 8c × 3.0
    if raw >= 16:   return 26
    if raw >= 12:   return 22
    if raw >= 8:    return 18
    if raw >= 5:    return 13
    if raw >= 2:    return 8
    return 4


def _score_storage(storage_gb: Optional[int], storage_type: Optional[str]) -> int:
    """Storage contributes up to 25 points — type matters most."""
    if not storage_gb or not storage_type:
        return 0
    is_ssd = (storage_type or "").upper() == "SSD"
    if is_ssd:
        if storage_gb >= 1000:  return 25
        if storage_gb >= 512:   return 22
        if storage_gb >= 256:   return 18
        return 14
    else:  # HDD
        if storage_gb >= 2000:  return 10
        if storage_gb >= 1000:  return 7
        if storage_gb >= 500:   return 5
        return 3


def _score_year(purchase_year: Optional[int]) -> int:
    """Purchase year contributes up to 15 points."""
    if not purchase_year:
        return 0
    from datetime import datetime
    age = datetime.now().year - purchase_year
    if age <= 1:    return 15
    if age <= 2:    return 13
    if age <= 3:    return 11
    if age <= 4:    return 8
    if age <= 6:    return 5
    if age <= 8:    return 3
    return 1


# ── Main Scorer ───────────────────────────────────────────────────────────────

def calculate_score(specs: ComputerSpecs) -> int:
    """
    Calculate a performance score (0–100) for a computer.
    Returns 0 if specs are incomplete.
    """
    if not specs.is_complete:
        return 0

    score = (
        _score_ram(specs.ram_gb)
        + _score_cpu(specs.cpu_cores, specs.cpu_ghz)
        + _score_storage(specs.storage_gb, specs.storage_type)
        + _score_year(specs.purchase_year)
    )
    return min(100, max(0, score))


def score_all(specs_list: list) -> list:
    """
    Score a list of ComputerSpecs and return them sorted best → worst.
    Each entry: (specs, score, tier, rank)
    """
    scored = []
    for specs in specs_list:
        score = calculate_score(specs)
        specs.perf_score = score
        scored.append(specs)

    scored.sort(key=lambda s: (s.perf_score or 0), reverse=True)
    return scored
