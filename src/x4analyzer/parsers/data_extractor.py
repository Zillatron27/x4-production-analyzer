"""Extract game data from parsed X4 save XML."""

import xml.etree.ElementTree as ET
import random
from typing import List, Optional, Callable
from ..models.entities import (
    Station, ProductionModule, Ship, TradeResource, EmpireData
)
from ..models.ware_database import get_ware


# Flavor text for data extraction phases
EXTRACTION_FLAVOR = [
    "Analyzing station configurations",
    "Cataloging production modules",
    "Mapping logistics networks",
    "Computing resource flows",
    "Evaluating cargo manifests",
    "Assessing module efficiency",
]


class DataExtractor:
    """Extracts empire data from parsed save file XML."""

    def __init__(self, root: ET.Element):
        """Initialize extractor with XML root element."""
        self.root = root
        self.ship_lookup = {}  # Cache for ship lookups

    def extract_all(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> EmpireData:
        """
        Extract all relevant data from the save file.

        Args:
            progress_callback: Optional callback(message, count) for progress updates

        Returns:
            EmpireData object with all extracted information
        """
        empire = EmpireData()

        # Show some flavor text before extraction
        if progress_callback:
            flavor = random.choice(EXTRACTION_FLAVOR)
            progress_callback(flavor + "...", 0)

        # Extract metadata
        if progress_callback:
            progress_callback("Extracting metadata...", 0)
        empire.save_timestamp = self._extract_timestamp()
        empire.player_name = self._extract_player_name()

        # Build ship lookup table first
        if progress_callback:
            flavor = random.choice(EXTRACTION_FLAVOR)
            progress_callback(flavor + "...", 0)
        self._build_ship_lookup()

        # Extract stations
        if progress_callback:
            progress_callback("Extracting stations...", 0)
        stations = self._extract_stations(progress_callback)
        empire.stations = stations

        if progress_callback:
            progress_callback(f"Found {len(stations)} stations", len(stations))

        return empire

    def _extract_timestamp(self) -> str:
        """Extract save file timestamp."""
        # Look for save info in XML
        info = self.root.find(".//info")
        if info is not None:
            save_date = info.get("date", "")
            save_time = info.get("time", "")
            if save_date and save_time:
                return f"{save_date} {save_time}"
        return "Unknown"

    def _extract_player_name(self) -> str:
        """Extract player name."""
        player = self.root.find(".//player")
        if player is not None:
            return player.get("name", "Unknown")
        return "Unknown"

    def _build_ship_lookup(self):
        """Build a lookup table of all ships for quick access."""
        # Find all ships in the universe
        for ship_elem in self.root.findall(".//component[@class='ship']"):
            ship_id = ship_elem.get("code", ship_elem.get("id", ""))
            if ship_id:
                self.ship_lookup[ship_id] = ship_elem

    def _extract_stations(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> List[Station]:
        """Extract all player-owned stations."""
        stations = []

        # Find all stations owned by player
        for station_elem in self.root.findall(".//component[@class='station']"):
            owner = station_elem.get("owner", "")

            # Check if player-owned
            if owner != "player":
                continue

            station = self._parse_station(station_elem)
            stations.append(station)

            if progress_callback:
                progress_callback(f"Processing station: {station.name}", len(stations))

        return stations

    def _parse_station(self, station_elem: ET.Element) -> Station:
        """Parse a single station element."""
        station_id = station_elem.get("code", station_elem.get("id", "unknown"))
        name = station_elem.get("name", f"Station {station_id}")
        owner = station_elem.get("owner", "unknown")

        # Get sector info
        sector = "Unknown"
        sector_elem = station_elem.find("./location")
        if sector_elem is not None:
            sector = sector_elem.get("sector", "Unknown")

        station = Station(
            station_id=station_id,
            name=name,
            owner=owner,
            sector=sector
        )

        # Extract modules
        station.modules = self._extract_modules(station_elem)

        # Extract assigned ships
        station.assigned_ships = self._extract_assigned_ships(station_elem, station_id)

        return station

    def _extract_modules(self, station_elem: ET.Element) -> List[ProductionModule]:
        """Extract production modules from station."""
        modules = []

        # Find all modules/components within the station
        for module_elem in station_elem.findall(".//connection/component[@class='module']"):
            module = self._parse_module(module_elem)
            if module:
                modules.append(module)

        return modules

    def _parse_module(self, module_elem: ET.Element) -> Optional[ProductionModule]:
        """Parse a single module element."""
        module_id = module_elem.get("code", module_elem.get("id", "unknown"))
        macro = module_elem.get("macro", "")

        # Only process production modules
        if "prod_" not in macro.lower():
            return None

        module = ProductionModule(
            module_id=module_id,
            macro=macro
        )

        # Extract production info
        production_elem = module_elem.find(".//production")
        if production_elem is not None:
            # Get output ware
            ware_id = production_elem.get("wares", production_elem.get("ware", ""))
            if ware_id:
                module.output_ware = get_ware(ware_id)

        # Extract storage/trade data
        cargo_elem = module_elem.find(".//cargo")
        if cargo_elem is not None:
            # Parse input and output resources
            for ware_elem in cargo_elem.findall(".//ware"):
                ware_id = ware_elem.get("ware", "")
                amount = int(ware_elem.get("amount", 0))

                # Look for capacity in tags or attributes
                tags = ware_elem.get("tags", "")
                capacity = 0

                # Try to find storage capacity
                storage_elem = cargo_elem.find(f".//storage[@ware='{ware_id}']")
                if storage_elem is not None:
                    capacity = int(storage_elem.get("max", 0))

                ware = get_ware(ware_id)
                resource = TradeResource(ware=ware, amount=amount, capacity=capacity)

                # Determine if input or output
                if module.output_ware and ware == module.output_ware:
                    module.output = resource
                else:
                    module.inputs.append(resource)

        return module

    def _extract_assigned_ships(self, station_elem: ET.Element, station_id: str) -> List[Ship]:
        """Extract ships assigned to this station."""
        ships = []

        # Look for subordinates
        for subordinate in station_elem.findall(".//subordinates/component"):
            ship_id = subordinate.get("code", subordinate.get("id", ""))
            if ship_id and ship_id in self.ship_lookup:
                ship = self._parse_ship(self.ship_lookup[ship_id], station_id)
                if ship:
                    ships.append(ship)

        return ships

    def _parse_ship(self, ship_elem: ET.Element, assigned_station: str) -> Optional[Ship]:
        """Parse a ship element."""
        ship_id = ship_elem.get("code", ship_elem.get("id", "unknown"))
        name = ship_elem.get("name", f"Ship {ship_id}")
        ship_class = ship_elem.get("macro", "unknown")

        # Determine ship type from purpose or macro
        ship_type = "unknown"
        purpose = ship_elem.get("purpose", "").lower()

        if "trade" in purpose or "trade" in ship_class.lower():
            ship_type = "trader"
        elif "mine" in purpose or "mining" in ship_class.lower():
            ship_type = "miner"

        # Get cargo capacity
        cargo_capacity = 0
        cargo_elem = ship_elem.find(".//cargo")
        if cargo_elem is not None:
            cargo_capacity = int(cargo_elem.get("max", 0))

        return Ship(
            ship_id=ship_id,
            name=name,
            ship_class=ship_class,
            ship_type=ship_type,
            cargo_capacity=cargo_capacity,
            assigned_station_id=assigned_station
        )
