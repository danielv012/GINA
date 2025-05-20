import math
from dataclasses import dataclass, asdict
from pprint import pprint

import numpy as np
import matplotlib.pyplot as plt

from pyfluids import Fluid, FluidsList, Input
from scipy.constants import convert_temperature, psi

from conversions import in2_to_m2


def flow_velocity(mass_flow_rate: float, density: float, area: float) -> float:
    """
    Calculate the flow velocity of a fluid.

    Args:
        mass_flow_rate: Mass flow rate in kg/s
        density: Density of the fluid in kg/m^3
        area: Area of the pipe in m^2

    Returns:
        Flow velocity in m/s
    """
    return mass_flow_rate / (density * area)


@dataclass
class SimulationInput:
    """Input parameters."""

    # Fluid to use for density calculations
    fluid: FluidsList
    # Fluid purity (percentage)
    fluid_purity: float
    # Ambient temperature (R)
    T: float
    # Mass flow rate (kg/s)
    mass_flow_rate: float
    # Pipe diameter (inches)
    pipe_diameter: float
    # Pressure range (psi)
    pressure_range: tuple = (100, 1000)
    # Pressure increment (psi)
    pressure_increment: float = 100.0


simulations = [
    SimulationInput(
        fluid=FluidsList.Oxygen,
        fluid_purity=100.0,
        T=convert_temperature(70, "F", "R"),
        mass_flow_rate=0.0787087986,
        pipe_diameter=0.527,
    ),
    SimulationInput(
        fluid=FluidsList.Ethanol,
        fluid_purity=100.0,
        T=convert_temperature(70, "F", "R"),
        mass_flow_rate=0.0655906655,
        pipe_diameter=0.305,
    ),
]


for simulation in simulations:
    print("Running simulation with parameters:")
    pprint(asdict(simulation), sort_dicts=False)
    pipe_area = in2_to_m2(math.pi * (simulation.pipe_diameter / 2) ** 2)
    pressure_and_velocity = []
    for pressure in np.arange(
        simulation.pressure_range[0],
        simulation.pressure_range[1],
        simulation.pressure_increment,
    ):
        density = (
            Fluid(simulation.fluid, simulation.fluid_purity)
            .with_state(
                Input.pressure(pressure * psi),
                Input.temperature(convert_temperature(simulation.T, "R", "C")),
            )
            .density
        )
        flow_velocity_value = flow_velocity(
            simulation.mass_flow_rate, density, pipe_area
        )
        print(
            f"Pressure: {pressure} PSI, Density: {density} kg/m^3, Flow Velocity: {flow_velocity_value} m/s"
        )
        pressure_and_velocity.append((pressure, flow_velocity_value))
    pressure_and_velocity = np.asarray(pressure_and_velocity)

    plt.subplots()[1].axhline(y=30, color="k")
    plt.plot(pressure_and_velocity[:, 0], pressure_and_velocity[:, 1])
    plt.xlabel("Pressure (PSI)")
    plt.ylabel("Flow Velocity (m/s)")
    plt.title(
        f"Flow Velocity vs Pressure for {simulation.fluid.name} in a {simulation.pipe_diameter} inch ID tube"
    )
    plt.show()
