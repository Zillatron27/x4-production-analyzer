"""Expansion planning and impact analysis."""

import math
from dataclasses import dataclass, field
from typing import List, Optional

from ..models.entities import Ware
from ..models.ware_database import get_ware


@dataclass
class InputRequirement:
    """Analysis of a single input ware requirement for expansion."""
    ware: Ware
    current_consumption: float  # units/hr currently consumed empire-wide
    new_consumption: float  # units/hr after expansion
    delta_consumption: float  # additional consumption needed
    your_production: float  # units/hr you currently produce
    your_net_available: float  # production - existing consumption
    status: str  # "sufficient", "marginal", "insufficient"
    surplus_or_deficit: float  # positive = surplus, negative = deficit


@dataclass
class BottleneckSolution:
    """A specific way to resolve a bottleneck."""
    solution_type: str  # "expand_production", "assign_miners", "purchase_market"
    description: str  # Human-readable action
    modules_needed: Optional[int] = None
    miners_needed: Optional[int] = None
    is_feasible: bool = True
    blocking_issues: List[str] = field(default_factory=list)


@dataclass
class Bottleneck:
    """A production bottleneck that must be resolved."""
    ware: Ware
    deficit: float  # units/hr shortage
    severity: str  # "critical" (>50% short), "high" (20-50%), "medium" (<20%)
    solutions: List[BottleneckSolution] = field(default_factory=list)
    recommended_solution: Optional[BottleneckSolution] = None


@dataclass
class ExpansionPlan:
    """Complete analysis of expanding production of a ware."""
    target_ware: Ware
    current_modules: int
    planned_modules: int
    current_rate: float  # units/hr
    planned_rate: float  # units/hr
    increase_amount: float  # units/hr increase
    increase_percent: float

    input_requirements: List[InputRequirement] = field(default_factory=list)
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    is_feasible: bool = True  # Can this expansion proceed without resolving bottlenecks?


# Raw materials that can be mined
RAW_MATERIALS = {
    "ore", "silicon", "nividium", "rawscrap",
    "hydrogen", "helium", "methane", "ice"
}


def is_raw_material(ware_id: str) -> bool:
    """Check if a ware is a mineable raw material."""
    normalized = ware_id.lower().replace("_", "")
    return normalized in RAW_MATERIALS


def calculate_expansion_impact(
    ware_id: str,
    additional_modules: int,
    wares_extractor,
    analyzer
) -> ExpansionPlan:
    """
    Calculate the impact of expanding production of a ware.

    Args:
        ware_id: The ware to expand (e.g., "hullparts")
        additional_modules: How many modules to add
        wares_extractor: WaresExtractor instance with game data
        analyzer: ProductionAnalyzer with current empire state

    Returns:
        Complete expansion analysis
    """
    # Get current stats from analyzer
    current_stats = analyzer.get_ware_stats(ware_id)
    if not current_stats:
        raise ValueError(f"No production data found for '{ware_id}' in your empire")

    # Get game data for this ware
    game_ware = wares_extractor.wares.get(ware_id.lower())
    if not game_ware or not game_ware.default_method:
        raise ValueError(f"No game production data for '{ware_id}' - may not be a producible ware")

    # Calculate new production rate
    method = game_ware.default_method
    module_rate = method.units_per_hour
    current_rate = current_stats.production_rate_per_hour
    planned_rate = current_rate + (additional_modules * module_rate)
    increase_amount = additional_modules * module_rate
    increase_percent = (increase_amount / current_rate * 100) if current_rate > 0 else 100.0

    # Analyze each input requirement
    input_requirements = []
    bottlenecks = []

    for resource in method.resources:
        input_req = _analyze_input_requirement(
            resource.ware_id,
            resource.amount,
            additional_modules,
            method,
            analyzer
        )
        input_requirements.append(input_req)

        if input_req.status == "insufficient":
            bottleneck = _create_bottleneck(
                input_req.ware,
                abs(input_req.surplus_or_deficit),
                wares_extractor,
                analyzer
            )
            bottlenecks.append(bottleneck)

    # Generate recommendations
    recommendations = _generate_recommendations(
        current_stats.ware,
        additional_modules,
        input_requirements,
        bottlenecks
    )

    # Is this feasible without resolving bottlenecks?
    is_feasible = len(bottlenecks) == 0

    return ExpansionPlan(
        target_ware=current_stats.ware,
        current_modules=current_stats.module_count,
        planned_modules=current_stats.module_count + additional_modules,
        current_rate=current_rate,
        planned_rate=planned_rate,
        increase_amount=increase_amount,
        increase_percent=increase_percent,
        input_requirements=input_requirements,
        bottlenecks=bottlenecks,
        recommendations=recommendations,
        is_feasible=is_feasible
    )


def _analyze_input_requirement(
    input_ware_id: str,
    amount_per_cycle: int,
    additional_modules: int,
    production_method,
    analyzer
) -> InputRequirement:
    """
    Analyze a single input requirement for the expansion.
    """
    ware = get_ware(input_ware_id)

    # Calculate consumption increase per module
    consumption_per_module = production_method.resource_per_hour(input_ware_id)
    delta_consumption = additional_modules * consumption_per_module

    # Get current state of this input ware
    input_stats = analyzer.get_ware_stats(input_ware_id)

    if input_stats:
        current_consumption = input_stats.consumption_rate_per_hour
        your_production = input_stats.production_rate_per_hour
    else:
        # No stats means we don't produce or consume this currently
        current_consumption = 0.0
        your_production = 0.0

    new_consumption = current_consumption + delta_consumption
    your_net_available = your_production - current_consumption
    surplus_or_deficit = your_net_available - delta_consumption

    # Determine status with 10% buffer threshold
    if surplus_or_deficit < 0:
        status = "insufficient"
    elif surplus_or_deficit < (delta_consumption * 0.1):
        status = "marginal"
    else:
        status = "sufficient"

    return InputRequirement(
        ware=ware,
        current_consumption=current_consumption,
        new_consumption=new_consumption,
        delta_consumption=delta_consumption,
        your_production=your_production,
        your_net_available=your_net_available,
        status=status,
        surplus_or_deficit=surplus_or_deficit
    )


