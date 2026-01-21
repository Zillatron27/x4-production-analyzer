"""Memory-efficient streaming parser for X4 save files."""

import gzip
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any
from xml.etree.ElementTree import iterparse
from dataclasses import dataclass, field

from ..models.entities import Station, ProductionModule, Ship, TradeResource, EmpireData
from ..models.ware_database import get_ware


def setup_logger():
    """Setup logger to write to project logs directory."""
    log_dir = Path.home() / "x4-production-analyzer" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "x4_parser.log"

    logger = logging.getLogger("x4analyzer.parser")
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers to avoid duplicates
    logger.handlers = []

    # File handler
    fh = logging.FileHandler(log_file, mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

    return logger, log_file


logger, LOG_FILE = setup_logger()


@dataclass
class ParsedStation:
    """Lightweight station data holder during parsing."""
    station_id: str
    name: str
    owner: str
    sector: str = "Unknown"
    station_type: str = "production"
    modules: List[str] = field(default_factory=list)  # macro names only
    subordinate_ids: List[str] = field(default_factory=list)
    subordinate_connection_ids: List[str] = field(default_factory=list)  # Connection IDs from <connection connection="subordinates">
    trade_wares: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class ParsedShip:
    """Lightweight ship data holder during parsing."""
    ship_id: str
    name: str
    macro: str
    owner: str = ""
    purpose: str = ""
    cargo_capacity: int = 0
    commander_id: Optional[str] = None  # Station or fleet commander this ship is assigned to


class StreamingParser:
    """
    Memory-efficient streaming parser for X4 save files.

    Uses iterparse to process the XML incrementally without loading
    the entire tree into memory.
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

        # Lightweight storage during parsing
        self._stations: Dict[str, ParsedStation] = {}
        self._ships: Dict[str, ParsedShip] = {}
        self._player_name = "Unknown"
        self._save_timestamp = "Unknown"

        # State tracking
        self._current_station_id: Optional[str] = None
        self._in_player_station = False

        # Ship-station linking: maps subordinates connection ID to station ID
        self._subordinate_conn_to_station: Dict[str, str] = {}
        # Maps ship commander connected ID to ship ID (for linking)
        self._ship_commander_connected: Dict[str, str] = {}

    def parse(self, progress_callback: Optional[Callable[[str, int], None]] = None) -> EmpireData:
        """
        Parse save file using streaming to minimize memory usage.

        Args:
            progress_callback: Optional callback(message, count) for updates

        Returns:
            EmpireData with extracted information
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Save file not found: {self.file_path}")

        logger.info(f"=== Starting streaming parse ===")
        logger.info(f"File: {self.file_path}")
        logger.info(f"Size: {self.file_path.stat().st_size / 1024 / 1024:.1f} MB")

        if progress_callback:
            progress_callback("Opening save file...", 0)

        # Open file (handle gzip or plain XML)
        try:
            file_handle = gzip.open(self.file_path, 'rb')
            # Test if it's actually gzipped
            file_handle.read(1)
            file_handle.seek(0)
            logger.info("File is gzipped")
        except gzip.BadGzipFile:
            file_handle = open(self.file_path, 'rb')
            logger.info("File is plain XML")

        try:
            self._parse_stream(file_handle, progress_callback)
        finally:
            file_handle.close()

        # Build final EmpireData
        if progress_callback:
            progress_callback("Building empire data...", len(self._stations))

        empire = self._build_empire_data()

        logger.info(f"Parse complete: {len(empire.stations)} stations, {sum(len(s.assigned_ships) for s in empire.stations)} ships")

        return empire

    def _parse_stream(self, file_handle, progress_callback: Optional[Callable]):
        """Stream through XML extracting relevant data."""

        station_count = 0
        ship_count = 0
        player_ship_count = 0

        # Track element path for context
        path = []
        current_component = None
        component_stack = []
        in_ships_connection = False  # Track when inside <connection connection="ships">

        # Track current ship being parsed for commander extraction
        current_player_ship_id: Optional[str] = None
        in_commander_connection = False  # Track when inside <connection connection="commander">
        in_subordinates_connection = False  # Track when inside <connection connection="subordinates">
        current_subordinates_conn_id: Optional[str] = None

        if progress_callback:
            progress_callback("Scanning save file...", 0)

        for event, elem in iterparse(file_handle, events=('start', 'end')):
            tag = elem.tag

            if event == 'start':
                path.append(tag)

                # Track when we enter a ships connection
                if tag == 'connection' and elem.get('connection') == 'ships':
                    in_ships_connection = True

                # Track when we enter a commander connection (inside a ship)
                if tag == 'connection' and elem.get('connection') == 'commander':
                    in_commander_connection = True

                # Track when we enter a subordinates connection (inside a station)
                if tag == 'connection' and elem.get('connection') == 'subordinates':
                    in_subordinates_connection = True
                    current_subordinates_conn_id = elem.get('id', '')
                    # Record this subordinates connection ID for the current station
                    if self._in_player_station and self._current_station_id and current_subordinates_conn_id:
                        station = self._stations.get(self._current_station_id)
                        if station:
                            station.subordinate_connection_ids.append(current_subordinates_conn_id)
                            self._subordinate_conn_to_station[current_subordinates_conn_id] = self._current_station_id

                # Track nested components
                if tag == 'component':
                    comp_class = elem.get('class', '')
                    comp_owner = elem.get('owner', '')
                    comp_id = elem.get('code', elem.get('id', ''))

                    component_stack.append({
                        'class': comp_class,
                        'owner': comp_owner,
                        'id': comp_id,
                        'elem': elem
                    })

                    # Found a player station
                    if comp_class == 'station' and comp_owner == 'player':
                        self._current_station_id = comp_id
                        self._in_player_station = True
                        station = ParsedStation(
                            station_id=comp_id,
                            name=elem.get('name', f'Station {comp_id}'),
                            owner=comp_owner
                        )
                        self._stations[comp_id] = station
                        station_count += 1

                        if progress_callback and station_count % 5 == 0:
                            progress_callback(f"Found {station_count} stations...", station_count)

                    # Found a ship - X4 uses class="ship_xs", "ship_s", "ship_m", "ship_l", "ship_xl"
                    # Exclude dockingbay, dockarea, and other station modules
                    valid_ship_classes = ('ship_xs', 'ship_s', 'ship_m', 'ship_l', 'ship_xl')
                    is_ship = comp_class in valid_ship_classes

                    if is_ship:
                        ship = ParsedShip(
                            ship_id=comp_id,
                            name=elem.get('name', f'Ship {comp_id}'),
                            macro=elem.get('macro', ''),
                            owner=comp_owner,
                            purpose=elem.get('purpose', '')
                        )
                        self._ships[comp_id] = ship
                        ship_count += 1

                        # Track this ship if it's a player ship (for commander linking)
                        if comp_owner == 'player':
                            current_player_ship_id = comp_id
                            player_ship_count += 1

                        if ship_count <= 10 or ship_count % 100 == 0:
                            logger.debug(f"Found ship: {ship.name} ({comp_id}) class={comp_class} owner={comp_owner}")

                        if progress_callback and ship_count % 500 == 0:
                            progress_callback(f"Found {station_count} stations, {ship_count} ships...", station_count)

            elif event == 'end':
                # Process completed elements

                # Capture the <connected> element inside commander connection
                if tag == 'connected' and in_commander_connection and current_player_ship_id:
                    connected_id = elem.get('connection', '')
                    if connected_id:
                        # Store this for post-processing: connected_id -> ship_id
                        self._ship_commander_connected[current_player_ship_id] = connected_id
                        ship = self._ships.get(current_player_ship_id)
                        if ship:
                            ship.commander_id = connected_id
                            logger.debug(f"Ship {current_player_ship_id} commander connected to {connected_id}")

                # Track when we exit a ships connection
                if tag == 'connection':
                    conn_type = elem.get('connection', '')
                    if conn_type == 'ships':
                        in_ships_connection = False
                    elif conn_type == 'commander':
                        in_commander_connection = False
                    elif conn_type == 'subordinates':
                        in_subordinates_connection = False
                        current_subordinates_conn_id = None

                # Save metadata from info element
                if tag == 'save' and 'info' in path:
                    date = elem.get('date', '')
                    if date:
                        try:
                            from datetime import datetime
                            ts = int(date)
                            self._save_timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, OSError):
                            pass

                elif tag == 'player' and 'info' in path:
                    self._player_name = elem.get('name', 'Unknown')

                # Process station subordinates (ship assignments)
                elif tag == 'component' and len(component_stack) > 0:
                    comp_info = component_stack[-1]

                    # Check if this is a subordinate reference within a player station
                    if self._in_player_station and 'subordinates' in path:
                        sub_id = elem.get('code', elem.get('id', ''))
                        if sub_id and self._current_station_id:
                            station = self._stations.get(self._current_station_id)
                            if station and sub_id not in station.subordinate_ids:
                                station.subordinate_ids.append(sub_id)

                    component_stack.pop()

                    # Check if we're leaving the player station
                    if comp_info['class'] == 'station' and comp_info['owner'] == 'player':
                        self._in_player_station = False
                        self._current_station_id = None

                    # Check if we're leaving a player ship
                    if comp_info['class'].startswith('ship_') and comp_info['owner'] == 'player':
                        current_player_ship_id = None

                # Process production module entries
                elif tag == 'entry' and self._in_player_station:
                    macro = elem.get('macro', '')
                    if 'prod_' in macro.lower():
                        station = self._stations.get(self._current_station_id)
                        if station:
                            station.modules.append(macro)
                    # Check for station type indicators
                    elif self._current_station_id:
                        station = self._stations.get(self._current_station_id)
                        if station:
                            macro_lower = macro.lower()
                            if 'shipyard' in macro_lower:
                                station.station_type = 'shipyard'
                            elif 'wharf' in macro_lower:
                                station.station_type = 'wharf'
                            elif 'equipmentdock' in macro_lower:
                                station.station_type = 'equipmentdock'
                            elif 'defence' in macro_lower or 'pier' in macro_lower:
                                station.station_type = 'defence'

                # Process trade data
                elif tag == 'trade' and self._in_player_station:
                    ware_id = elem.get('ware', '')
                    if ware_id:
                        station = self._stations.get(self._current_station_id)
                        if station:
                            is_seller = elem.get('seller') is not None
                            is_buyer = elem.get('buyer') is not None
                            amount = int(elem.get('amount', 0))
                            desired = int(elem.get('desired', 0))

                            if ware_id not in station.trade_wares:
                                station.trade_wares[ware_id] = {'sell': [], 'buy': []}

                            trade_entry = {'amount': amount, 'desired': desired}
                            if is_seller:
                                station.trade_wares[ware_id]['sell'].append(trade_entry)
                            elif is_buyer:
                                station.trade_wares[ware_id]['buy'].append(trade_entry)

                # Process ship cargo capacity
                elif tag == 'cargo' and len(component_stack) > 0:
                    comp_info = component_stack[-1]
                    # X4 uses class="ship_s", "ship_m", "ship_l", "ship_xl"
                    if comp_info['class'].startswith('ship_') or comp_info['class'] == 'ship':
                        ship = self._ships.get(comp_info['id'])
                        if ship:
                            ship.cargo_capacity = int(elem.get('max', 0))

                # Clear element to free memory
                elem.clear()

                if path:
                    path.pop()

        logger.info(f"Streaming parse found {station_count} stations, {ship_count} ships ({player_ship_count} player ships)")
        logger.info(f"Collected {len(self._subordinate_conn_to_station)} subordinate connections from stations")
        logger.info(f"Collected {len(self._ship_commander_connected)} ship commander connections")

        # Post-processing: Link ships to stations via commander connections
        self._link_ships_to_stations()

        # Count assigned ships
        assigned_count = sum(len(s.subordinate_ids) for s in self._stations.values())
        logger.info(f"After linking: {assigned_count} ships assigned to player stations")

        if progress_callback:
            progress_callback(f"Found {station_count} stations, {ship_count} ships ({assigned_count} assigned)", station_count)

    def _link_ships_to_stations(self):
        """
        Link player ships to stations using the commander connection data.

        X4 structure:
        - Stations have <connection connection="subordinates" id="[conn_id]">
        - Ships have <connection connection="commander"><connected connection="[conn_id]"/></connection>

        When a ship's commander connected ID matches a station's subordinates connection ID,
        the ship is assigned to that station.
        """
        linked_count = 0

        for ship_id, commander_conn_id in self._ship_commander_connected.items():
            ship = self._ships.get(ship_id)
            if not ship or ship.owner != 'player':
                continue

            # Check if this commander connection points to a station's subordinates connection
            station_id = self._subordinate_conn_to_station.get(commander_conn_id)
            if station_id:
                station = self._stations.get(station_id)
                if station and ship_id not in station.subordinate_ids:
                    station.subordinate_ids.append(ship_id)
                    linked_count += 1
                    if linked_count <= 20:
                        logger.debug(f"Linked ship {ship_id} ({ship.name}) to station {station_id} ({station.name})")

        logger.info(f"Linked {linked_count} ships to stations via commander connections")

    def _build_empire_data(self) -> EmpireData:
        """Convert parsed data to EmpireData model."""
        empire = EmpireData()
        empire.player_name = self._player_name
        empire.save_timestamp = self._save_timestamp

        # Track which ships get assigned to stations
        assigned_ship_ids = set()

        for station_id, parsed in self._stations.items():
            station = Station(
                station_id=parsed.station_id,
                name=parsed.name,
                owner=parsed.owner,
                sector=parsed.sector,
                station_type=parsed.station_type
            )

            # Convert modules
            for macro in parsed.modules:
                ware_id = self._extract_ware_from_macro(macro)
                module = ProductionModule(
                    module_id=f"{station_id}_{macro}",
                    macro=macro
                )
                if ware_id:
                    module.output_ware = get_ware(ware_id)

                    # Add trade data if available
                    if ware_id in parsed.trade_wares:
                        trade = parsed.trade_wares[ware_id]
                        if trade['sell']:
                            sell_data = trade['sell'][0]
                            module.output = TradeResource(
                                ware=module.output_ware,
                                amount=sell_data['amount'],
                                capacity=sell_data['desired'] if sell_data['desired'] > 0 else sell_data['amount'] * 2
                            )

                station.modules.append(module)

            # Build input demands from buy trades
            for ware_id, trade in parsed.trade_wares.items():
                if trade['buy']:
                    total_demand = sum(t['desired'] or t['amount'] for t in trade['buy'])
                    if total_demand > 0:
                        station.input_demands[ware_id] = total_demand

            # Assign ships
            for sub_id in parsed.subordinate_ids:
                ship_data = self._ships.get(sub_id)
                if ship_data:
                    ship_type = self._determine_ship_type(ship_data)
                    ship = Ship(
                        ship_id=ship_data.ship_id,
                        name=ship_data.name,
                        ship_class=ship_data.macro,
                        ship_type=ship_type,
                        cargo_capacity=ship_data.cargo_capacity,
                        assigned_station_id=station_id
                    )
                    station.assigned_ships.append(ship)
                    assigned_ship_ids.add(sub_id)

            empire.stations.append(station)

        # Collect unassigned player ships
        for ship_id, ship_data in self._ships.items():
            if ship_data.owner == 'player' and ship_id not in assigned_ship_ids:
                ship_type = self._determine_ship_type(ship_data)
                ship = Ship(
                    ship_id=ship_data.ship_id,
                    name=ship_data.name,
                    ship_class=ship_data.macro,
                    ship_type=ship_type,
                    cargo_capacity=ship_data.cargo_capacity,
                    assigned_station_id=None
                )
                empire.unassigned_ships.append(ship)

        logger.info(f"Built empire data: {len(empire.stations)} stations, "
                   f"{len(empire.all_assigned_ships)} assigned ships, "
                   f"{len(empire.unassigned_ships)} unassigned ships")

        return empire

    def _extract_ware_from_macro(self, macro: str) -> str:
        """Extract ware ID from production module macro name."""
        if "prod_" not in macro.lower():
            return ""

        macro = macro.lower()
        for prefix in ['prod_gen_', 'prod_arg_', 'prod_par_', 'prod_tel_', 'prod_spl_', 'prod_ter_', 'prod_']:
            macro = macro.replace(prefix, '')
        for suffix in ['_macro', '_01', '_02', '_03']:
            macro = macro.replace(suffix, '')

        return macro

    def _determine_ship_type(self, ship: ParsedShip) -> str:
        """Determine ship type from purpose and macro."""
        purpose = ship.purpose.lower()
        macro = ship.macro.lower()

        # Check purpose first (most reliable)
        if 'trade' in purpose:
            return 'trader'
        elif 'mine' in purpose:
            return 'miner'
        elif 'build' in purpose or 'moveto' in purpose:
            return 'builder'

        # Check macro for ship role hints
        if 'trans' in macro or 'freighter' in macro or 'hauler' in macro:
            return 'trader'
        elif 'miner' in macro or 'mining' in macro:
            return 'miner'
        elif 'builder' in macro or 'construct' in macro:
            return 'builder'
        elif 'fighter' in macro or 'corvette' in macro or 'frigate' in macro:
            return 'combat'
        elif 'carrier' in macro or 'destroyer' in macro or 'battleship' in macro:
            return 'combat'

        return 'other'
