"""
Iterative solver for regulated pressure given valve Cv's and a desired outlet pressure.
Use for incompressible gas or liquid single-phase flow only.
"""

from __future__ import annotations
from math import sqrt
from enum import Enum
from pprint import pprint

from dataclasses import dataclass, asdict
from conversions import m3_to_gal, m3_to_scft

from pyfluids import Fluid, FluidsList, Input
from scipy.constants import convert_temperature, psi


class FluidType(Enum):
    """Fluid types."""

    LIQUID = "liquid"
    GAS = "gas"


@dataclass
class SimulationInput:
    """Simulation input parameters."""

    # Fluid to use for density calculations
    fluid: FluidsList
    # Fluid purity (percentage)
    fluid_purity: float
    # Fluid type (gas or liquid)
    fluid_type: FluidType
    # Standard gravity of fluid
    SG: float
    # Desired outlet pressure (PSI)
    desired_outlet_pressure: float
    # Ambient temperature (R)
    T: float
    # Mass flow rate (kg/s)
    mass_flow_rate: float
    # Valves in order of closet to furthest from the tank.
    valves: list[Valve]
    # Initial guess for regulated pressure (PSI)
    initial_reg_pressure_guess: float
    # Iterations for solver
    iterations: int = 1000
    # Learning rate for solver
    learning_rate: float = 0.1
    # Account for density changes over valves
    density_change_over_valves: bool = True


@dataclass
class Valve:
    name: str
    Cv: float

    def inlet_P_gas(
        self,
        mass_flow_rate: float,
        sg: float,
        t: float,
        density: float,
        outlet_pressure: float,
    ) -> float:
        """Calculate inlet pressure of gas.

        Args:
            mass_flow_rate (float): Mass flow rate in kg/s.
            sg (float): Specific gravity of fluid.
            t (float): Temperature in Rankine.
            density (float): Density in kg/m^3.
            outlet_pressure (float): Outlet pressure in psi.

        Returns:
            float: Inlet pressure in psi.
        """
        Q = m3_to_scft(mass_flow_rate / density) * 60  # SCFH
        return sqrt(sg * t * ((Q / (962 * self.Cv)) ** 2) + outlet_pressure**2)

    def outlet_P_gas(
        self,
        mass_flow_rate: float,
        sg: float,
        t: float,
        density: float,
        inlet_pressure: float,
    ) -> float:
        """Calculate outlet pressure of gas.

        Args:
            mass_flow_rate (float): Mass flow rate in kg/s.
            sg (float): Specific gravity of fluid.
            t (float): Temperature in Rankine.
            density (float): Density in kg/m^3.
            inlet_pressure (float): Inlet pressure in psi.

        Returns:
            float: Outlet pressure in psi.
        """
        Q = m3_to_scft(mass_flow_rate / density) * 60  # SCFH
        return sqrt(inlet_pressure**2 - (sg * t * (Q / (962 * self.Cv)) ** 2))

    def dP_liquid(self, mass_flow_rate: float, sg: float, density: float) -> float:
        """Calculate pressure drop across valve for liquid.

        Args:
            mass_flow_rate (float): Mass flow rate in kg/s.
            sg (float): Specific gravity of fluid.
            density (float): Density in kg/m^3.

        Returns:
            float: Pressure drop in psi.
        """
        Q = m3_to_gal(mass_flow_rate / density) * 60  # GPM
        return sg * ((Q / self.Cv) ** 2)


def get_density(fluid: FluidsList, fluid_purity: float, p: float, t: float) -> float:
    """Get density of fluid at given pressure and temperature.

    Args:
        fluid (FluidsList): Fluid to use for density calculations.
        fluid_purity (float): Fluid purity (percentage).
        p (float): Pressure in psi.
        t (float): Temperature in Rankine.

    Returns:
        float: Density in kg/m^3.
    """
    return (
        Fluid(fluid, fluid_purity)
        .with_state(
            Input.pressure(p * psi), Input.temperature(convert_temperature(t, "R", "C"))
        )
        .density
    )


