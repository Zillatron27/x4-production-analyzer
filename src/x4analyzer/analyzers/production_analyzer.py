"""Production analysis and statistics."""

from typing import Dict, List, Tuple, Optional
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

        # Supply/Demand tracking
        self.total_production_output = 0  # Sum of production capacity
        self.total_consumption_demand = 0  # Sum of consumption from all stations
        self.consuming_stations: Dict[str, int] = {}  # station_name -> demand amount
        self.producing_stations: Dict[str, int] = {}  # station_name -> module count

        # True production rates (from game data)
        self.production_rate_per_hour: float = 0.0  # Units per hour
        self.consumption_rate_per_hour: float = 0.0  # Units per hour
        self.has_rate_data: bool = False  # Whether we have actual rate data

    @property
    def capacity_percent(self) -> float:
        """Calculate overall stock vs capacity utilization (storage fill level)."""
        if self.total_capacity == 0:
            return 0.0
        return (self.total_stock / self.total_capacity) * 100

    @property
    def production_utilization(self) -> float:
        """Calculate consumption vs production utilization (supply/demand balance)."""
        if self.total_production_output == 0:
            return 0.0
        return (self.total_consumption_demand / self.total_production_output) * 100

    @property
    def supply_status(self) -> str:
        """Get supply status: Surplus, Balanced, or Shortage."""
        # Use rate-based calculation if available
        if self.has_rate_data:
            return self._rate_based_supply_status()

        # Fallback to stock-based estimation
        # If we have consumption but no production, that's a shortage
        if self.total_consumption_demand > 0 and self.total_production_output == 0:
            return "Shortage"

        # If no consumption, check if we're producing (surplus) or not tracking
        if self.total_consumption_demand == 0:
            if self.total_production_output > 0:
                return "Surplus"  # Producing but no internal demand
            return "No Demand"

        util = self.production_utilization
        if util < 80:
            return "Surplus"
        elif util <= 120:
            return "Balanced"
        else:
            return "Shortage"

    def _rate_based_supply_status(self) -> str:
        """Get supply status based on actual production rates."""
        if self.production_rate_per_hour == 0:
            if self.consumption_rate_per_hour > 0:
                return "Shortage"
            return "No Demand"

        if self.consumption_rate_per_hour == 0:
            return "Surplus"

        # Calculate ratio of consumption to production
        ratio = self.consumption_rate_per_hour / self.production_rate_per_hour
        if ratio < 0.8:
            return "Surplus"
        elif ratio <= 1.2:
            return "Balanced"
        else:
            return "Shortage"

    @property
    def rate_balance(self) -> float:
        """Get the balance between production and consumption rates (units/hour)."""
        return self.production_rate_per_hour - self.consumption_rate_per_hour

    def add_module(self, module: ProductionModule, station_name: str = "Unknown"):
        """Add a module to the stats."""
        self.module_count += 1
        self.modules.append(module)

        if module.output:
            self.total_stock += module.output.amount
            self.total_capacity += module.output.capacity
            # Estimate production output from capacity (or use stock * 2 as estimate)
            production_estimate = module.output.capacity if module.output.capacity > 0 else 10000
            self.total_production_output += production_estimate
        else:
            # Module with no trade data - estimate default production
            self.total_production_output += 10000

        # Track producing station
        if station_name not in self.producing_stations:
            self.producing_stations[station_name] = 0
        self.producing_stations[station_name] += 1

    def add_consumption(self, station_name: str, demand_amount: int):
        """Add consumption demand from a station."""
        self.total_consumption_demand += demand_amount
        if station_name not in self.consuming_stations:
            self.consuming_stations[station_name] = 0
        self.consuming_stations[station_name] += demand_amount


