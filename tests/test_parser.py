#!/usr/bin/env python3
"""Basic tests for the X4 analyzer."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from x4analyzer.parsers.save_parser import SaveFileParser
from x4analyzer.parsers.data_extractor import DataExtractor
from x4analyzer.analyzers.production_analyzer import ProductionAnalyzer


def test_basic_parsing():
    """Test basic save file parsing."""
    print("Testing save file parsing...")

    # Parse the test save
    parser = SaveFileParser("test_save.xml.gz")
    root = parser.parse()

    assert root is not None, "Failed to parse save file"
    print("✓ Save file parsed successfully")

    # Extract data
    extractor = DataExtractor(root)
    empire = extractor.extract_all()

    assert empire is not None, "Failed to extract empire data"
    assert len(empire.stations) > 0, "No stations found"
    print(f"✓ Found {len(empire.stations)} stations")

    assert empire.total_production_modules > 0, "No production modules found"
    print(f"✓ Found {empire.total_production_modules} production modules")

    # Analyze production
    analyzer = ProductionAnalyzer(empire)

    production_stats = analyzer.get_all_production_stats()
    assert len(production_stats) > 0, "No production stats generated"
    print(f"✓ Generated stats for {len(production_stats)} wares")

    # Test specific functionality
    by_category = analyzer.get_production_by_category()
    print(f"✓ Production grouped into {len(by_category)} categories")

    logistics = analyzer.get_logistics_summary()
    print(f"✓ Logistics summary: {logistics['total_ships']} ships")

    # Test search
    results = analyzer.search_production("hull")
    if results:
        print(f"✓ Search found {len(results)} results for 'hull'")

    print("\n✅ All tests passed!")


def test_station_details():
    """Test station detail extraction."""
    print("\nTesting station details...")

    parser = SaveFileParser("test_save.xml.gz")
    root = parser.parse()
    extractor = DataExtractor(root)
    empire = extractor.extract_all()

    for station in empire.stations:
        print(f"\nStation: {station.name}")
        print(f"  Sector: {station.sector}")
        print(f"  Modules: {len(station.production_modules)}")
        print(f"  Ships: {len(station.assigned_ships)}")
        print(f"  Traders: {len(station.traders)}")
        print(f"  Miners: {len(station.miners)}")
        print(f"  Unique products: {len(station.unique_products)}")

        for ware in station.unique_products:
            print(f"    - {ware.name}")


def test_capacity_planning():
    """Test capacity planning analysis."""
    print("\nTesting capacity planning...")

    parser = SaveFileParser("test_save.xml.gz")
    root = parser.parse()
    extractor = DataExtractor(root)
    empire = extractor.extract_all()
    analyzer = ProductionAnalyzer(empire)

    # Test dependency analysis
    deps = analyzer.analyze_dependencies("hullparts")
    if deps:
        print(f"✓ Dependency analysis for hullparts:")
        print(f"  Inputs: {len(deps.get('inputs', []))}")
        print(f"  Consumers: {len(deps.get('consumers', []))}")

        for input_stat in deps.get('inputs', []):
            print(f"    - {input_stat.ware.name}: {input_stat.module_count} modules")


if __name__ == "__main__":
    print("=" * 60)
    print("X4 PRODUCTION ANALYZER - TEST SUITE")
    print("=" * 60)
    print()

    try:
        test_basic_parsing()
        test_station_details()
        test_capacity_planning()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