def _create_bottleneck(
    ware: Ware,
    deficit: float,
    wares_extractor,
    analyzer
) -> Bottleneck:
    """Create bottleneck analysis with solution options."""
    solutions = []
    ware_id = ware.ware_id.lower()

    # Get current production to calculate severity
    input_stats = analyzer.get_ware_stats(ware_id)
    current_production = input_stats.production_rate_per_hour if input_stats else 0.0

    # Calculate severity based on deficit vs total needed
    total_needed = current_production + deficit
    deficit_percent = (deficit / total_needed * 100) if total_needed > 0 else 100

    if deficit_percent > 50:
        severity = "critical"
    elif deficit_percent > 20:
        severity = "high"
    else:
        severity = "medium"

    # Solution 1: Expand production (if producible)
    game_ware = wares_extractor.wares.get(ware_id)
    if game_ware and game_ware.default_method:
        module_output = game_ware.default_method.units_per_hour
        modules_needed = math.ceil(deficit / module_output) if module_output > 0 else 1

        # Check if expanding this would create secondary bottlenecks
        blocking_issues = []
        for resource in game_ware.default_method.resources:
            res_stats = analyzer.get_ware_stats(resource.ware_id)
            if res_stats:
                res_available = res_stats.production_rate_per_hour - res_stats.consumption_rate_per_hour
                res_needed = modules_needed * game_ware.default_method.resource_per_hour(resource.ware_id)
                if res_available < res_needed:
                    res_ware = get_ware(resource.ware_id)
                    blocking_issues.append(f"{res_ware.name} also needs expansion")

        solutions.append(BottleneckSolution(
            solution_type="expand_production",
            description=f"Add {modules_needed} {ware.name} production module{'s' if modules_needed > 1 else ''}",
            modules_needed=modules_needed,
            is_feasible=len(blocking_issues) == 0,
            blocking_issues=blocking_issues
        ))

    # Solution 2: Mining (if raw material)
    if is_raw_material(ware_id):
        # Rough estimate: average miner ~10,000 units/hr throughput
        avg_miner_throughput = 10000
        miners_needed = math.ceil(deficit / avg_miner_throughput)

        solutions.append(BottleneckSolution(
            solution_type="assign_miners",
            description=f"Assign {miners_needed} additional miner{'s' if miners_needed > 1 else ''} for {ware.name}",
            miners_needed=miners_needed,
            is_feasible=True,
            blocking_issues=["Requires available miners in fleet"]
        ))

    # Solution 3: Market purchase (always available)
    solutions.append(BottleneckSolution(
        solution_type="purchase_market",
        description=f"Purchase ~{int(deficit):,}/hr from NPC stations",
        is_feasible=True,
        blocking_issues=["Ongoing cost - not self-sufficient"]
    ))

    # Recommend best solution
    recommended = _recommend_solution(solutions)

    return Bottleneck(
        ware=ware,
        deficit=deficit,
        severity=severity,
        solutions=solutions,
        recommended_solution=recommended
    )


def _recommend_solution(solutions: List[BottleneckSolution]) -> Optional[BottleneckSolution]:
    """
    Recommend best solution.
    Priority: feasible production > mining > non-feasible production > market
    """
    # Feasible production expansion
    for sol in solutions:
        if sol.solution_type == "expand_production" and sol.is_feasible:
            return sol

    # Mining
    for sol in solutions:
        if sol.solution_type == "assign_miners":
            return sol

    # Non-feasible production (still better long-term than market)
    for sol in solutions:
        if sol.solution_type == "expand_production":
            return sol

    # Market as last resort
    for sol in solutions:
        if sol.solution_type == "purchase_market":
            return sol

    return None


def _generate_recommendations(
    target_ware: Ware,
    additional_modules: int,
    input_requirements: List[InputRequirement],
    bottlenecks: List[Bottleneck]
) -> List[str]:
    """Generate human-readable recommendations."""
    recommendations = []

    if not bottlenecks:
        recommendations.append(
            "Expansion is feasible - all input requirements can be met"
        )
        recommendations.append(
            f"You can safely add {additional_modules} {target_ware.name} module{'s' if additional_modules > 1 else ''}"
        )
    else:
        recommendations.append(
            f"{len(bottlenecks)} bottleneck{'s' if len(bottlenecks) > 1 else ''} must be resolved first:"
        )

        for bottleneck in bottlenecks:
            if bottleneck.recommended_solution:
                sol = bottleneck.recommended_solution
                rec = f"  {bottleneck.ware.name}: {sol.description}"
                recommendations.append(rec)

                if not sol.is_feasible and sol.blocking_issues:
                    for issue in sol.blocking_issues:
                        recommendations.append(f"    (Note: {issue})")

    # Highlight marginal inputs
    marginal = [r for r in input_requirements if r.status == "marginal"]
    if marginal:
        recommendations.append("")
        recommendations.append("Marginal supplies (tight buffer):")
        for req in marginal:
            recommendations.append(
                f"  {req.ware.name}: only {req.surplus_or_deficit:,.0f}/hr surplus after expansion"
            )

    return recommendations
