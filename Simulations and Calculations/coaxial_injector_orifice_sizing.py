import math

from pyfluids import Fluid, FluidsList, Input
from scipy.constants import convert_temperature, bar


def calculate_injector_element_geometry(num_elements: int):
    """
    Calculates the geometry for a single injector element given the total
    number of elements on the faceplate.
    """
    print(f"\n--- Calculating for {num_elements} Element(s) ---")

    # --- Constants ---
    CHAMBER_PRESSURE = 20  # bar
    TOTAL_M_FLOW_RATE = 0.1442994641  # kg/s
    OF = 1.3
    Cd = 0.6
    GOX_GAMMA = 1.4
    GOX_INLET_P = 55  # bar
    GOX_INLET_T = 300  # K
    ETHANOL_INLET_T = 300  # K
    ETHANOL_REF_P = 25  # bar
    ETHANOL_DP_FRAC = 0.15
    WALL_THICKNESS_MM = 0.5

    # --- Mass Flow Per Element ---
    m_flow_rate_per_element = TOTAL_M_FLOW_RATE / num_elements
    gox_m_flow_rate = m_flow_rate_per_element * (OF / (1 + OF))
    ethanol_m_flow_rate = m_flow_rate_per_element * (1 / (OF + 1))

    # --- Fluid Properties ---
    gox_inlet_density = (
        Fluid(FluidsList.Oxygen, 100)
        .with_state(
            Input.pressure(GOX_INLET_P * bar),
            Input.temperature(convert_temperature(GOX_INLET_T, "K", "C")),
        )
        .density
    )
    ethanol_inlet_density = (
        Fluid(FluidsList.Ethanol, 100)
        .with_state(
            Input.pressure(ETHANOL_REF_P * bar),
            Input.temperature(convert_temperature(ETHANOL_INLET_T, "K", "C")),
        )
        .density
    )

    # --- GOX Orifice Area Calculation (Unchoked Flow) ---
    p_ratio = CHAMBER_PRESSURE / GOX_INLET_P
    is_choked_flow = (CHAMBER_PRESSURE / GOX_INLET_P) <= (
        (2 / (GOX_GAMMA + 1)) ** (GOX_GAMMA / (GOX_GAMMA - 1))
    )

    if is_choked_flow:
        print("----------> Calculating for compressible choked flow")
        A_gox = gox_m_flow_rate / (
            Cd
            * math.sqrt(
                GOX_GAMMA
                * gox_inlet_density
                * GOX_INLET_P
                * bar
                * ((2 / (GOX_GAMMA + 1)) ** ((GOX_GAMMA + 1) / (GOX_GAMMA - 1)))
            )
        )
        Vel_gox = gox_m_flow_rate / (gox_inlet_density * A_gox)
        print(f"GOX orifice area: {A_gox * 1e6} mm^2")
        print(f"GOX velocity at the orifice: {Vel_gox} m/s")
    else:
        # https://en.wikipedia.org/wiki/Orifice_plate#Compressible_flow
        print("----------> Caculating for compressible un-choked flow")
        p_ratio = CHAMBER_PRESSURE / GOX_INLET_P
        A_gox = gox_m_flow_rate / (
            Cd
            * math.sqrt(
                2
                * gox_inlet_density
                * (GOX_INLET_P * bar)
                * (
                    (GOX_GAMMA / (GOX_GAMMA - 1))
                    * (
                        p_ratio ** (2 / GOX_GAMMA)
                        - p_ratio ** ((GOX_GAMMA + 1) / GOX_GAMMA)
                    )
                )
            )
        )
        Vel_gox = gox_m_flow_rate / (gox_inlet_density * A_gox)
        print(f"GOX orifice area: {A_gox * 1e6} mm^2")
        print(f"GOX velocity at the orifice: {Vel_gox} m/s")

    # --- Ethanol Orifice Area Calculation ---
    ethanol_target_dp = ETHANOL_DP_FRAC * CHAMBER_PRESSURE  # Target dP in bar
    A_eth = ethanol_m_flow_rate / (
        Cd * math.sqrt(2 * ethanol_inlet_density * (ethanol_target_dp * bar))
    )
    Vel_eth = ethanol_m_flow_rate / (ethanol_inlet_density * A_eth)

    # --- Calculate Element Geometry (assuming GOX Annular, Ethanol Centric) ---
    A_eth_mm2 = A_eth * 1e6
    A_gox_mm2 = A_gox * 1e6

    # Ethanol (centric) is the inner element
    D_eth_inner = math.sqrt(4 * A_eth_mm2 / math.pi)

    # Assume a wall thickness for the ethanol post, e.g., 1 mm
    # So the OD is the ID + 2 * wall_thickness
    D_eth_post_OD = D_eth_inner + 2 * WALL_THICKNESS_MM  # This is the "post" diameter

    # The area of the post itself
    A_post_mm2 = (math.pi / 4) * (D_eth_post_OD**2)

    # The GOX (annular) flows around the ethanol post.
    # The total area occupied by the GOX and the post is A_outer.
    A_outer_mm2 = A_gox_mm2 + A_post_mm2
    D_gox_outer = math.sqrt(4 * A_outer_mm2 / math.pi)

    print("\n--- Overall sizing outcomes ---")
    print(
        f"J (g/l): {(gox_inlet_density * (Vel_gox ** 2))/ (ethanol_inlet_density * (Vel_eth ** 2))}"
    )
    print(f"Area Ratio: (g/l): {A_gox/A_eth}")

    # --- Print Results for a Single Element ---
    print(f"Mass Flow Rate per Element: {m_flow_rate_per_element:.4f} kg/s")
    print(f"Required GOX Orifice Area: {A_gox_mm2:.4f} mm^2")
    print(f"Required Ethanol Orifice Area: {A_eth_mm2:.4f} mm^2")
    print("\n--- Single Element Dimensions ---")
    print(f"Ethanol Inner Diameter (ID): {D_eth_inner:.4f} mm")
    print(f"Ethanol Post Outer Diameter (OD): {D_eth_post_OD:.4f} mm")
    print(f"GOX Annulus Outer Diameter (OD): {D_gox_outer:.4f} mm")


# --- Run the calculation for different element counts ---
calculate_injector_element_geometry(num_elements=1)
calculate_injector_element_geometry(num_elements=2)
