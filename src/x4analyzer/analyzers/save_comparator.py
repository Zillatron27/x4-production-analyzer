"""Compare two save files to identify changes in supply status and production."""

from dataclasses import dataclass, field
from typing import List
from enum import Enum

from ..models.entities import Ware


class ChangeType(Enum):
    """Type of change detected."""
    IMPROVED = "improved"      # Shortage -> Balanced/Surplus, or Balanced -> Surplus
    DEGRADED = "degraded"      # Surplus -> Balanced/Shortage, or Balanced -> Shortage
    NEW_PRODUCTION = "new"     # Didn't exist before, now producing
    STOPPED = "stopped"        # Was producing, now gone
    UNCHANGED = "unchanged"    # Same status


@dataclass
class WareChange:
    """Change in a single ware between two saves."""
    ware: Ware

    # Status
    old_status: str  # "Surplus", "Balanced", "Shortage", "No Demand", or "Not Produced"
    new_status: str
    change_type: ChangeType

    # Production
    old_modules: int
    new_modules: int
    module_delta: int

    # Rates (if available)
    old_production_rate: float
    new_production_rate: float
    old_consumption_rate: float
    new_consumption_rate: float

    # Balance
    old_balance: float  # production - consumption
    new_balance: float
    balance_delta: float


@dataclass
class StationChange:
    """Change in stations between saves."""
    name: str
    change_type: str  # "added", "removed", "modified"
    old_module_count: int = 0
    new_module_count: int = 0
    module_delta: int = 0


@dataclass
class SaveComparison:
    """Complete comparison between two saves."""
    old_save_timestamp: str
    new_save_timestamp: str
    old_save_path: str
    new_save_path: str

    # Summary counts
    total_wares_compared: int = 0
    improved_count: int = 0
    degraded_count: int = 0
    new_production_count: int = 0
    stopped_count: int = 0
    unchanged_count: int = 0

    # Station changes
    stations_added: int = 0
    stations_removed: int = 0
    total_modules_delta: int = 0

    # Detailed changes (only non-unchanged)
    ware_changes: List[WareChange] = field(default_factory=list)
    station_changes: List[StationChange] = field(default_factory=list)

    # Alerts - significant changes to highlight
    alerts: List[str] = field(default_factory=list)


def compare_empires(old_analyzer, new_analyzer,
                    old_timestamp: str, new_timestamp: str,
                    old_path: str, new_path: str) -> SaveComparison:
    """
    Compare two analyzed empires and identify changes.

    Args:
        old_analyzer: ProductionAnalyzer for the older save
        new_analyzer: ProductionAnalyzer for the newer save
        old_timestamp: Timestamp string of old save
        new_timestamp: Timestamp string of new save
        old_path: Path to old save file
        new_path: Path to new save file

    Returns:
        SaveComparison with all identified changes
    """
    comparison = SaveComparison(
        old_save_timestamp=old_timestamp,
        new_save_timestamp=new_timestamp,
        old_save_path=old_path,
        new_save_path=new_path
    )

    # Get all stats from both
    old_stats_map = {s.ware.ware_id: s for s in old_analyzer.get_all_production_stats()}
    new_stats_map = {s.ware.ware_id: s for s in new_analyzer.get_all_production_stats()}

    # All ware IDs from both saves
    all_ware_ids = set(old_stats_map.keys()) | set(new_stats_map.keys())
    comparison.total_wares_compared = len(all_ware_ids)

    for ware_id in all_ware_ids:
        old_stats = old_stats_map.get(ware_id)
        new_stats = new_stats_map.get(ware_id)

        change = _compare_ware_stats(ware_id, old_stats, new_stats)

        # Count by type
        if change.change_type == ChangeType.IMPROVED:
            comparison.improved_count += 1
            comparison.ware_changes.append(change)
        elif change.change_type == ChangeType.DEGRADED:
            comparison.degraded_count += 1
            comparison.ware_changes.append(change)
        elif change.change_type == ChangeType.NEW_PRODUCTION:
            comparison.new_production_count += 1
            comparison.ware_changes.append(change)
        elif change.change_type == ChangeType.STOPPED:
            comparison.stopped_count += 1
            comparison.ware_changes.append(change)
        else:
            comparison.unchanged_count += 1
            # Don't add unchanged to the list

    # Compare stations
    old_stations = {s.name: s for s in old_analyzer.empire.stations}
    new_stations = {s.name: s for s in new_analyzer.empire.stations}

    all_station_names = set(old_stations.keys()) | set(new_stations.keys())

    for name in all_station_names:
        old_station = old_stations.get(name)
        new_station = new_stations.get(name)

        if old_station and not new_station:
            comparison.stations_removed += 1
            comparison.total_modules_delta -= len(old_station.production_modules)
            comparison.station_changes.append(StationChange(
                name=name,
                change_type="removed",
                old_module_count=len(old_station.production_modules)
            ))
        elif new_station and not old_station:
            comparison.stations_added += 1
            comparison.total_modules_delta += len(new_station.production_modules)
            comparison.station_changes.append(StationChange(
                name=name,
                change_type="added",
                new_module_count=len(new_station.production_modules)
            ))
        elif old_station and new_station:
            old_count = len(old_station.production_modules)
            new_count = len(new_station.production_modules)
            delta = new_count - old_count
            if delta != 0:
                comparison.total_modules_delta += delta
                comparison.station_changes.append(StationChange(
                    name=name,
                    change_type="modified",
                    old_module_count=old_count,
                    new_module_count=new_count,
                    module_delta=delta
                ))

    # Generate alerts for significant changes
    comparison.alerts = _generate_alerts(comparison)

    # Sort changes by significance
    comparison.ware_changes.sort(key=lambda c: (
        0 if c.change_type == ChangeType.DEGRADED else
        1 if c.change_type == ChangeType.STOPPED else
        2 if c.change_type == ChangeType.IMPROVED else
        3 if c.change_type == ChangeType.NEW_PRODUCTION else 4
    ))

    return comparison


