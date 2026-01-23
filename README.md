# X4 Empire Production Analyzer

A command-line tool to analyze player empire production in X4: Foundations. Parse your save files, view production/consumption rates, identify supply imbalances, and understand your industrial empire.

## Features

### Production Analysis
- **Actual Production Rates** - Uses X4 game data to calculate real units/hour production and consumption
- **Supply/Demand Balance** - See net surplus or deficit for each ware across your empire
- **Per-Station Breakdown** - View what each station produces, consumes, and its net contribution
- **Categorized Display** - Production grouped by tier (Tier 3 → Tier 2 → Tier 1 → Raw Materials)

### Raw Materials & Mining
- **Mining Capacity Tracking** - Shows miners assigned to stations and their cargo capacity
- **Mining Coverage Status** - Indicates if mining capacity is Sufficient, Marginal, or Insufficient for consumption needs
- **Solid vs Liquid Miners** - Tracks miner types separately for ore/silicon vs hydrogen/helium

### Ship Building Facilities
- **Dedicated View** - Separate menu for wharfs, shipyards, and equipment docks
- **Material Demands** - Shows trade orders and input requirements
- **Supply Analysis** - Empire-wide surplus/deficit for materials needed by ship builders
- **Recommendations** - Suggests production modules needed to meet demand

### Logistics Analysis
- **Fleet Summary** - Total ships, traders, miners with assigned/unassigned breakdown
- **Cargo Capacity vs Throughput** - Compare trader capacity to inter-station flow requirements
- **Game-Defined Ship Types** - Uses X4's ship classifications (freighter, miner, fighter, etc.)
- **Station Assignments** - Per-station breakdown of assigned ships by type

### Views
- **[C] Capacity Planning** - Browse all wares with production/consumption rates, select any for detailed analysis
- **[S] Station View** - Per-station production rates, consumption rates, net deficits/surpluses
- **[L] Logistics Analysis** - Fleet capacity, cargo vs throughput, ship assignments
- **[B] Ship Building** - Wharfs, shipyards, material demands, supply status
- **[E] Export** - CSV, JSON, or text reports with rate data

### Technical
- **Memory-efficient parsing** - Streams large save files (900MB+) without loading into memory
- **Game data integration** - Extracts production cycle times and ship data from X4 game files
- **Cross-platform path detection** - Auto-detects save files on Windows, Linux, Steam, GOG, Flatpak
- **Secure XML parsing** - Safe handling of malformed data with XXE protection

## Requirements

- Python 3.8+
- X4: Foundations save file
- Dependencies: `lxml`, `rich`

## Installation

```bash
git clone https://github.com/Zillatron27/x4-production-analyzer.git
cd x4-production-analyzer
pip install -r requirements.txt
```

## Usage

```bash
python -m src.x4analyzer.app
```

The tool will:
1. Auto-detect your X4 save directory
2. List recent save files for selection
3. Parse the save and load game data (if X4 installation found)
4. Display the dashboard with production overview

### Menu Options

- **[C] Capacity Planning** - Browse all wares, view rates, analyze dependencies
- **[S] Station View** - Browse stations, see per-station production/consumption
- **[L] Logistics** - Fleet capacity, cargo vs throughput analysis
- **[B] Ship Building** - Wharfs, shipyards, material supply status
- **[E] Export** - Export to CSV/JSON/Text
- **[N] New Save** - Load a different save file
- **[O] Options** - Settings, refresh game data
- **[Q] Quit**

### Save File Locations

Auto-detected paths include:
- **Windows**: `Documents\Egosoft\X4\save\`
- **Linux Steam/Proton**: `~/.steam/steam/steamapps/compatdata/392160/pfx/.../Egosoft/X4/save/`
- **Linux Native**: `~/.config/EgoSoft/X4/save/`

## How It Works

1. **Save Parsing**: Streams the XML save file extracting player stations, production modules, ships, and trade data
2. **Game Data Extraction**: Reads X4's `wares.xml` and ship macros from game files to get production rates and ship specifications
3. **Rate Calculation**: Calculates actual units/hour for production and consumption based on module counts and cycle times
4. **Analysis**: Aggregates rates per-station and empire-wide to show supply/demand balance

### Rate Calculation

```
production_rate = (amount_per_cycle / cycle_time_seconds) * 3600 * module_count
consumption_rate = sum of all modules consuming this ware * their input requirements
net_balance = production_rate - consumption_rate
```

### Supply Status Thresholds

- **Surplus**: Consumption/Production ratio < 0.8
- **Balanced**: Ratio between 0.8 and 1.2
- **Shortage**: Ratio > 1.2

If game data isn't available (X4 installation not found), the tool falls back to storage-based estimates.

## Project Structure

```
x4-production-analyzer/
├── src/x4analyzer/
│   ├── models/           # Data models (Station, Ship, Ware, ShipPurpose enum)
│   ├── parsers/          # Streaming XML parser for save files
│   ├── analyzers/        # Production analysis with rate calculations
│   ├── game_data/        # X4 game file extraction (wares, ships, catalogs)
│   ├── ui/               # Terminal UI (dashboard, views)
│   └── config.py         # Path detection and configuration
├── tests/
└── requirements.txt
```

## Known Limitations

- **Mining heuristic**: Mining coverage is estimated by comparing cargo capacity to consumption rate. Actual throughput depends on mining speed, distance to asteroids, and miner AI efficiency.
- **Workforce bonuses**: Not yet factored into production rates
- **Wharf/Shipyard consumption**: Variable based on build orders - shown as current trade demand
- **Some DLC modules**: May not be recognized in ware database

## License

MIT License

## Acknowledgments

- Egosoft for X4: Foundations
- [X4FProjector](https://github.com/bno1/X4FProjector) for game file extraction patterns (Apache-2.0)
- [Rich](https://github.com/Textualize/rich) library for terminal UI
