# X4 Empire Production Analyzer

> **Warning**: This project is in active development and will change rapidly. Use at your own risk.

A command-line tool to analyze player empire production in X4: Foundations. Parse your save files, view production/consumption rates, identify supply imbalances, and understand your industrial empire.

## Current Status

This tool is (mostly) functional but under active development. Features may change, break, or be removed without notice.

## Features

### Production Analysis
- **Actual Production Rates** - Uses X4 game data to calculate real units/hour production and consumption
- **Supply/Demand Balance** - See net surplus or deficit for each ware across your empire
- **Per-Station Breakdown** - View what each station produces, consumes, and its net contribution
- **Categorized Display** - Production grouped by tier (Tier 3 → Tier 2 → Tier 1 → Raw Materials)

### Views
- **Capacity Planning** - Browse all wares with production/consumption rates, select any for detailed analysis
- **Station View** - Per-station production rates, consumption rates, net deficits/surpluses
- **Logistics Analysis** - Empire-wide ship assignments, cargo capacity, station types
- **Export** - CSV, JSON, or text reports with rate data

### Technical
- **Memory-efficient parsing** - Streams large save files (900MB+) without loading into memory
- **Game data integration** - Extracts production cycle times from X4 game files for accurate rate calculations
- **Cross-platform path detection** - Auto-detects save files on Windows, Linux, Steam, GOG, Flatpak

## Requirements

- Python 3.7+
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
python x4analyzer.py
```

The tool will:
1. Auto-detect your X4 save directory
2. List recent save files for selection
3. Parse the save and load game data (if X4 installation found)
4. Display the dashboard with production overview

### Menu Options

- **[C] Capacity Planning** - Browse all wares, view rates, analyze dependencies
- **[S] Station View** - Browse stations, see per-station production/consumption
- **[L] Logistics** - Empire-wide ship and cargo summary
- **[P] Search Production** - Same as Capacity Planning
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
2. **Game Data Extraction**: Reads X4's `wares.xml` from game files to get production cycle times and input requirements
3. **Rate Calculation**: Calculates actual units/hour for production and consumption based on module counts and cycle times
4. **Analysis**: Aggregates rates per-station and empire-wide to show supply/demand balance

### Rate Calculation

```
production_rate = (amount_per_cycle / cycle_time_seconds) * 3600 * module_count
consumption_rate = sum of all modules consuming this ware * their input requirements
net_balance = production_rate - consumption_rate
```

If game data isn't available (X4 installation not found), the tool falls back to storage-based estimates.

## Project Structure

```
x4-production-analyzer/
├── src/x4analyzer/
│   ├── models/           # Data models (Station, Ship, Ware, etc.)
│   ├── parsers/          # Streaming XML parser for save files
│   ├── analyzers/        # Production analysis with rate calculations
│   ├── game_data/        # X4 game file extraction (wares, catalogs)
│   ├── ui/               # Terminal UI (dashboard, views)
│   └── config.py         # Path detection and configuration
├── tests/
├── x4analyzer.py         # Entry point
└── requirements.txt
```

## Known Limitations

- Workforce bonuses not yet factored into production rates
- Wharf/Shipyard consumption is variable (depends on build orders) - shown as storage estimates
- Some DLC modules may not be recognized
- Sector information not always available from save files

## License

MIT License

## Acknowledgments

- Egosoft for X4: Foundations
- [X4FProjector](https://github.com/bno1/X4FProjector) for game file extraction patterns (Apache-2.0)
- [Rich](https://github.com/Textualize/rich) library for terminal UI
