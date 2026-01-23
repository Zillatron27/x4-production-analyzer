"""Database of X4 wares and their categories based on production tiers."""

from .entities import Ware, WareCategory

# Comprehensive ware database with tier-based categorization
# Based on X4 production chain: Raw -> Tier 1 -> Tier 2 -> Tier 3
WARE_DATABASE = {
    # RAW MATERIALS (Tier 0) - Mined/collected resources
    "helium": Ware("helium", "Helium", WareCategory.RAW),
    "hydrogen": Ware("hydrogen", "Hydrogen", WareCategory.RAW),
    "ice": Ware("ice", "Ice", WareCategory.RAW),
    "methane": Ware("methane", "Methane", WareCategory.RAW),
    "ore": Ware("ore", "Ore", WareCategory.RAW),
    "rawscrap": Ware("rawscrap", "Raw Scrap", WareCategory.RAW),
    "silicon": Ware("silicon", "Silicon", WareCategory.RAW),
    "nividium": Ware("nividium", "Nividium", WareCategory.RAW),

    # TIER 1 - Basic processed materials
    "antimattercells": Ware("antimattercells", "Antimatter Cells", WareCategory.TIER_1),
    "computronicsubstrate": Ware("computronicsubstrate", "Computronic Substrate", WareCategory.TIER_1),
    "energycells": Ware("energycells", "Energy Cells", WareCategory.TIER_1),
    "graphene": Ware("graphene", "Graphene", WareCategory.TIER_1),
    "metallicmicrolattice": Ware("metallicmicrolattice", "Metallic Microlattice", WareCategory.TIER_1),
    "proteinpaste": Ware("proteinpaste", "Protein Paste", WareCategory.TIER_1),
    "refinedmetals": Ware("refinedmetals", "Refined Metals", WareCategory.TIER_1),
    "scrapmetal": Ware("scrapmetal", "Scrap Metal", WareCategory.TIER_1),
    "siliconwafers": Ware("siliconwafers", "Silicon Wafers", WareCategory.TIER_1),
    "stimulants": Ware("stimulants", "Stimulants", WareCategory.TIER_1),
    "superfluidcoolant": Ware("superfluidcoolant", "Superfluid Coolant", WareCategory.TIER_1),
    "teladianium": Ware("teladianium", "Teladianium", WareCategory.TIER_1),
    "water": Ware("water", "Water", WareCategory.TIER_1),

    # TIER 2 - Components and intermediate goods
    "advancedcomposites": Ware("advancedcomposites", "Advanced Composites", WareCategory.TIER_2),
    "bogas": Ware("bogas", "BoGas", WareCategory.TIER_2),
    "cheltmeat": Ware("cheltmeat", "Chelt Meat", WareCategory.TIER_2),
    "engineparts": Ware("engineparts", "Engine Parts", WareCategory.TIER_2),
    "hullparts": Ware("hullparts", "Hull Parts", WareCategory.TIER_2),
    "majasnails": Ware("majasnails", "Maja Snails", WareCategory.TIER_2),
    "meat": Ware("meat", "Meat", WareCategory.TIER_2),
    "microchips": Ware("microchips", "Microchips", WareCategory.TIER_2),
    "plankton": Ware("plankton", "Plankton", WareCategory.TIER_2),
    "plasmaconductors": Ware("plasmaconductors", "Plasma Conductors", WareCategory.TIER_2),
    "quantumtubes": Ware("quantumtubes", "Quantum Tubes", WareCategory.TIER_2),
    "scanningarrays": Ware("scanningarrays", "Scanning Arrays", WareCategory.TIER_2),
    "scruffinfruit": Ware("scruffinfruit", "Scruffin Fruit", WareCategory.TIER_2),
    "siliconcarbide": Ware("siliconcarbide", "Silicon Carbide", WareCategory.TIER_2),
    "smartchips": Ware("smartchips", "Smart Chips", WareCategory.TIER_2),
    "sojabeans": Ware("sojabeans", "Soja Beans", WareCategory.TIER_2),
    "spices": Ware("spices", "Spices", WareCategory.TIER_2),
    "sunrise_flowers": Ware("sunrise_flowers", "Sunrise Flowers", WareCategory.TIER_2),
    "sunriseflowers": Ware("sunriseflowers", "Sunrise Flowers", WareCategory.TIER_2),
    "swampplant": Ware("swampplant", "Swamp Plant", WareCategory.TIER_2),
    "terranmre": Ware("terranmre", "Terran MRE", WareCategory.TIER_2),
    "wheat": Ware("wheat", "Wheat", WareCategory.TIER_2),

    # TIER 3 - Advanced products (final tier)
    "advancedelectronics": Ware("advancedelectronics", "Advanced Electronics", WareCategory.TIER_3),
    "antimatterconverters": Ware("antimatterconverters", "Antimatter Converters", WareCategory.TIER_3),
    "bofu": Ware("bofu", "BoFu", WareCategory.TIER_3),
    "claytronics": Ware("claytronics", "Claytronics", WareCategory.TIER_3),
    "dronecomponents": Ware("dronecomponents", "Drone Components", WareCategory.TIER_3),
    "fieldcoils": Ware("fieldcoils", "Field Coils", WareCategory.TIER_3),
    "foodrations": Ware("foodrations", "Food Rations", WareCategory.TIER_3),
    "majadust": Ware("majadust", "Maja Dust", WareCategory.TIER_3),
    "medicalsupplies": Ware("medicalsupplies", "Medical Supplies", WareCategory.TIER_3),
    "missilecomponents": Ware("missilecomponents", "Missile Components", WareCategory.TIER_3),
    "nostropolil": Ware("nostropolil", "Nostrop Oil", WareCategory.TIER_3),
    "shieldcomponents": Ware("shieldcomponents", "Shield Components", WareCategory.TIER_3),
    "sojahusk": Ware("sojahusk", "Soja Husk", WareCategory.TIER_3),
    "spacefuel": Ware("spacefuel", "Spacefuel", WareCategory.TIER_3),
    "spaceweed": Ware("spaceweed", "Spaceweed", WareCategory.TIER_3),
    "turretcomponents": Ware("turretcomponents", "Turret Components", WareCategory.TIER_3),
    "weaponcomponents": Ware("weaponcomponents", "Weapon Components", WareCategory.TIER_3),
}


def normalize_ware_id(ware_id: str) -> str:
    """
    Normalize a ware ID for consistent lookups.

    X4 wares use lowercase IDs without underscores (e.g., "energycells", "refinedmetals").
    This normalizes any input format to match the database keys.
    """
    return ware_id.lower().replace("_", "").replace(" ", "")


def get_ware(ware_id: str) -> Ware:
    """Get ware from database or create a new unknown ware."""
    normalized = normalize_ware_id(ware_id)

    if normalized in WARE_DATABASE:
        return WARE_DATABASE[normalized]

    # Create unknown ware with original ID preserved
    return Ware(ware_id, ware_id.replace("_", " ").title(), WareCategory.UNKNOWN)


def categorize_ware(ware_id: str) -> WareCategory:
    """Determine category of a ware."""
    ware = get_ware(ware_id)
    return ware.category
