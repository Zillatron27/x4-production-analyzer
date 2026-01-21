"""Extract game data from parsed X4 save XML."""

import xml.etree.ElementTree as ET
import random
import logging
from datetime import datetime
from typing import List, Optional, Callable
from pathlib import Path
from ..models.entities import (
    Station, ProductionModule, Ship, TradeResource, EmpireData
)
from ..models.ware_database import get_ware


# Setup logging
def setup_logger():
    """Setup logger to write to project logs directory."""
    log_dir = Path.home() / "x4-production-analyzer" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "x4_parser.log"

    logger = logging.getLogger("x4analyzer.parser")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    logger.handlers = []

    # File handler
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

    return logger, log_file


logger, LOG_FILE = setup_logger()


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
        logger.info("=== Starting data extraction ===")
        logger.info(f"Log file: {LOG_FILE}")

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
        logger.info(f"Save timestamp: {empire.save_timestamp}")
        logger.info(f"Player name: {empire.player_name}")

        # Build ship lookup table first
        if progress_callback:
            flavor = random.choice(EXTRACTION_FLAVOR)
            progress_callback(flavor + "...", 0)
        self._build_ship_lookup()
        logger.info(f"Ship lookup table built: {len(self.ship_lookup)} ships")

        # Extract stations
        if progress_callback:
            progress_callback("Extracting stations...", 0)
        stations = self._extract_stations(progress_callback)
        empire.stations = stations

        logger.info(f"Extraction complete: {len(stations)} stations")
        if progress_callback:
            progress_callback(f"Found {len(stations)} stations", len(stations))

        return empire

    def _extract_timestamp(self) -> str:
        """Extract save file timestamp."""
        # Look for save element with Unix timestamp
        save_elem = self.root.find(".//info/save")
        if save_elem is not None:
            timestamp_str = save_elem.get("date", "")
            if timestamp_str:
                try:
                    # Convert Unix timestamp to readable format
                    timestamp = int(timestamp_str)
                    dt = datetime.fromtimestamp(timestamp)
                    return dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, OSError):
                    pass

        # Fallback: try old format
        info = self.root.find(".//info")
        if info is not None:
            save_date = info.get("date", "")
            save_time = info.get("time", "")
            if save_date and save_time:
                return f"{save_date} {save_time}"

        return "Unknown"

    def _extract_player_name(self) -> str:
        """Extract player name."""
        # Try the player element in info first
        player = self.root.find(".//info/player")
        if player is not None:
            name = player.get("name", "")
            if name:
                return name

        # Fallback: try player element elsewhere
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

        logger.debug(f"Parsing station: {name} ({station_id})")

        # Get sector info - try multiple methods
        sector = "Unknown"

        # Method 1: Direct location element
        sector_elem = station_elem.find("./location")
        if sector_elem is not None:
            sector = sector_elem.get("sector", "Unknown")

        # Method 2: Try to get from parent or zone (if method 1 didn't work)
        if sector == "Unknown":
            # The sector might be determined by the parent component structure
            # For now, we'll try to extract it from the station's connection path
            # This is a fallback and may need refinement based on actual save structure
            pass

        # Detect station type from modules
        station_type = self._detect_station_type(station_elem)

        station = Station(
            station_id=station_id,
            name=name,
            owner=owner,
            sector=sector,
            station_type=station_type
        )

        # Extract modules
        station.modules = self._extract_modules(station_elem)
        logger.debug(f"  - {len(station.modules)} production modules")

        # Extract assigned ships
        station.assigned_ships = self._extract_assigned_ships(station_elem, station_id)
        logger.debug(f"  - {len(station.assigned_ships)} assigned ships")

        # Extract input demands (for all stations, especially wharfs/shipyards)
        station.input_demands = self._extract_station_demands(station_elem)
        if station.input_demands:
            logger.debug(f"  - {len(station.input_demands)} input demands (type: {station_type})")

        return station

    def _detect_station_type(self, station_elem: ET.Element) -> str:
        """Detect station type from module macros."""
        construction = station_elem.find(".//construction/sequence")
        if construction is None:
            return "production"

        for entry in construction.findall("entry"):
            macro = entry.get("macro", "").lower()
            # Check for ship construction facilities
            if "wharf" in macro or "shipyard" in macro:
                if "shipyard" in macro:
                    return "shipyard"
                return "wharf"
            elif "equipmentdock" in macro or "equipment" in macro:
                return "equipmentdock"
            elif "defence" in macro or "pier" in macro:
                return "defence"

        return "production"

    def _extract_station_demands(self, station_elem: ET.Element) -> dict:
        """Extract all input demands from station trade data."""
        demands = {}

        # Find buyer trades (inputs/consumption)
        production_trades = station_elem.findall(".//trade/offers/production/trade")

        for trade in production_trades:
            # Only process buyer trades (consumption)
            if trade.get("buyer") is None:
                continue

            ware_id = trade.get("ware", "")
            if not ware_id:
                continue

            # Use 'desired' amount as demand, fallback to 'amount'
            desired = int(trade.get("desired", 0))
            amount = int(trade.get("amount", 0))
            demand = desired if desired > 0 else amount

            if demand > 0:
                if ware_id not in demands:
                    demands[ware_id] = 0
                demands[ware_id] += demand

        return demands

    def _extract_modules(self, station_elem: ET.Element) -> List[ProductionModule]:
        """Extract production modules from station."""
        modules = []

        # First, extract trade data for the station
        trade_data = self._extract_trade_data(station_elem)

        # Find all production modules in construction sequence
        construction = station_elem.find(".//construction/sequence")
        if construction is not None:
            for entry in construction.findall("entry"):
                macro = entry.get("macro", "")

                # Only process production modules
                if "prod_" not in macro.lower():
                    continue

                module = self._parse_module(entry, trade_data, macro)
                if module:
                    modules.append(module)

        return modules

    def _extract_trade_data(self, station_elem: ET.Element) -> dict:
        """Extract trade data from station."""
        trade_info = {}

        # Find trade offers
        production_trades = station_elem.findall(".//trade/offers/production/trade")

        for trade in production_trades:
            ware_id = trade.get("ware", "")
            if not ware_id:
                continue

            amount = int(trade.get("amount", 0))
            desired = int(trade.get("desired", 0))
            is_seller = trade.get("seller") is not None
            is_buyer = trade.get("buyer") is not None

            if ware_id not in trade_info:
                trade_info[ware_id] = {
                    "outputs": [],
                    "inputs": []
                }

            trade_entry = {
                "amount": amount,
                "capacity": desired if desired > 0 else amount * 2  # Estimate capacity if not specified
            }

            if is_seller:
                trade_info[ware_id]["outputs"].append(trade_entry)
            elif is_buyer:
                trade_info[ware_id]["inputs"].append(trade_entry)

        return trade_info

    def _parse_module(self, entry_elem: ET.Element, trade_data: dict, macro: str) -> Optional[ProductionModule]:
        """Parse a single production module entry."""
        module_id = entry_elem.get("id", "unknown")
        index = entry_elem.get("index", "0")

        module = ProductionModule(
            module_id=f"{module_id}_{index}",
            macro=macro
        )

        # Determine output ware from macro name
        # Extract ware type from macro like "prod_gen_advancedelectronics_macro"
        ware_id = self._extract_ware_from_macro(macro)

        if ware_id:
            module.output_ware = get_ware(ware_id)

            # Get trade data for this ware
            if ware_id in trade_data:
                ware_trade = trade_data[ware_id]

                # Set output resource
                if ware_trade["outputs"]:
                    output_data = ware_trade["outputs"][0]
                    module.output = TradeResource(
                        ware=module.output_ware,
                        amount=output_data["amount"],
                        capacity=output_data["capacity"]
                    )

                # Set input resources from buyer trades
                # For inputs, we need to find what this production module needs
                # This is trickier - we'll look for buyer trades and estimate
                for input_ware_id, input_trade in trade_data.items():
                    if input_ware_id != ware_id and input_trade["inputs"]:
                        for input_data in input_trade["inputs"]:
                            input_ware = get_ware(input_ware_id)
                            input_resource = TradeResource(
                                ware=input_ware,
                                amount=input_data["amount"],
                                capacity=input_data["capacity"]
                            )
                            module.inputs.append(input_resource)

        return module

    def _extract_ware_from_macro(self, macro: str) -> str:
        """Extract ware ID from production module macro name."""
        # Macro format: prod_gen_advancedelectronics_macro or prod_arg_energycells_01_macro
        if "prod_" not in macro.lower():
            return ""

        # Remove common prefixes and suffixes
        macro = macro.lower()
        macro = macro.replace("prod_gen_", "")
        macro = macro.replace("prod_arg_", "")
        macro = macro.replace("prod_par_", "")
        macro = macro.replace("prod_tel_", "")
        macro = macro.replace("prod_", "")
        macro = macro.replace("_macro", "")
        macro = macro.replace("_01", "")
        macro = macro.replace("_02", "")
        macro = macro.replace("_03", "")

        return macro

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
