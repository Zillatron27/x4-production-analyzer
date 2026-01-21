"""Database of X4 wares and their categories."""

from .entities import Ware, WareCategory

# Comprehensive ware database with categorization
WARE_DATABASE = {
    # Ship Components - used in ship construction and equipment
    "advancedcomposite": Ware("advancedcomposite", "Advanced Composites", WareCategory.SHIP_COMPONENTS),
    "advancedelectronics": Ware("advancedelectronics", "Advanced Electronics", WareCategory.SHIP_COMPONENTS),
    "antimatterconverters": Ware("antimatterconverters", "Antimatter Converters", WareCategory.SHIP_COMPONENTS),
    "claytronics": Ware("claytronics", "Claytronics", WareCategory.SHIP_COMPONENTS),
    "dronecomponents": Ware("dronecomponents", "Drone Components", WareCategory.SHIP_COMPONENTS),
    "engineparts": Ware("engineparts", "Engine Parts", WareCategory.SHIP_COMPONENTS),
    "fieldcoils": Ware("fieldcoils", "Field Coils", WareCategory.SHIP_COMPONENTS),
    "hullparts": Ware("hullparts", "Hull Parts", WareCategory.SHIP_COMPONENTS),
    "missilecomponents": Ware("missilecomponents", "Missile Components", WareCategory.SHIP_COMPONENTS),
    "shieldcomponents": Ware("shieldcomponents", "Shield Components", WareCategory.SHIP_COMPONENTS),
    "smartchips": Ware("smartchips", "Smart Chips", WareCategory.SHIP_COMPONENTS),
    "turretcomponents": Ware("turretcomponents", "Turret Components", WareCategory.SHIP_COMPONENTS),
    "weaponcomponents": Ware("weaponcomponents", "Weapon Components", WareCategory.SHIP_COMPONENTS),

    # Advanced Materials - high-tech manufacturing inputs
    "antimattercells": Ware("antimattercells", "Antimatter Cells", WareCategory.ADVANCED_MATERIALS),
    "microchips": Ware("microchips", "Microchips", WareCategory.ADVANCED_MATERIALS),
    "quantumtubes": Ware("quantumtubes", "Quantum Tubes", WareCategory.ADVANCED_MATERIALS),
    "scanningarrays": Ware("scanningarrays", "Scanning Arrays", WareCategory.ADVANCED_MATERIALS),
    "plasmaconductors": Ware("plasmaconductors", "Plasma Conductors", WareCategory.ADVANCED_MATERIALS),
    "superfluidcoolant": Ware("superfluidcoolant", "Superfluid Coolant", WareCategory.ADVANCED_MATERIALS),

    # Intermediate - processed materials and components
    "energycells": Ware("energycells", "Energy Cells", WareCategory.INTERMEDIATE),
    "foodrations": Ware("foodrations", "Food Rations", WareCategory.INTERMEDIATE),
    "graphene": Ware("graphene", "Graphene", WareCategory.INTERMEDIATE),
    "refinedmetals": Ware("refinedmetals", "Refined Metals", WareCategory.INTERMEDIATE),
    "siliconwafers": Ware("siliconwafers", "Silicon Wafers", WareCategory.INTERMEDIATE),
    "teladianium": Ware("teladianium", "Teladianium", WareCategory.INTERMEDIATE),
    "medicalsupplies": Ware("medicalsupplies", "Medical Supplies", WareCategory.INTERMEDIATE),
    "majadust": Ware("majadust", "Maja Dust", WareCategory.INTERMEDIATE),
    "spacefuel": Ware("spacefuel", "Spacefuel", WareCategory.INTERMEDIATE),
    "spaceweed": Ware("spaceweed", "Spaceweed", WareCategory.INTERMEDIATE),

    # Basic - raw materials and food ingredients
    "water": Ware("water", "Water", WareCategory.BASIC),
    "methane": Ware("methane", "Methane", WareCategory.BASIC),
    "hydrogen": Ware("hydrogen", "Hydrogen", WareCategory.BASIC),
    "helium": Ware("helium", "Helium", WareCategory.BASIC),
    "ice": Ware("ice", "Ice", WareCategory.BASIC),
    "ore": Ware("ore", "Ore", WareCategory.BASIC),
    "silicon": Ware("silicon", "Silicon", WareCategory.BASIC),
    "nividium": Ware("nividium", "Nividium", WareCategory.BASIC),
    "rawscrap": Ware("rawscrap", "Raw Scrap", WareCategory.BASIC),
    "spices": Ware("spices", "Spices", WareCategory.BASIC),
    "wheat": Ware("wheat", "Wheat", WareCategory.BASIC),
    "meat": Ware("meat", "Meat", WareCategory.BASIC),
    "sojabeans": Ware("sojabeans", "Soja Beans", WareCategory.BASIC),
    "sojahusk": Ware("sojahusk", "Soja Husk", WareCategory.BASIC),
    "sunrise_flowers": Ware("sunrise_flowers", "Sunrise Flowers", WareCategory.BASIC),
    "majasnails": Ware("majasnails", "Maja Snails", WareCategory.BASIC),
    "swampplant": Ware("swampplant", "Swamp Plant", WareCategory.BASIC),
}


def get_ware(ware_id: str) -> Ware:
    """Get ware from database or create a new unknown ware."""
    if ware_id in WARE_DATABASE:
        return WARE_DATABASE[ware_id]
    # Create unknown ware
    return Ware(ware_id, ware_id.replace("_", " ").title(), WareCategory.UNKNOWN)


def categorize_ware(ware_id: str) -> WareCategory:
    """Determine category of a ware."""
    ware = get_ware(ware_id)
    return ware.category
