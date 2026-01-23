"""Data models for X4 game entities."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class WareCategory(Enum):
    """Production ware categories based on production tiers."""
    RAW = "Raw Materials"
    TIER_1 = "Tier 1 - Processed"
    TIER_2 = "Tier 2 - Components"
    TIER_3 = "Tier 3 - Advanced"
    UNKNOWN = "Unknown"


@dataclass
class Ware:
    """Represents a production ware/commodity."""
    ware_id: str
    name: str
    category: WareCategory = WareCategory.UNKNOWN

    def __hash__(self):
        return hash(self.ware_id)

    def __eq__(self, other):
        if isinstance(other, Ware):
            return self.ware_id == other.ware_id
        return False


@dataclass
class TradeResource:
    """Input or output resource for production."""
    ware: Ware
    amount: int = 0
    capacity: int = 0

    @property
    def capacity_percent(self) -> float:
        """Calculate capacity utilization percentage."""
        if self.capacity == 0:
            return 0.0
        return (self.amount / self.capacity) * 100


@dataclass
class ProductionModule:
    """Represents a production module on a station."""
    module_id: str
    macro: str
    output_ware: Optional[Ware] = None
    inputs: List[TradeResource] = field(default_factory=list)
    output: Optional[TradeResource] = None

    @property
    def is_production(self) -> bool:
        """Check if this is a production module."""
        return "prod_" in self.macro.lower()


@dataclass
class Ship:
    """Represents a ship assigned to a station."""
    ship_id: str
    name: str
    ship_class: str
    ship_type: str  # trader, miner, etc.
    cargo_capacity: int = 0
    assigned_station_id: Optional[str] = None
    cargo_tags: str = ""  # What this ship can carry: "solid", "liquid", "container"
    mining_ware: str = ""  # What ware this ship is mining (if any)
    order_type: str = ""  # Current order type: "MiningRoutine", "TradeRoutine", etc.


@dataclass
class Station:
    """Represents a player-owned station."""
    station_id: str
    name: str
    owner: str
    sector: str = "Unknown"
    modules: List[ProductionModule] = field(default_factory=list)
    assigned_ships: List[Ship] = field(default_factory=list)
    station_type: str = "production"  # production, wharf, shipyard, equipmentdock
    input_demands: Dict[str, int] = field(default_factory=dict)  # ware_id -> demand amount

    @property
    def production_modules(self) -> List[ProductionModule]:
        """Get only production modules."""
        return [m for m in self.modules if m.is_production]

    @property
    def traders(self) -> List[Ship]:
        """Get assigned trader ships."""
        return [s for s in self.assigned_ships if s.ship_type == "trader"]

    @property
    def miners(self) -> List[Ship]:
        """Get assigned miner ships."""
        return [s for s in self.assigned_ships if s.ship_type == "miner"]

    @property
    def total_cargo_capacity(self) -> int:
        """Total cargo capacity of all assigned ships."""
        return sum(s.cargo_capacity for s in self.assigned_ships)

    @property
    def unique_products(self) -> set:
        """Get unique products produced by this station."""
        products = set()
        for module in self.production_modules:
            if module.output_ware:
                products.add(module.output_ware)
        return products


@dataclass
class EmpireData:
    """Container for all parsed empire data."""
    stations: List[Station] = field(default_factory=list)
    unassigned_ships: List[Ship] = field(default_factory=list)  # Player ships not assigned to any station
    save_timestamp: str = ""
    player_name: str = "Unknown"

    @property
    def total_production_modules(self) -> int:
        """Total number of production modules across all stations."""
        return sum(len(s.production_modules) for s in self.stations)

    @property
    def all_assigned_ships(self) -> List[Ship]:
        """Get all ships assigned to stations."""
        ships = []
        for station in self.stations:
            ships.extend(station.assigned_ships)
        return ships

    @property
    def all_ships(self) -> List[Ship]:
        """Get all player ships (assigned + unassigned)."""
        return self.all_assigned_ships + self.unassigned_ships

    @property
    def unassigned_traders(self) -> List[Ship]:
        """Get unassigned trader ships."""
        return [s for s in self.unassigned_ships if s.ship_type == "trader"]

    @property
    def unassigned_miners(self) -> List[Ship]:
        """Get unassigned miner ships."""
        return [s for s in self.unassigned_ships if s.ship_type == "miner"]

    def get_production_by_ware(self) -> Dict[Ware, List[ProductionModule]]:
        """Group production modules by output ware."""
        production_map = {}
        for station in self.stations:
            for module in station.production_modules:
                if module.output_ware:
                    if module.output_ware not in production_map:
                        production_map[module.output_ware] = []
                    production_map[module.output_ware].append(module)
        return production_map
