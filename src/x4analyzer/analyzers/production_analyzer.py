"""Production analysis and statistics."""

from typing import Dict, List, Tuple
from collections import defaultdict
from ..models.entities import (
    EmpireData, Station, ProductionModule, Ware, WareCategory, TradeResource
)


class ProductionStats:
    """Statistics for a specific ware production."""

    def __init__(self, ware: Ware):
        self.ware = ware
        self.module_count = 0
        self.total_stock = 0
        self.total_capacity = 0
        self.modules: List[ProductionModule] = []

    @property
    def capacity_percent(self) -> float:
        """Calculate overall capacity utilization."""
        if self.total_capacity == 0:
            return 0.0
        return (self.total_stock / self.total_capacity) * 100

    def add_module(self, module: ProductionModule):
        """Add a module to the stats."""
        self.module_count += 1
        self.modules.append(module)

        if module.output:
            self.total_stock += module.output.amount
            self.total_capacity += module.output.capacity


class ProductionAnalyzer:
    """Analyzes production data and generates statistics."""

    def __init__(self, empire: EmpireData):
        self.empire = empire
        self._production_stats: Dict[Ware, ProductionStats] = {}
        self._analyze()

    def _analyze(self):
        """Perform initial analysis of production data."""
        # Build production statistics
        for station in self.empire.stations:
            for module in station.production_modules:
                if module.output_ware:
                    if module.output_ware not in self._production_stats:
                        self._production_stats[module.output_ware] = ProductionStats(module.output_ware)

                    self._production_stats[module.output_ware].add_module(module)

    def get_production_by_category(self) -> Dict[WareCategory, List[ProductionStats]]:
        """Group production stats by ware category."""
        by_category = defaultdict(list)

        for stats in self._production_stats.values():
            by_category[stats.ware.category].append(stats)

        # Sort each category by module count (descending)
        for category in by_category:
            by_category[category].sort(key=lambda s: s.module_count, reverse=True)

        return dict(by_category)

    def get_all_production_stats(self) -> List[ProductionStats]:
        """Get all production stats sorted by module count."""
        return sorted(self._production_stats.values(), key=lambda s: s.module_count, reverse=True)

    def get_ware_stats(self, ware_id: str) -> ProductionStats:
        """Get statistics for a specific ware."""
        for stats in self._production_stats.values():
            if stats.ware.ware_id == ware_id or stats.ware.name.lower() == ware_id.lower():
                return stats
        return None

    def get_most_produced(self, limit: int = 5) -> List[ProductionStats]:
        """Get top N most produced wares."""
        all_stats = self.get_all_production_stats()
        return all_stats[:limit]

    def get_diverse_stations(self, min_products: int = 3) -> List[Station]:
        """Get stations that produce multiple different products."""
        diverse = []
        for station in self.empire.stations:
            if len(station.unique_products) >= min_products:
                diverse.append(station)
        return sorted(diverse, key=lambda s: len(s.unique_products), reverse=True)

    def get_potential_bottlenecks(self, stock_threshold: float = 30.0) -> List[ProductionStats]:
        """
        Identify potential bottlenecks (low stock levels).

        Args:
            stock_threshold: Percentage below which stock is considered low

        Returns:
            List of production stats with low stock
        """
        bottlenecks = []
        for stats in self._production_stats.values():
            if stats.total_capacity > 0 and stats.capacity_percent < stock_threshold:
                bottlenecks.append(stats)
        return sorted(bottlenecks, key=lambda s: s.capacity_percent)

    def analyze_dependencies(self, ware_id: str) -> Dict[str, List[ProductionStats]]:
        """
        Analyze production dependencies for a ware.

        Returns dict with 'inputs' and 'consumers' lists.
        """
        target_stats = self.get_ware_stats(ware_id)
        if not target_stats:
            return {"inputs": [], "consumers": []}

        # Get input requirements
        input_wares = set()
        for module in target_stats.modules:
            for input_res in module.inputs:
                input_wares.add(input_res.ware)

        # Find production stats for inputs
        input_stats = []
        for ware in input_wares:
            stats = self._production_stats.get(ware)
            if stats:
                input_stats.append(stats)

        # Find consumers (modules that use this ware as input)
        consumer_stats = []
        for stats in self._production_stats.values():
            for module in stats.modules:
                for input_res in module.inputs:
                    if input_res.ware == target_stats.ware:
                        consumer_stats.append(stats)
                        break

        return {
            "inputs": input_stats,
            "consumers": consumer_stats
        }

    def get_logistics_summary(self) -> Dict[str, int]:
        """Get empire-wide logistics summary."""
        total_traders = 0
        total_miners = 0
        total_cargo = 0
        total_ships = 0

        for station in self.empire.stations:
            total_traders += len(station.traders)
            total_miners += len(station.miners)
            total_cargo += station.total_cargo_capacity
            total_ships += len(station.assigned_ships)

        return {
            "total_ships": total_ships,
            "traders": total_traders,
            "miners": total_miners,
            "total_cargo_capacity": total_cargo
        }

    def search_production(self, query: str) -> List[ProductionStats]:
        """Search for production by ware name."""
        query_lower = query.lower()
        results = []

        for stats in self._production_stats.values():
            if query_lower in stats.ware.name.lower() or query_lower in stats.ware.ware_id.lower():
                results.append(stats)

        return sorted(results, key=lambda s: s.module_count, reverse=True)
