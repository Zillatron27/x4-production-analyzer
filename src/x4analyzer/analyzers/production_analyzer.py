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

        # Supply/Demand tracking (storage-based estimates)
        self.total_production_output = 0  # Sum of production capacity (estimate)
        self.total_consumption_demand = 0  # Sum of buy orders from all stations (estimate)
        self.consuming_stations: Dict[str, int] = {}  # station_name -> demand amount (storage-based)
        self.producing_stations: Dict[str, int] = {}  # station_name -> module count

        # True production rates (from game data)
        self.production_rate_per_hour: float = 0.0  # Total units/hour produced empire-wide
        self.consumption_rate_per_hour: float = 0.0  # Total units/hour consumed empire-wide
        self.has_rate_data: bool = False  # Whether we have actual rate data

        # Per-station rate data (populated when game data is loaded)
        self.station_production_rates: Dict[str, float] = {}  # station_name -> units/hour produced
        self.station_consumption_rates: Dict[str, float] = {}  # station_name -> units/hour consumed

        # Mining capacity (for raw materials)
        self.mining_ship_count: int = 0  # Number of miners assigned to stations consuming this ware
        self.mining_cargo_capacity: int = 0  # Total cargo capacity of those miners

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

        # If no rate data but also no production and no consumption, it's "No Demand"
        # This catches wares that appear in storage but aren't actively used
        if self.total_production_output == 0 and self.total_consumption_demand == 0:
            return "No Demand"

        # Fallback to stock-based estimation
        # If we have consumption but no production, check for mining capacity
        if self.total_consumption_demand > 0 and self.total_production_output == 0:
            # Check if this is a mined raw material with sufficient miners
            if self.mining_ship_count > 0:
                mining_status = self.mining_coverage_status
                if mining_status in ("Sufficient", "Marginal"):
                    return "Balanced"
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
                # No production modules - check if this is a mined raw material
                if self.mining_ship_count > 0:
                    # Use mining coverage status instead
                    mining_status = self.mining_coverage_status
                    if mining_status == "Sufficient":
                        return "Balanced"  # Miners can supply the demand
                    elif mining_status == "Marginal":
                        return "Balanced"  # Miners might be able to supply
                    else:
                        return "Shortage"  # Insufficient miners
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

    def add_mining_capacity(self, ship_count: int, cargo_capacity: int):
        """Add mining capacity from miners assigned to stations consuming this ware."""
        self.mining_ship_count += ship_count
        self.mining_cargo_capacity += cargo_capacity

    @property
    def mining_coverage_status(self) -> str:
        """
        Get mining coverage status for raw materials.

        Compares mining cargo capacity to consumption rate.
        Returns status: "Sufficient", "Marginal", "Insufficient", or "No Miners"
        """
        if self.mining_ship_count == 0:
            return "No Miners"

        if not self.has_rate_data or self.consumption_rate_per_hour == 0:
            # Can't determine coverage without consumption rate
            return f"{self.mining_ship_count} miners"

        # Compare mining capacity to consumption rate
        # Rough heuristic: if cargo capacity >= consumption/hr, miners can probably keep up
        # (depends on mining speed, distance, etc. but gives a ballpark)
        if self.mining_cargo_capacity >= self.consumption_rate_per_hour * 1.5:
            return "Sufficient"
        elif self.mining_cargo_capacity >= self.consumption_rate_per_hour:
            return "Marginal"
        else:
            return "Insufficient"

    def get_station_production_rate(self, station_name: str) -> float:
        """Get production rate for a specific station (units/hour)."""
        return self.station_production_rates.get(station_name, 0.0)

    def get_station_consumption_rate(self, station_name: str) -> float:
        """Get consumption rate for a specific station (units/hour)."""
        return self.station_consumption_rates.get(station_name, 0.0)

    def get_station_net_rate(self, station_name: str) -> float:
        """Get net production rate for a station (production - consumption)."""
        return self.get_station_production_rate(station_name) - self.get_station_consumption_rate(station_name)