def run_simulation(
    sim: SimulationInput,
):
    """Run a simulation for the given input parameters.

    Args:
        simulation (SimulationInput): Simulation input parameters.

    Returns:
        float: Regulated pressure in psi.
    """
    print("Running simulation with parameters:")
    pprint(asdict(sim), sort_dicts=False)

    ## Run iterative solver for regulated pressure.
    reg_pressure = sim.initial_reg_pressure_guess
    for _ in range(sim.iterations):
        # Solve for outlet pressure given a tank pressure
        prev_pressure = reg_pressure
        density = get_density(sim.fluid, sim.fluid_purity, prev_pressure, sim.T)
        for valve in sim.valves:
            if sim.fluid_type == FluidType.GAS:
                prev_pressure = valve.outlet_P_gas(
                    mass_flow_rate=sim.mass_flow_rate,
                    sg=sim.SG,
                    t=sim.T,
                    density=density,
                    inlet_pressure=prev_pressure,
                )
            elif sim.fluid_type == FluidType.LIQUID:
                prev_pressure -= valve.dP_liquid(
                    mass_flow_rate=sim.mass_flow_rate, sg=sim.SG, density=density
                )

            # Assume incompressibility over valves,
            # but correct for density changes after each valve.
            if sim.density_change_over_valves:
                density = get_density(sim.fluid, sim.fluid_purity, prev_pressure, sim.T)

        # Correct tank pressure based on error.
        error = sim.desired_outlet_pressure - prev_pressure
        reg_pressure += sim.learning_rate * error

    ## Run simulation forward using ideal regulated pressure.
    pressure = reg_pressure
    for valve in sim.valves:
        inlet_pressure = pressure
        density = get_density(sim.fluid, sim.fluid_purity, inlet_pressure, sim.T)
        if sim.fluid_type == FluidType.GAS:
            pressure = valve.outlet_P_gas(
                mass_flow_rate=sim.mass_flow_rate,
                sg=sim.SG,
                t=sim.T,
                density=density,
                inlet_pressure=inlet_pressure,
            )
        elif sim.fluid_type == FluidType.LIQUID:
            pressure -= valve.dP_liquid(
                mass_flow_rate=sim.mass_flow_rate, sg=sim.SG, density=density
            )

        if sim.density_change_over_valves:
            density = get_density(sim.fluid, sim.fluid_purity, pressure, sim.T)

        print(
            valve.name,
            "Inlet P: ",
            inlet_pressure,
            "Outlet P: ",
            pressure,
            "dP: ",
            inlet_pressure - pressure,
        )
    print("Final outlet pressure: ", pressure)

    return reg_pressure


simulations: list[SimulationInput] = [
    SimulationInput(
        fluid=FluidsList.Oxygen,
        fluid_purity=100,
        fluid_type=FluidType.GAS,
        SG=1.1044,
        desired_outlet_pressure=322.305555556,
        T=convert_temperature(72, "F", "R"),
        mass_flow_rate=0.0787087986,
        valves=[
            Valve(name="Ball Valve", Cv=1.5),
            Valve(name="Check Valve", Cv=1.1),
        ],
        initial_reg_pressure_guess=1000,
    ),
    SimulationInput(
        fluid=FluidsList.Ethanol,
        fluid_purity=100,
        fluid_type=FluidType.LIQUID,
        SG=0.787,
        desired_outlet_pressure=322.305555556,
        T=convert_temperature(72, "F", "R"),
        mass_flow_rate=0.0655906655,
        valves=[
            Valve(name="Ball Valve 1", Cv=1.5),
            Valve(name="Ball Valve 2", Cv=1.5),
        ],
        initial_reg_pressure_guess=1000,
    ),
    SimulationInput(
        fluid=FluidsList.Ethanol,
        fluid_purity=100,
        fluid_type=FluidType.LIQUID,
        SG=0.787,
        desired_outlet_pressure=386.666666667,
        T=convert_temperature(72, "F", "R"),
        mass_flow_rate=0.0655906655,
        valves=[
            Valve(name="System", Cv=0.404),
        ],
        initial_reg_pressure_guess=1000,
    ),
]

for simulation in simulations:
    run_simulation(simulation)
