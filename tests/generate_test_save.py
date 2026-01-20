#!/usr/bin/env python3
"""
Generate a sample X4 save file for testing purposes.
This creates a minimal but valid X4-like save structure.
"""

import gzip
from datetime import datetime


def generate_test_save(filename="test_save.xml.gz"):
    """Generate a test save file with sample production data."""

    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<savegame version="1.0">
  <info date="2026-01-20" time="14:30:15"/>

  <universe>
    <player name="Commander Smith" money="15000000"/>

    <!-- Station 1: Manufacturing Hub Alpha -->
    <component class="station" code="station_001" name="Manufacturing Hub Alpha" owner="player">
      <location sector="Argon Prime"/>
      <connection>
        <component class="module" code="mod_001" macro="module_arg_prod_hullparts_01">
          <production wares="hullparts"/>
          <cargo>
            <ware ware="hullparts" amount="12450"/>
            <storage ware="hullparts" max="20000"/>
            <ware ware="graphene" amount="2850"/>
            <storage ware="graphene" max="10000"/>
            <ware ware="refinedmetals" amount="8900"/>
            <storage ware="refinedmetals" max="15000"/>
          </cargo>
        </component>
        <component class="module" code="mod_002" macro="module_arg_prod_hullparts_01">
          <production wares="hullparts"/>
          <cargo>
            <ware ware="hullparts" amount="8320"/>
            <storage ware="hullparts" max="20000"/>
          </cargo>
        </component>
        <component class="module" code="mod_003" macro="module_arg_prod_engineparts_01">
          <production wares="engineparts"/>
          <cargo>
            <ware ware="engineparts" amount="5600"/>
            <storage ware="engineparts" max="15000"/>
            <ware ware="refinedmetals" amount="4200"/>
            <storage ware="refinedmetals" max="10000"/>
          </cargo>
        </component>
      </connection>
      <subordinates>
        <component code="ship_001"/>
        <component code="ship_002"/>
      </subordinates>
    </component>

    <!-- Station 2: Advanced Materials Facility -->
    <component class="station" code="station_002" name="Advanced Materials Facility" owner="player">
      <location sector="The Void"/>
      <connection>
        <component class="module" code="mod_004" macro="module_arg_prod_claytronics_01">
          <production wares="claytronics"/>
          <cargo>
            <ware ware="claytronics" amount="2100"/>
            <storage ware="claytronics" max="10000"/>
            <ware ware="microchips" amount="3500"/>
            <storage ware="microchips" max="8000"/>
          </cargo>
        </component>
        <component class="module" code="mod_005" macro="module_arg_prod_microchips_01">
          <production wares="microchips"/>
          <cargo>
            <ware ware="microchips" amount="5400"/>
            <storage ware="microchips" max="12000"/>
            <ware ware="siliconwafers" amount="4800"/>
            <storage ware="siliconwafers" max="10000"/>
          </cargo>
        </component>
        <component class="module" code="mod_006" macro="module_arg_prod_advancedelectronics_01">
          <production wares="advancedelectronics"/>
          <cargo>
            <ware ware="advancedelectronics" amount="3200"/>
            <storage ware="advancedelectronics" max="8000"/>
            <ware ware="microchips" amount="2100"/>
            <storage ware="microchips" max="5000"/>
          </cargo>
        </component>
      </connection>
      <subordinates>
        <component code="ship_003"/>
        <component code="ship_004"/>
        <component code="ship_005"/>
      </subordinates>
    </component>

    <!-- Station 3: Intermediate Production Complex -->
    <component class="station" code="station_003" name="Intermediate Production Complex" owner="player">
      <location sector="Heretic's End"/>
      <connection>
        <component class="module" code="mod_007" macro="module_arg_prod_graphene_01">
          <production wares="graphene"/>
          <cargo>
            <ware ware="graphene" amount="2850"/>
            <storage ware="graphene" max="10000"/>
            <ware ware="methane" amount="5600"/>
            <storage ware="methane" max="12000"/>
          </cargo>
        </component>
        <component class="module" code="mod_008" macro="module_arg_prod_refinedmetals_01">
          <production wares="refinedmetals"/>
          <cargo>
            <ware ware="refinedmetals" amount="10080"/>
            <storage ware="refinedmetals" max="15000"/>
            <ware ware="ore" amount="7200"/>
            <storage ware="ore" max="12000"/>
          </cargo>
        </component>
        <component class="module" code="mod_009" macro="module_arg_prod_siliconwafers_01">
          <production wares="siliconwafers"/>
          <cargo>
            <ware ware="siliconwafers" amount="6400"/>
            <storage ware="siliconwafers" max="10000"/>
            <ware ware="silicon" amount="4800"/>
            <storage ware="silicon" max="8000"/>
          </cargo>
        </component>
        <component class="module" code="mod_010" macro="module_arg_prod_energycells_01">
          <production wares="energycells"/>
          <cargo>
            <ware ware="energycells" amount="45000"/>
            <storage ware="energycells" max="80000"/>
          </cargo>
        </component>
      </connection>
      <subordinates>
        <component code="ship_006"/>
      </subordinates>
    </component>

    <!-- Ships -->
    <component class="ship" code="ship_001" name="Trade Runner Alpha" macro="ship_arg_m_trader_01" purpose="trade">
      <cargo max="5000"/>
    </component>
    <component class="ship" code="ship_002" name="Trade Runner Beta" macro="ship_arg_m_trader_01" purpose="trade">
      <cargo max="5000"/>
    </component>
    <component class="ship" code="ship_003" name="Ore Hauler 1" macro="ship_arg_m_miner_01" purpose="mining">
      <cargo max="8000"/>
    </component>
    <component class="ship" code="ship_004" name="Trade Vessel Gamma" macro="ship_arg_l_trader_01" purpose="trade">
      <cargo max="12000"/>
    </component>
    <component class="ship" code="ship_005" name="Ore Hauler 2" macro="ship_arg_m_miner_01" purpose="mining">
      <cargo max="8000"/>
    </component>
    <component class="ship" code="ship_006" name="Supply Runner" macro="ship_arg_s_trader_01" purpose="trade">
      <cargo max="2000"/>
    </component>

  </universe>
</savegame>
"""

    # Compress and write
    with gzip.open(filename, 'wb') as f:
        f.write(xml_content.encode('utf-8'))

    print(f"Test save file created: {filename}")
    print(f"This file contains:")
    print("  - 3 player stations")
    print("  - 10 production modules")
    print("  - 6 assigned ships (4 traders, 2 miners)")
    print("  - Multiple production chains")
    print()
    print("You can now test the analyzer with:")
    print(f"  python x4analyzer.py")


if __name__ == "__main__":
    generate_test_save()
