# X4 Production Analyzer - Roadmap

## Version 1.0 - Core Features ✅ COMPLETE

- Save file parsing (gzip + XML streaming)
- Extract player stations, production modules, trade data, logistics assignments
- Dashboard, capacity planning, station detail, logistics views
- Search and export (CSV/JSON/TXT)

## Version 1.1 - Polish ✅ COMPLETE

- Auto-detect save files and game installation
- Configuration persistence, recent file list
- Color-coded supply status indicators
- Progress feedback during parsing
- Ship Building view [B] with material demand analysis
- Mining coverage analysis
- Cargo capacity vs throughput comparison

## Version 2.0 - Simulation Mode 🔶 IN PROGRESS

| Feature | Status |
|---------|--------|
| Production cycle times from game files | ✅ Done |
| Actual throughput calculation (units/hr) | ✅ Done |
| Supply chain flow modeling | ✅ Done |
| "What if" expansion simulator | ❌ Planned |
| Bottleneck severity ranking | 🔶 Partial |
| Historical analysis (compare saves) | ❌ Planned |

**Requires:** Decoupled formula engine to support workforce/sun/sector modifiers without re-parsing.

## Version 2.5 - Mod Support 📋 PLANNED

| Feature | Status |
|---------|--------|
| VFS resolver (catalog priority loading) | ❌ Planned |
| XML diff patch application | ❌ Planned |
| Mod conflict detection | ❌ Planned |

**Note:** Currently reads base game data only. Mods that change production rates via XML patches are not reflected.

## Version 3.0 - Advanced Features 📋 PLANNED

- Web-based dashboard (Flask/FastAPI)
- Real-time save file monitoring
- Production graphs/charts
- Multi-save comparison
- SQLite backend for large empires
- Profit analysis integration
- UI themes

---

✅ Complete | 🔶 In Progress | ❌ Planned | 📋 Future Version