def _compare_ware_stats(ware_id: str, old_stats, new_stats) -> WareChange:
    """Compare stats for a single ware."""
    from ..models.ware_database import get_ware

    ware = get_ware(ware_id)

    # Handle missing stats
    if not old_stats:
        old_status = "Not Produced"
        old_modules = 0
        old_prod_rate = 0.0
        old_cons_rate = 0.0
    else:
        old_status = old_stats.supply_status
        old_modules = old_stats.module_count
        old_prod_rate = old_stats.production_rate_per_hour
        old_cons_rate = old_stats.consumption_rate_per_hour

    if not new_stats:
        new_status = "Not Produced"
        new_modules = 0
        new_prod_rate = 0.0
        new_cons_rate = 0.0
    else:
        new_status = new_stats.supply_status
        new_modules = new_stats.module_count
        new_prod_rate = new_stats.production_rate_per_hour
        new_cons_rate = new_stats.consumption_rate_per_hour

    # Calculate balances
    old_balance = old_prod_rate - old_cons_rate
    new_balance = new_prod_rate - new_cons_rate

    # Determine change type
    change_type = _determine_change_type(old_status, new_status, old_modules, new_modules)

    return WareChange(
        ware=ware,
        old_status=old_status,
        new_status=new_status,
        change_type=change_type,
        old_modules=old_modules,
        new_modules=new_modules,
        module_delta=new_modules - old_modules,
        old_production_rate=old_prod_rate,
        new_production_rate=new_prod_rate,
        old_consumption_rate=old_cons_rate,
        new_consumption_rate=new_cons_rate,
        old_balance=old_balance,
        new_balance=new_balance,
        balance_delta=new_balance - old_balance
    )


def _determine_change_type(old_status: str, new_status: str,
                           old_modules: int, new_modules: int) -> ChangeType:
    """Determine the type of change based on status transitions."""

    # New production
    if old_status == "Not Produced" and new_modules > 0:
        return ChangeType.NEW_PRODUCTION

    # Stopped production
    if new_status == "Not Produced" and old_modules > 0:
        return ChangeType.STOPPED

    # Same status
    if old_status == new_status:
        return ChangeType.UNCHANGED

    # Status ranking for comparison (higher = better)
    status_rank = {
        "Surplus": 3,
        "Balanced": 2,
        "No Demand": 1,  # Neutral - no consumption
        "Shortage": 0,
        "Not Produced": -1
    }

    old_rank = status_rank.get(old_status, 1)
    new_rank = status_rank.get(new_status, 1)

    if new_rank > old_rank:
        return ChangeType.IMPROVED
    elif new_rank < old_rank:
        return ChangeType.DEGRADED
    else:
        return ChangeType.UNCHANGED


def _generate_alerts(comparison: SaveComparison) -> List[str]:
    """Generate alert messages for significant changes."""
    alerts = []

    # New shortages are critical
    new_shortages = [c for c in comparison.ware_changes
                     if c.change_type == ChangeType.DEGRADED
                     and c.new_status == "Shortage"]
    if new_shortages:
        alerts.append(f"⚠️  {len(new_shortages)} ware(s) now in SHORTAGE")

    # Resolved shortages are good news
    resolved = [c for c in comparison.ware_changes
                if c.change_type == ChangeType.IMPROVED
                and c.old_status == "Shortage"]
    if resolved:
        alerts.append(f"✓ {len(resolved)} shortage(s) resolved")

    # Stations removed
    if comparison.stations_removed > 0:
        alerts.append(f"📉 {comparison.stations_removed} station(s) removed")

    # Stations added
    if comparison.stations_added > 0:
        alerts.append(f"📈 {comparison.stations_added} new station(s)")

    # Significant module changes
    if comparison.total_modules_delta > 10:
        alerts.append(f"📈 +{comparison.total_modules_delta} production modules")
    elif comparison.total_modules_delta < -10:
        alerts.append(f"📉 {comparison.total_modules_delta} production modules")

    return alerts