class ProductionAnalyzer:
    """Analyzes production data and generates statistics."""

    def __init__(self, empire: EmpireData):
        self.empire = empire
        self._production_stats: Dict[Ware, ProductionStats] = {}
        self._analyze()

    # Define which raw materials can be mined by which cargo type
    # Solid miners: ore, silicon, nividium, rawscrap
    # Liquid/Gas miners: hydrogen, helium, methane, ice (ice can be either)
    RAW_MATERIAL_CARGO_TYPES = {
        "ore": "solid",
        "silicon": "solid",
        "nividium": "solid",
        "rawscrap": "solid",
        "hydrogen": "liquid",
        "helium": "liquid",
        "methane": "liquid",
        "ice": "liquid",  # Ice is typically collected by gas miners
    }

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

        # Third pass: Track mining capacity for raw materials
        self._analyze_mining_capacity()

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
                if ware not in self._production_stats:
                    # Create production stats for wares we consume but don't produce
                    # This includes raw materials, wares consumed by wharfs/shipyards, etc.
                    self._production_stats[ware] = ProductionStats(ware)
                self._production_stats[ware].add_consumption(station.name, demand)

    def _analyze_mining_capacity(self):
        """
        Analyze mining capacity for raw materials.

        For each raw material, count the miners assigned to stations that consume it,
        and sum up their cargo capacity.
        """
        from ..models.ware_database import get_ware
        from ..models.entities import WareCategory

        # Track which stations consume which raw materials
        raw_material_consumers: Dict[str, List[str]] = {}  # ware_id -> list of station_names

        for stats in self._production_stats.values():
            if stats.ware.category == WareCategory.RAW:
                ware_id = stats.ware.ware_id.lower()
                raw_material_consumers[ware_id] = list(stats.consuming_stations.keys())

        # For each station, check if it has miners that can supply its raw material needs
        for station in self.empire.stations:
            # Get miners at this station
            miners = station.miners

            if not miners:
                continue

            # Categorize miners by cargo type
            solid_miners = []
            liquid_miners = []

            for miner in miners:
                cargo_tags = miner.cargo_tags.lower() if miner.cargo_tags else ""
                if "solid" in cargo_tags:
                    solid_miners.append(miner)
                elif "liquid" in cargo_tags or "gas" in cargo_tags:
                    liquid_miners.append(miner)
                else:
                    # Unknown type - check macro for hints
                    macro = miner.ship_class.lower()
                    if "liquid" in macro or "gas" in macro:
                        liquid_miners.append(miner)
                    else:
                        solid_miners.append(miner)  # Default to solid

            # For each raw material this station consumes, add mining capacity
            for ware_id, consuming_stations in raw_material_consumers.items():
                if station.name not in consuming_stations:
                    continue

                # Determine which miners can supply this raw material
                cargo_type = self.RAW_MATERIAL_CARGO_TYPES.get(ware_id, "solid")
                relevant_miners = solid_miners if cargo_type == "solid" else liquid_miners

                if relevant_miners:
                    ware = get_ware(ware_id)
                    if ware in self._production_stats:
                        total_cargo = sum(m.cargo_capacity for m in relevant_miners)
                        self._production_stats[ware].add_mining_capacity(
                            len(relevant_miners), total_cargo
                        )

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

        This calculates actual production and consumption rates based on:
        - Production modules and their output rates from game data
        - Input requirements for each production module
        - Aggregated at the empire level per ware

        Args:
            wares_extractor: A WaresExtractor instance with loaded game data

        Returns:
            True if rate data was successfully loaded
        """
        if not wares_extractor:
            return False

        try:
            game_wares = wares_extractor.extract()

            # Calculate all production and consumption rates
            # This single pass handles both production output and input consumption
            self._calculate_all_consumption_rates(game_wares)

            # Count how many wares got rate data
            loaded_count = sum(1 for stats in self._production_stats.values() if stats.has_rate_data)
            return loaded_count > 0

        except Exception as e:
            import logging
            logging.getLogger("x4analyzer").warning(f"Failed to load game data: {e}")
            return False

    def _calculate_all_consumption_rates(self, game_wares: dict):
        """
        Calculate production and consumption rates for all wares.

        For each production module in the empire:
        - Calculate its output rate from game data
        - Look up its input requirements from game data
        - Track both empire-wide totals and per-station breakdowns
        """
        from ..models.ware_database import get_ware

        # Track rates per ware and per station
        # Structure: ware_id -> {total, stations: {station_name -> rate}}
        production_rates: Dict[str, Dict] = {}  # ware produced
        consumption_rates: Dict[str, Dict] = {}  # ware consumed

        # Iterate through all production modules in the empire
        for station in self.empire.stations:
            for module in station.production_modules:
                if not module.output_ware:
                    continue

                # Get production data for what this module produces
                produced_ware_id = module.output_ware.ware_id.lower()
                game_ware = game_wares.get(produced_ware_id)

                if not game_ware or not game_ware.default_method:
                    continue

                # Track production rate for output ware
                output_rate = game_ware.default_method.units_per_hour
                if produced_ware_id not in production_rates:
                    production_rates[produced_ware_id] = {"total": 0.0, "stations": {}}
                production_rates[produced_ware_id]["total"] += output_rate
                if station.name not in production_rates[produced_ware_id]["stations"]:
                    production_rates[produced_ware_id]["stations"][station.name] = 0.0
                production_rates[produced_ware_id]["stations"][station.name] += output_rate

                # Track consumption rate for each input ware
                for resource in game_ware.default_method.resources:
                    input_ware_id = resource.ware_id.lower()
                    consumption_rate = game_ware.default_method.resource_per_hour(resource.ware_id)

                    if input_ware_id not in consumption_rates:
                        consumption_rates[input_ware_id] = {"total": 0.0, "stations": {}}
                    consumption_rates[input_ware_id]["total"] += consumption_rate
                    if station.name not in consumption_rates[input_ware_id]["stations"]:
                        consumption_rates[input_ware_id]["stations"][station.name] = 0.0
                    consumption_rates[input_ware_id]["stations"][station.name] += consumption_rate

        # Apply rates to existing production stats
        # Mark all stats as having rate data - if a ware has no production or consumption
        # rates calculated, that means it's truly "No Demand" (not producing, not consuming)
        for stats in self._production_stats.values():
            ware_id = stats.ware.ware_id.lower()

            # Apply production rates
            if ware_id in production_rates:
                stats.production_rate_per_hour = production_rates[ware_id]["total"]
                stats.station_production_rates = production_rates[ware_id]["stations"]

            # Apply consumption rates
            if ware_id in consumption_rates:
                stats.consumption_rate_per_hour = consumption_rates[ware_id]["total"]
                stats.station_consumption_rates = consumption_rates[ware_id]["stations"]

            # Mark as having rate data - even if rates are 0, we know it's accurate
            # (as opposed to falling back to storage-based estimates)
            stats.has_rate_data = True

        # Create stats for wares that are consumed but not produced
        # (e.g., raw materials we buy from NPCs)
        for ware_id, rates in consumption_rates.items():
            # Check if we already have stats for this ware
            found = False
            for stats in self._production_stats.values():
                if stats.ware.ware_id.lower() == ware_id:
                    found = True
                    break

            if not found:
                # Create new stats for consumed-only ware
                ware = get_ware(ware_id)
                new_stats = ProductionStats(ware)
                new_stats.consumption_rate_per_hour = rates["total"]
                new_stats.station_consumption_rates = rates["stations"]
                new_stats.has_rate_data = True
                self._production_stats[ware] = new_stats

    @property
    def has_rate_data(self) -> bool:
        """Check if any production stats have rate data loaded."""
        return any(stats.has_rate_data for stats in self._production_stats.values())

    def get_station_rates(self, station_name: str) -> Dict[str, Dict[str, float]]:
        """
        Get all production and consumption rates for a specific station.

        Returns:
            Dict with 'production' and 'consumption' keys, each mapping
            ware_name -> rate (units/hour)
        """
        production = {}
        consumption = {}

        for stats in self._production_stats.values():
            prod_rate = stats.get_station_production_rate(station_name)
            cons_rate = stats.get_station_consumption_rate(station_name)

            if prod_rate > 0:
                production[stats.ware.name] = prod_rate
            if cons_rate > 0:
                consumption[stats.ware.name] = cons_rate

        return {
            "production": production,
            "consumption": consumption
        }

    def get_station_summary(self, station: Station) -> Dict:
        """
        Get a comprehensive rate summary for a station.

        Returns dict with:
        - produced_wares: List of {ware, rate, modules} for each produced ware
        - consumed_wares: List of {ware, rate} for each consumed ware
        - net_rates: List of {ware, net_rate} where net_rate = production - consumption
        """
        from ..models.ware_database import get_ware

        produced = []
        consumed = []
        net_rates = {}

        # Get production from this station's modules
        for module in station.production_modules:
            if not module.output_ware:
                continue

            ware_name = module.output_ware.name
            stats = self._production_stats.get(module.output_ware)
            if stats and stats.has_rate_data:
                rate = stats.get_station_production_rate(station.name)
                # Find existing entry or create new
                existing = next((p for p in produced if p["ware"] == ware_name), None)
                if existing:
                    existing["modules"] += 1
                else:
                    produced.append({
                        "ware": ware_name,
                        "ware_id": module.output_ware.ware_id,
                        "rate": rate,
                        "modules": 1
                    })

                # Track net rate
                if ware_name not in net_rates:
                    net_rates[ware_name] = {"produced": 0, "consumed": 0}
                net_rates[ware_name]["produced"] = rate

        # Get consumption at this station
        for stats in self._production_stats.values():
            cons_rate = stats.get_station_consumption_rate(station.name)
            if cons_rate > 0:
                consumed.append({
                    "ware": stats.ware.name,
                    "ware_id": stats.ware.ware_id,
                    "rate": cons_rate
                })

                # Track net rate
                if stats.ware.name not in net_rates:
                    net_rates[stats.ware.name] = {"produced": 0, "consumed": 0}
                net_rates[stats.ware.name]["consumed"] = cons_rate

        # Calculate net rates
        net_list = []
        for ware_name, rates in net_rates.items():
            net = rates["produced"] - rates["consumed"]
            net_list.append({
                "ware": ware_name,
                "net_rate": net,
                "production": rates["produced"],
                "consumption": rates["consumed"]
            })

        return {
            "produced_wares": sorted(produced, key=lambda x: x["rate"], reverse=True),
            "consumed_wares": sorted(consumed, key=lambda x: x["rate"], reverse=True),
            "net_rates": sorted(net_list, key=lambda x: x["net_rate"])
        }

