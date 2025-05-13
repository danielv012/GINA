import math
from dataclasses import dataclass, field


# Configuration Constants
WALL_THICKNESS = 0.06889659248  # ~4 mm


@dataclass
class Parameters:
    R_c: float  # Chamber radius
    R_t: float  # Throat radius
    Lvp: float  # Virtual point length
    contraction_ratio: float
    contract_angle: float  # Degrees
    nozzle_angle: float  # Degrees
    R_e: float  # Exit radius

    # Derived attributes
    R_4: float = field(init=False)
    R_5: float = field(init=False)

    def __post_init__(self):
        self.R_4 = 1.5 * self.R_t
        self.R_5 = 0.45 * self.R_t

    def apply_wall_thickness(self, thickness: float):
        self.R_c += thickness
        self.R_t = self.R_c / math.sqrt(self.contraction_ratio)
        self.__post_init__()

    def __str__(self):
        return (
            f"R_c: {self.R_c:.4f}\nR_t: {self.R_t:.4f}\nR_e: {self.R_e:.4f}\nLvp: {self.Lvp:.4f}\n"
            f"contract_angle: {self.contract_angle}°\nnozzle_angle: {self.nozzle_angle}°\n"
            f"R_4: {self.R_4:.4f}\nR_5: {self.R_5:.4f}"
        )


@dataclass
class Sizing:
    t_4: float
    z_4: float
    r_4: float
    r_3: float
    z_3: float
    t_3: float
    z_2: float
    R_2: float
    r_2: float
    t_5: float
    r_6: float
    z_6: float
    L_n: float

    def __str__(self):
        return (
            f"t_4: {math.degrees(self.t_4):.2f}°\nz_4: {self.z_4:.4f}\nr_4: {self.r_4:.4f}\n"
            f"r_3: {self.r_3:.4f}\nz_3: {self.z_3:.4f}\nt_3: {math.degrees(self.t_3):.2f}°\n"
            f"z_2: {self.z_2:.4f}\nR_2: {self.R_2:.4f}\nr_2: {self.r_2:.4f}\n"
            f"t_5: {math.degrees(self.t_5):.2f}°\nr_6: {self.r_6:.4f}\nz_6: {self.z_6:.4f}\n"
            f"L_n: {self.L_n:.4f}"
        )


def calculate_sizing(params: Parameters) -> Sizing:
    # === Contraction arc from throat to transition point (Point 4) ===
    # t_4: angle of the arc at point 4 (entrance to throat curve)
    t_4 = math.atan(-1 / math.tan(math.radians(-params.contract_angle))) + math.pi
    # z_4: axial (horizontal) position at start of contraction arc (Point 4)
    z_4 = params.R_4 * math.cos(t_4)
    # r_4: radial (vertical) position at start of contraction arc (Point 4)
    r_4 = params.R_4 * math.sin(t_4) + params.R_t + params.R_4

    # === Converging straight line from chamber to contraction arc (Point 3) ===
    # r_3: radial position of point 3, linear interpolation from chamber to point 4 using virtual point method
    r_3 = params.R_c - params.Lvp * (params.R_c - r_4)
    # z_3: axial position of point 3, based on contraction angle and linear slope from r_3 to r_4
    z_3 = ((r_3 - r_4) / math.tan(math.radians(-params.contract_angle))) + z_4

    # === Contraction circular blend between straight line and chamber (Point 2) ===
    # t_3: tangent angle at point 3 for contraction circle
    t_3 = math.atan(-1 / math.tan(math.radians(-params.contract_angle)))
    # z_2: axial position where the contraction arc (curve 2) begins
    z_2 = -((r_3 - params.R_c) * math.cos(t_3) - z_3 * (math.sin(t_3) - 1)) / (
        math.sin(t_3) - 1
    )
    # R_2: radius of curvature for curve 2 (between chamber and straight line)
    R_2 = (r_3 - params.R_c) / (math.sin(t_3) - 1)
    # r_2: radial position where contraction arc (curve 2) begins
    r_2 = params.R_c - R_2

    # === Expansion arc after throat (Point 5 to Point 6) ===
    # t_5: tangent angle at point 5, start of diverging nozzle arc
    t_5 = math.atan(-1 / math.tan(math.radians(params.nozzle_angle)))
    # r_6: radial position of point 6, end of expansion arc
    r_6 = params.R_5 * math.sin(t_5) + params.R_t + params.R_5
    # z_6: axial position of point 6, end of expansion arc
    z_6 = params.R_5 * math.cos(t_5)

    # === Nozzle straight section (during curve 5-6) ===
    # L_n: nozzle length from throat (r_t) to exit (r_e), forming final conical section
    L_n = (params.R_e - params.R_t) / math.tan(math.radians(params.nozzle_angle))

    # Return full geometry profile encapsulated in Sizing dataclass
    return Sizing(t_4, z_4, r_4, r_3, z_3, t_3, z_2, R_2, r_2, t_5, r_6, z_6, L_n)


def main():
    # Initial geometry (pre-wall-thickness)
    base_params = Parameters(
        R_c=3.530950365 / 2,
        R_t=1.248379473 / 2,
        R_e=2.301477106 / 2,
        Lvp=1 / 3,
        contraction_ratio=8,
        contract_angle=30,
        nozzle_angle=15,
    )

    print("=== Base Parameters ===")
    print(base_params)
    print("\n=== Base Sizing ===")
    print(calculate_sizing(base_params))

    # Adjust for wall thickness
    base_params.apply_wall_thickness(WALL_THICKNESS)

    print("\n-------------------------------------")
    print("=== With Wall Thickness Applied ===")
    print(base_params)
    print("\n=== Sizing After Wall Thickness ===")
    print(calculate_sizing(base_params))


if __name__ == "__main__":
    main()