class ProductionAnalyzer:
    """Analyzes production data and generates statistics."""

    def __init__(self, empire: EmpireData):
        self.empire = empire
        self._production_stats: Dict[Ware, ProductionStats] = {}
        self._analyze()

    def _analyze(self):
        """Perform initial analysis of production data."""
        # First pass: Build production statistics
        for station in self.empire.stations:
            for module in station.production_modules:
                if module.output_ware:
                    if module.output_ware not in self._production_stats:
                        self._production_stats[module.output_ware] = ProductionStats(module.output_ware)

                    self._production_stats[module.output_ware].add_module(module, station.name)

        # Second pass: Track consumption demand from all stations
        self._analyze_consumption()

    def _analyze_consumption(self):
        """Analyze consumption demand across all stations."""
        from ..models.ware_database import get_ware

        for station in self.empire.stations:
            # Collect all inputs from all modules at this station
            station_inputs: Dict[str, int] = {}  # ware_id -> total demand

            # Method 1: Get inputs from production modules
            for module in station.production_modules:
                for input_res in module.inputs:
                    ware_id = input_res.ware.ware_id
                    # Use capacity as demand (desired amount)
                    demand = input_res.capacity if input_res.capacity > 0 else input_res.amount
                    if ware_id not in station_inputs:
                        station_inputs[ware_id] = 0
                    station_inputs[ware_id] += demand

            # Method 2: Get inputs from station's direct trade data
            # This captures wharf/shipyard/equipmentdock consumption
            for ware_id, demand in station.input_demands.items():
                if ware_id not in station_inputs:
                    station_inputs[ware_id] = 0
                station_inputs[ware_id] = max(station_inputs[ware_id], demand)

            # Add consumption to production stats for each input ware
            for ware_id, demand in station_inputs.items():
                ware = get_ware(ware_id)
                if ware in self._production_stats:
                    self._production_stats[ware].add_consumption(station.name, demand)
                elif station.station_type in ("wharf", "shipyard", "equipmentdock"):
                    # Create production stats for wares consumed by wharfs/shipyards
                    # even if we don't produce them (shows demand exists)
                    self._production_stats[ware] = ProductionStats(ware)
                    self._production_stats[ware].add_consumption(station.name, demand)

    def get_supply_shortages(self) -> List[ProductionStats]:
        """Get wares with supply shortages (demand exceeds production)."""
        shortages = []
        for stats in self._production_stats.values():
            if stats.supply_status == "Shortage":
                shortages.append(stats)
        return sorted(shortages, key=lambda s: s.production_utilization, reverse=True)

    def get_supply_surplus(self) -> List[ProductionStats]:
        """Get wares with surplus production."""
        surplus = []
        for stats in self._production_stats.values():
            if stats.supply_status == "Surplus":
                surplus.append(stats)
        return sorted(surplus, key=lambda s: s.production_utilization)

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
        assigned_traders = 0
        assigned_miners = 0
        assigned_cargo = 0
        assigned_ships = 0

        for station in self.empire.stations:
            assigned_traders += len(station.traders)
            assigned_miners += len(station.miners)
            assigned_cargo += station.total_cargo_capacity
            assigned_ships += len(station.assigned_ships)

        # Unassigned ships
        unassigned_ships = len(self.empire.unassigned_ships)
        unassigned_traders = len(self.empire.unassigned_traders)
        unassigned_miners = len(self.empire.unassigned_miners)
        unassigned_cargo = sum(s.cargo_capacity for s in self.empire.unassigned_ships)

        return {
            "total_ships": assigned_ships + unassigned_ships,
            "assigned_ships": assigned_ships,
            "unassigned_ships": unassigned_ships,
            "traders": assigned_traders + unassigned_traders,
            "assigned_traders": assigned_traders,
            "unassigned_traders": unassigned_traders,
            "miners": assigned_miners + unassigned_miners,
            "assigned_miners": assigned_miners,
            "unassigned_miners": unassigned_miners,
            "total_cargo_capacity": assigned_cargo + unassigned_cargo,
            "assigned_cargo_capacity": assigned_cargo,
            "unassigned_cargo_capacity": unassigned_cargo
        }

    def search_production(self, query: str) -> List[ProductionStats]:
        """Search for production by ware name."""
        query_lower = query.lower()
        results = []

        for stats in self._production_stats.values():
            if query_lower in stats.ware.name.lower() or query_lower in stats.ware.ware_id.lower():
                results.append(stats)

        return sorted(results, key=lambda s: s.module_count, reverse=True)

    def get_ship_building_stations(self) -> List[Station]:
        """Get wharfs, shipyards, and equipment docks."""
        ship_builders = []
        for station in self.empire.stations:
            if station.station_type in ("wharf", "shipyard", "equipmentdock"):
                ship_builders.append(station)
        return ship_builders

    def get_stations_by_type(self) -> Dict[str, List[Station]]:
        """Group stations by type."""
        by_type = defaultdict(list)
        for station in self.empire.stations:
            by_type[station.station_type].append(station)
        return dict(by_type)

    def load_game_data(self, wares_extractor) -> bool:
        """
        Load production rate data from game files.

        Args:
            wares_extractor: A WaresExtractor instance with loaded game data

        Returns:
            True if rate data was successfully loaded
        """
        if not wares_extractor:
            return False

        try:
            game_wares = wares_extractor.extract()
            loaded_count = 0

            for stats in self._production_stats.values():
                ware_id = stats.ware.ware_id.lower()
                game_ware = game_wares.get(ware_id)

                if game_ware and game_ware.default_method:
                    # Calculate total production rate (rate per module * module count)
                    rate_per_module = game_ware.default_method.units_per_hour
                    stats.production_rate_per_hour = rate_per_module * stats.module_count
                    stats.has_rate_data = True
                    loaded_count += 1

                    # Calculate consumption rate for this ware
                    # Sum up consumption from all modules that use this ware as input
                    self._calculate_consumption_rate(stats, game_wares)

            return loaded_count > 0

        except Exception as e:
            import logging
            logging.getLogger("x4analyzer").warning(f"Failed to load game data: {e}")
            return False

    def _calculate_consumption_rate(self, stats: ProductionStats, game_wares: dict):
        """Calculate consumption rate for a ware based on what consumes it."""
        total_consumption = 0.0

        # Find all modules that consume this ware
        for other_stats in self._production_stats.values():
            if other_stats.ware.ware_id == stats.ware.ware_id:
                continue

            # Check if this ware produces something that consumes our target ware
            other_ware_id = other_stats.ware.ware_id.lower()
            other_game_ware = game_wares.get(other_ware_id)

            if other_game_ware and other_game_ware.default_method:
                for resource in other_game_ware.default_method.resources:
                    if resource.ware_id.lower() == stats.ware.ware_id.lower():
                        # This ware consumes our target
                        consumption_per_module = other_game_ware.default_method.resource_per_hour(resource.ware_id)
                        total_consumption += consumption_per_module * other_stats.module_count
                        break

        stats.consumption_rate_per_hour = total_consumption

    @property
    def has_rate_data(self) -> bool:
        """Check if any production stats have rate data loaded."""
        return any(stats.has_rate_data for stats in self._production_stats.values())

