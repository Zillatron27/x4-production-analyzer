"""Extract game data from X4 save XML using memory-efficient streaming."""

import gzip
import xml.etree.ElementTree as ET
import random
from datetime import datetime
from typing import Optional, Callable
from pathlib import Path
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


class StreamingDataExtractor:
    """
    Memory-efficient streaming extractor for X4 save files.
    Uses iterparse() to process large XML files without loading entire tree into memory.
    """

    def __init__(self, file_path: str):
        """Initialize streaming extractor with save file path."""
        self.file_path = Path(file_path)
        self.save_timestamp = "Unknown"
        self.player_name = "Unknown"

    def extract_all(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> EmpireData:
        """
        Stream-parse the save file and extract all relevant data.

        Args:
            progress_callback: Optional callback(message, count) for progress updates

        Returns:
            EmpireData object with all extracted information
        """
        # Create logs directory if it doesn't exist
        from pathlib import Path
        log_dir = Path.home() / "x4-production-analyzer" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "x4_debug.log"

        # Open debug log file
        debug_log = open(log_file, 'w')
        debug_log.write("=== X4 Streaming Parser Debug Log ===\n\n")

        if progress_callback:
            flavor = random.choice(EXTRACTION_FLAVOR)
            progress_callback(flavor + "...", 0)
            progress_callback(f"DEBUG: Writing detailed log to {log_file}", 0)

        empire = EmpireData()
        stations = []

        # State tracking for nested elements
        in_station = False
        in_player_station = False
        in_construction = False
        in_sequence = False
        in_trade = False
        in_offers = False
        in_production = False
        in_subordinates = False

        current_station = None
        current_station_elem = None
        station_production_modules = []
        station_trade_data = {}
        station_traders = 0
        station_miners = 0

        elements_processed = 0
        stations_found = 0

        try:
            # Open gzipped file and create streaming parser
            with gzip.open(self.file_path, 'rb') as gz_file:
                if progress_callback:
                    progress_callback("Streaming XML data...", 0)

                context = ET.iterparse(gz_file, events=('start', 'end'))

                for event, elem in context:
                    elements_processed += 1

                    # DEBUG: Log first 2000 elements to understand structure
                    if elements_processed <= 2000:
                        tag_info = f"{elem.tag}"
                        if elem.get('class'):
                            tag_info += f" class={elem.get('class')}"
                        if elem.get('owner'):
                            tag_info += f" owner={elem.get('owner')}"
                        if elem.get('name'):
                            tag_info += f" name={elem.get('name')[:20]}"
                        if elem.get('date'):
                            tag_info += f" date={elem.get('date')}"
                        debug_log.write(f"[{event:5s}] {elements_processed:4d}: {tag_info}\n")

                        # Show progress every 100 elements
                        if elements_processed % 100 == 0 and progress_callback:
                            progress_callback(f"Logged {elements_processed} elements to debug file", 0)

                    # Progress update every 10,000 elements
                    if elements_processed % 10000 == 0 and progress_callback:
                        progress_callback(
                            f"Processing... ({stations_found} stations found)",
                            stations_found
                        )

                    # === METADATA EXTRACTION (first pass) ===
                    if event == 'end' and elem.tag == 'save' and not self.save_timestamp:
                        debug_log.write(f"\n*** SAVE TAG FOUND! date={elem.get('date', 'NONE')} ***\n")
                        timestamp_str = elem.get("date", "")
                        if timestamp_str:
                            try:
                                timestamp = int(timestamp_str)
                                dt = datetime.fromtimestamp(timestamp)
                                self.save_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                                debug_log.write(f"*** Save timestamp extracted: {self.save_timestamp} ***\n")
                                if progress_callback:
                                    progress_callback(f"Found save date: {self.save_timestamp}", 0)
                            except (ValueError, OSError) as e:
                                debug_log.write(f"*** Error parsing timestamp: {e} ***\n")
                        elem.clear()

                    elif event == 'end' and elem.tag == 'player' and not self.player_name:
                        debug_log.write(f"\n*** PLAYER TAG FOUND! name={elem.get('name', 'NONE')} ***\n")
                        self.player_name = elem.get("name", "Unknown")
                        debug_log.write(f"*** Player name extracted: {self.player_name} ***\n")
                        if progress_callback:
                            progress_callback(f"Found player: {self.player_name}", 0)
                        elem.clear()

                    # === STATION DETECTION ===
                    elif event == 'start' and elem.tag == 'component':
                        if elem.get('class') == 'station':
                            in_station = True
                            if elem.get('owner') == 'player':
                                in_player_station = True
                                current_station_elem = {
                                    'code': elem.get('code', 'unknown'),
                                    'name': elem.get('name', f"Station {elem.get('code', 'unknown')}"),
                                    'sector': 'Unknown'
                                }
                                station_production_modules = []
                                station_trade_data = {}
                                station_traders = 0
                                station_miners = 0
                                if stations_found < 2:
                                    debug_log.write(f"\n*** PLAYER STATION FOUND: {current_station_elem['name']} ***\n")
                                if progress_callback and stations_found < 2:
                                    progress_callback(f"DEBUG: Entering station {current_station_elem['name']}", stations_found)

                    # === NESTED TAG TRACKING ===
                    elif event == 'start' and in_player_station:
                        if elem.tag == 'construction':
                            in_construction = True
                            if stations_found < 2:
                                debug_log.write(f"  -> Entered construction section\n")
                            if progress_callback and stations_found < 2:
                                progress_callback(f"DEBUG: Entered construction section", stations_found)
                        elif elem.tag == 'sequence' and in_construction:
                            in_sequence = True
                            if stations_found < 2:
                                debug_log.write(f"  -> Entered sequence section\n")
                            if progress_callback and stations_found < 2:
                                progress_callback(f"DEBUG: Entered sequence section", stations_found)
                        elif elem.tag == 'trade':
                            in_trade = True
                            if stations_found < 2:
                                debug_log.write(f"  -> Entered trade section\n")
                            if progress_callback and stations_found < 2:
                                progress_callback(f"DEBUG: Entered trade section", stations_found)
                        elif elem.tag == 'offers' and in_trade:
                            in_offers = True
                            if stations_found < 2:
                                debug_log.write(f"  -> Entered offers section\n")
                            if progress_callback and stations_found < 2:
                                progress_callback(f"DEBUG: Entered offers section", stations_found)
                        elif elem.tag == 'production' and in_offers:
                            in_production = True
                            if stations_found < 2:
                                debug_log.write(f"  -> Entered production section\n")
                            if progress_callback and stations_found < 2:
                                progress_callback(f"DEBUG: Entered production section", stations_found)
                        elif elem.tag == 'subordinates':
                            in_subordinates = True
                            if stations_found < 2:
                                debug_log.write(f"  -> Entered subordinates section\n")
                            if progress_callback and stations_found < 2:
                                progress_callback(f"DEBUG: Entered subordinates section", stations_found)

                    # === DATA EXTRACTION ===
                    elif event == 'end' and in_player_station:

                        # Production modules in construction sequence
                        if elem.tag == 'entry' and in_sequence:
                            macro = elem.get('macro', '')
                            if stations_found < 2:
                                debug_log.write(f"  Entry in sequence: macro={macro}\n")
                            if 'prod_' in macro.lower():
                                ware_id = self._extract_ware_from_macro(macro)
                                if ware_id:
                                    station_production_modules.append({
                                        'macro': macro,
                                        'ware_id': ware_id,
                                        'index': elem.get('index', '0')
                                    })
                                    if len(station_production_modules) == 1:
                                        debug_log.write(f"*** PRODUCTION MODULE FOUND: {ware_id} ***\n")
                                    if progress_callback and len(station_production_modules) == 1:
                                        progress_callback(f"Found production module: {ware_id}", stations_found)
                            elem.clear()

                        # Trade data (inputs/outputs)
                        elif elem.tag == 'trade' and in_production:
                            ware_id = elem.get('ware', '')
                            if ware_id:
                                is_seller = elem.get('seller') is not None
                                is_buyer = elem.get('buyer') is not None
                                amount = int(elem.get('amount', 0))
                                desired = int(elem.get('desired', 0))

                                if ware_id not in station_trade_data:
                                    station_trade_data[ware_id] = {
                                        'output_amount': 0,
                                        'output_capacity': 0,
                                        'input_amount': 0,
                                        'input_capacity': 0
                                    }

                                if is_seller:
                                    station_trade_data[ware_id]['output_amount'] = amount
                                    station_trade_data[ware_id]['output_capacity'] = desired if desired > 0 else amount * 2
                                elif is_buyer:
                                    station_trade_data[ware_id]['input_amount'] = amount
                                    station_trade_data[ware_id]['input_capacity'] = desired
                            elem.clear()

                        # Subordinates (traders/miners)
                        elif elem.tag == 'group' and in_subordinates:
                            assignment = elem.get('assignment', '')
                            if assignment == 'trade':
                                station_traders += 1
                            elif assignment == 'mine':
                                station_miners += 1
                            elem.clear()

                        # End of nested sections
                        elif elem.tag == 'sequence':
                            in_sequence = False
                            elem.clear()
                        elif elem.tag == 'construction':
                            in_construction = False
                            elem.clear()
                        elif elem.tag == 'production':
                            in_production = False
                            elem.clear()
                        elif elem.tag == 'offers':
                            in_offers = False
                            elem.clear()
                        elif elem.tag == 'trade' and not in_production:
                            in_trade = False
                            elem.clear()
                        elif elem.tag == 'subordinates':
                            in_subordinates = False
                            elem.clear()

                    # === STATION COMPLETION ===
                    elif event == 'end' and elem.tag == 'component' and elem.get('class') == 'station':
                        if in_player_station and current_station_elem:
                            # Build Station object
                            station = self._build_station(
                                current_station_elem,
                                station_production_modules,
                                station_trade_data,
                                station_traders,
                                station_miners
                            )
                            stations.append(station)
                            stations_found += 1

                            if progress_callback:
                                progress_callback(
                                    f"Found station: {station.name}",
                                    stations_found
                                )

                        # Reset state
                        in_station = False
                        in_player_station = False
                        current_station_elem = None
                        elem.clear()

                    # Clear other elements to free memory
                    elif event == 'end':
                        elem.clear()

        except Exception as e:
            debug_log.write(f"\n*** ERROR: {e} ***\n")
            debug_log.close()
            if progress_callback:
                progress_callback(f"Error during parsing: {e}", stations_found)
            raise

        # Build empire data
        empire.save_timestamp = self.save_timestamp
        empire.player_name = self.player_name
        empire.stations = stations

        debug_log.write(f"\n=== EXTRACTION SUMMARY ===\n")
        debug_log.write(f"Save timestamp: {self.save_timestamp}\n")
        debug_log.write(f"Player name: {self.player_name}\n")
        debug_log.write(f"Stations found: {len(stations)}\n")
        debug_log.write(f"Total elements processed: {elements_processed}\n")
        debug_log.close()

        if progress_callback:
            progress_callback(f"Extraction complete! Found {len(stations)} stations", len(stations))
            progress_callback(f"Debug log saved to: {log_file}", len(stations))

        return empire

    def _extract_ware_from_macro(self, macro: str) -> str:
        """Extract ware ID from production module macro name."""
        if "prod_" not in macro.lower():
            return ""

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

        return macro.strip()

    def _build_station(self, station_elem: dict, prod_modules: list,
                      trade_data: dict, traders: int, miners: int) -> Station:
        """Build a Station object from extracted data."""
        station = Station(
            station_id=station_elem['code'],
            name=station_elem['name'],
            owner='player',
            sector=station_elem.get('sector', 'Unknown')
        )

        # Build production modules
        for module_data in prod_modules:
            ware_id = module_data['ware_id']
            ware = get_ware(ware_id)

            module = ProductionModule(
                module_id=f"{module_data.get('index', '0')}",
                macro=module_data['macro'],
                output_ware=ware
            )

            # Add trade data if available
            if ware_id in trade_data:
                trade = trade_data[ware_id]
                if trade['output_amount'] > 0 or trade['output_capacity'] > 0:
                    module.output = TradeResource(
                        ware=ware,
                        amount=trade['output_amount'],
                        capacity=trade['output_capacity']
                    )

                # Add inputs (all buyer trades at station level)
                for input_ware_id, input_trade in trade_data.items():
                    if input_ware_id != ware_id and input_trade['input_capacity'] > 0:
                        input_ware = get_ware(input_ware_id)
                        module.inputs.append(TradeResource(
                            ware=input_ware,
                            amount=input_trade['input_amount'],
                            capacity=input_trade['input_capacity']
                        ))

            station.modules.append(module)

        # Add ship placeholders (we're not fully parsing ships in streaming mode yet)
        # This is a simplified version - full ship parsing would require second pass
        for i in range(traders):
            ship = Ship(
                ship_id=f"trader_{i}",
                name=f"Trader {i+1}",
                ship_class="trader",
                ship_type="trader",
                cargo_capacity=5000,
                assigned_station_id=station.station_id
            )
            station.assigned_ships.append(ship)

        for i in range(miners):
            ship = Ship(
                ship_id=f"miner_{i}",
                name=f"Miner {i+1}",
                ship_class="miner",
                ship_type="miner",
                cargo_capacity=8000,
                assigned_station_id=station.station_id
            )
            station.assigned_ships.append(ship)

        return station
