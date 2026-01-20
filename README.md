# X4 Empire Production Analyzer

A powerful command-line tool to analyze player empire production in X4: Foundations. Parse your save files, visualize production chains, identify bottlenecks, and optimize your industrial empire!

## Features

### Core Analysis
- **Production Overview** - See all your production grouped by category (Ship Components, Advanced Materials, Intermediate, Basic)
- **Capacity Planning** - Analyze production dependencies and identify bottlenecks for any ware
- **Station View** - Detailed breakdown of each station's production and assigned ships
- **Logistics Analysis** - Empire-wide view of trader/miner assignments and cargo capacity
- **Production Search** - Quick lookup of any ware production
- **Export Reports** - Export production data to CSV or JSON for external analysis

### Beautiful Terminal UI
- Rich, colorful terminal interface using the `rich` library
- Progress indicators for loading and parsing
- Visual capacity bars and tables
- Categorized production displays
- Quick stats and bottleneck warnings

## Installation

### Requirements
- Python 3.7+
- X4: Foundations save file

### Setup

1. Clone this repository:
```bash
git clone https://github.com/Zillatron27/x4-production-analyzer.git
cd x4-production-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the analyzer:
```bash
python x4analyzer.py
```

Or make it executable:
```bash
chmod +x x4analyzer.py
./x4analyzer.py
```

### Save File Location

The analyzer will attempt to auto-detect your X4 save file location. Common paths:
- Windows: `C:\Users\<username>\Documents\Egosoft\X4\save\`
- Linux (Steam): `~/.local/share/Steam/steamapps/compatdata/392160/pfx/drive_c/users/steamuser/Documents/Egosoft/X4/save/`

You can also manually specify the path when prompted.

### Menu Options

After loading a save file, you'll see the main dashboard with the following options:

**[1] CAPACITY PLANNING**
- Enter a ware name (e.g., "hull parts")
- See current production statistics
- View input requirements and their capacity
- Get bottleneck warnings
- Receive expansion recommendations

**[2] STATION VIEW**
- Browse all your stations
- See detailed production breakdown per station
- View assigned traders and miners
- Check cargo capacity

**[3] LOGISTICS ANALYSIS**
- Empire-wide logistics summary
- Total traders, miners, and cargo capacity
- Per-station ship assignments
- Identify stations lacking logistics support

**[4] SEARCH PRODUCTION**
- Search for any ware by name
- See all matching production
- Quick overview of capacity and stock levels

**[5] EXPORT REPORT**
- Export to CSV for spreadsheet analysis
- Export to JSON for programmatic processing
- Includes all production statistics

**[6] LOAD NEW SAVE**
- Switch to a different save file
- Useful for comparing different game states

**[Q] QUIT**
- Exit the analyzer

## Example Output

### Main Dashboard
```
╔═══════════════════════════════════════════════════════╗
║     X4 EMPIRE PRODUCTION ANALYZER v1.0                ║
╚═══════════════════════════════════════════════════════╝

Save: 2026-01-20 14:30:15
Player: Commander Smith
Stations: 12 | Production Modules: 87

PRODUCTION OVERVIEW

  Ship Components
  Ware              Modules  Stock    Capacity  Utilization
  Hull Parts        8        12,450   20,000    ████████████░░░░░░░░ 62.3%
  Engine Parts      6        8,200    15,000    ██████████░░░░░░░░░░ 54.7%
  Weapon Components 4        3,100    8,000     ███████░░░░░░░░░░░░░ 38.8%

  Advanced Materials
  Claytronics       5        2,100    10,000    ████░░░░░░░░░░░░░░░░ 21.0%
  Microchips        7        5,400    12,000    ████████░░░░░░░░░░░░ 45.0%

QUICK STATS
  Most Produced: Hull Parts (8 modules)
  Most Diverse Station: Manufacturing Complex Alpha (5 products)
  Potential Bottlenecks: 3 wares with low stock
    - Claytronics (21.0% capacity)
    - Graphene (28.5% capacity)
```

### Capacity Planning
```
CAPACITY PLANNING

Enter ware name to analyze: hull parts

Production: Hull Parts
  Current modules: 8
  Total stock: 12,450
  Total capacity: 20,000
  Utilization: 62.3%

Input Requirements:
Input Ware      Modules  Capacity
Graphene        4        28.5%
Refined Metals  6        67.2%

Bottleneck Warnings:
  - Graphene: Low capacity (28.5%)

Recommended Expansions:
  - Expand Graphene production
```

## Project Structure

```
x4-production-analyzer/
├── src/
│   └── x4analyzer/
│       ├── models/          # Data models (Station, Ship, Ware, etc.)
│       ├── parsers/         # Save file parser and data extractor
│       ├── analyzers/       # Production analysis engine
│       └── ui/              # Terminal UI components
├── tests/                   # Test files
├── x4analyzer.py            # Main executable
├── requirements.txt         # Python dependencies
└── README.md
```

## Technical Details

### Save File Format
X4 save files are gzip-compressed XML files. The analyzer:
1. Decompresses the .xml.gz file
2. Parses the XML structure
3. Extracts player-owned stations (owner="player")
4. Identifies production modules (macro contains "prod_")
5. Reads trade data (inputs/outputs, stock levels)
6. Maps assigned ships to stations

### Ware Categories
Wares are automatically categorized into:
- **Ship Components** - Hull parts, engines, weapons, shields, etc.
- **Advanced Materials** - Claytronics, advanced electronics, microchips
- **Intermediate** - Energy cells, graphene, refined metals, silicon wafers
- **Basic** - Water, ore, silicon, ice, hydrogen, etc.

## Limitations (Phase 1)

This is version 1.0 focusing on data extraction and analysis. The following features are planned for future versions:
- Production cycle time calculations
- Actual throughput modeling (units/hour)
- Supply chain flow visualization
- "What if" expansion simulator
- Auto-optimization suggestions

## Troubleshooting

**"Save file not found"**
- Verify your X4 save location
- Ensure the file is a valid .xml.gz file
- Check file permissions

**"Failed to parse save file"**
- Ensure you're using a compatible X4 version
- Try with a different save file
- Check if the file is corrupted

**Missing production modules**
- Only player-owned stations are analyzed
- Only modules with "prod_" in their macro are counted
- Some DLC modules may not be recognized

## Contributing

Contributions are welcome! Areas for improvement:
- Additional ware definitions
- Support for more module types
- UI enhancements
- Performance optimizations
- Additional export formats

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Egosoft for creating X4: Foundations
- The X4 community for game mechanics documentation
- Rich library for beautiful terminal UI

## Version History

### v1.0.0 (2026-01-20)
- Initial release
- Save file parsing
- Production analysis
- Interactive CLI dashboard
- Capacity planning
- Station and logistics views
- Export functionality
