"""
This script generates a STEP file of Rao's nozzle using given parameters.
Parameters should be in millimeters.
"""

import numpy as np
import cadquery as cq
import math
from dataclasses import dataclass, field

# Workaround for show_object if not in CQ Editor.
if "show_object" not in globals():

    def show_object(*args, **kwargs):
        pass


@dataclass
class Parameters:
    """
    Parameters for the nozzle geometry.

    Attributes:
        R_c: float  # Chamber radius
        R_t: float  # Throat radius
        Lvp: float  # Vertical point length (0 < Lvp < 1)
        Note: Lvp is the amount of the chamber radius you want the contraction line to take up.
        contraction_diameter_ratio: float
        contract_angle: float  # Degrees
        nozzle_angle: float  # Degrees
        R_e: float  # Exit radius
        L_c: float  # Chamber length. This includes the contraction area (from the start of the chamber to the throat).
        wall_thickness: float  # Wall thickness of the nozzle
    """

    R_c: float  # Chamber radius
    R_t: float  # Throat radius
    Lvp: float  #  Vertical point length (0 < Lvp < 1)
    contraction_diameter_ratio: float
    contract_angle: float  # Degrees
    nozzle_angle: float  # Degrees
    R_e: float  # Exit radius
    L_c: float  # Chamber length. This includes the contraction area (from the start of the chamber to the throat).
    wall_thickness: float  # Wall thickness of the nozzle

    # Derived attributes
    R_4: float = field(init=False)
    R_5: float = field(init=False)

    def __post_init__(self):
        self.R_4 = 1.5 * self.R_t
        self.R_5 = 0.45 * self.R_t

    def apply_wall_thickness(self, thickness: float):
        self.R_c += thickness
        self.R_t = self.R_c / self.contraction_diameter_ratio
        self.__post_init__()

    def __str__(self):
        return (
            f"R_c: {self.R_c:.4f}\nR_t: {self.R_t:.4f}\nR_e: {self.R_e:.4f}\nLvp: {self.Lvp:.4f}\n"
            f"contract_angle: {self.contract_angle}°\nnozzle_angle: {self.nozzle_angle}°\n"
            f"R_4: {self.R_4:.4f}\nR_5: {self.R_5:.4f}"
        )


@dataclass
class Sizing:
    """
    Sizing parameters for the nozzle geometry.
    """

    L_c: float
    R_t: float
    R_c: float
    R_e: float
    t_4: float
    z_4: float
    r_4: float
    r_3: float
    z_3: float
    t_3: float
    z_2: float
    R_2: float
    r_2: float
    R_4: float
    R_5: float
    t_5: float
    r_5: float
    z_5: float
    L_n: float
    nozzle_angle: float
    wall_thickness: float

    def __str__(self):
        return (
            f"t_4: {math.degrees(self.t_4):.2f}°\nz_4: {self.z_4:.4f}\nr_4: {self.r_4:.4f}\n"
            f"r_3: {self.r_3:.4f}\nz_3: {self.z_3:.4f}\nt_3: {math.degrees(self.t_3):.2f}°\n"
            f"z_2: {self.z_2:.4f}\nR_2: {self.R_2:.4f}\nr_2: {self.r_2:.4f}\n"
            f"t_5: {math.degrees(self.t_5):.2f}°\nr_6: {self.r_5:.4f}\nz_6: {self.z_5:.4f}\n"
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
    r_5 = params.R_5 * math.sin(t_5) + params.R_t + params.R_5
    # z_6: axial position of point 6, end of expansion arc
    z_5 = params.R_5 * math.cos(t_5)

    # === Nozzle straight section (during curve 5-6) ===
    # L_n: nozzle length from throat (r_t) to exit (r_e), forming final conical section
    L_n = (params.R_e - params.R_t) / math.tan(math.radians(params.nozzle_angle))

    # Return full geometry profile encapsulated in Sizing dataclass
    return Sizing(
        params.L_c,
        params.R_t,
        params.R_c,
        params.R_e,
        t_4,
        z_4,
        r_4,
        r_3,
        z_3,
        t_3,
        z_2,
        R_2,
        r_2,
        params.R_4,
        params.R_5,
        t_5,
        r_5,
        z_5,
        L_n,
        params.nozzle_angle,
        params.wall_thickness,
    )


class Line:
    x1: float
    y1: float
    x2: float
    y2: float

    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def offset(self, dx: float, dy: float):
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy


class ParametricCircle:
    h: float
    k: float
    r: float

    def __init__(self, h: float, k: float, r: float):
        self.h = h
        self.k = k
        self.r = r

    def get_point(self, t: float) -> tuple[float, float]:
        x = self.h + self.r * math.cos(t)
        y = self.k + self.r * math.sin(t)
        return x, y


def circle_line_intersection(
    circle: ParametricCircle, line: Line, tol=1e-2
) -> list[tuple[float, float]]:
    # Solve using parametric substitution
    c = np.array([circle.h, circle.k])
    a = np.array([line.x1, line.y1])
    b = np.array([line.x2, line.y2]) - a

    # Quadratic coefficients
    A = np.dot(b, b)
    B = 2 * np.dot(b, a - c)
    C = np.dot(a - c, a - c) - circle.r**2

    descriminant = B**2 - 4 * A * C
    if descriminant < -tol:
        return []
    elif abs(descriminant) < tol:
        t = -B / (2 * A)
        x_y = a + b * t
        return [tuple(x_y)]
    else:
        result = []
        for op in [-1, 1]:
            t = (-B + op * np.sqrt(descriminant)) / (2 * A)
            intersecting_pt = a + b * t
            result.append(tuple(intersecting_pt))
        return result


def cad(sizing: Sizing) -> cq.Assembly:
    """
    Create the CAD model of the rocket nozzle using the provided sizing parameters.

    Args:
        sizing (Sizing): The sizing parameters for the nozzle.

    Returns:
        cq.Assembly: The CAD assembly of the nozzle.
    """
    inner_intersections = circle_line_intersection(
        ParametricCircle(sizing.z_2, sizing.r_2, sizing.R_2),
        Line(-999, sizing.R_c, 999, sizing.R_c),
    )
    if len(inner_intersections) == 0:
        raise ValueError("No intersection between inner R1 and Chamber Line found")
    # Choose the leftmost intersection point. This is the point in which R1 intersects with the combustion chamber.
    inner_leftmost_intersection = min(inner_intersections, key=lambda pt: pt[0])

    nozzle_end_z = (sizing.R_e - sizing.R_t) / math.tan(
        math.radians(sizing.nozzle_angle)
    )

    outer_intersections = circle_line_intersection(
        ParametricCircle(sizing.z_2, sizing.r_2 + sizing.wall_thickness, sizing.R_2),
        Line(
            -999,
            sizing.R_c + sizing.wall_thickness,
            999,
            sizing.R_c + sizing.wall_thickness,
        ),
    )
    if len(outer_intersections) == 0:
        raise ValueError("No intersection between outer R1 and Chamber Line found")
    # Choose the leftmost intersection point. This is the point in which R1 intersects with the combustion chamber.
    outer_leftmost_intersection = min(outer_intersections, key=lambda pt: pt[0])

    profile = (
        cq.Workplane("XY")
        # Move to leftmost point of the combustion chamber.
        .moveTo(-sizing.L_c, sizing.R_c)
        # Chamber outer wall line to start of initial contraction arc.
        .lineTo(inner_leftmost_intersection[0], inner_leftmost_intersection[1])
        # Inner contraction arc.
        .radiusArc((sizing.z_3, sizing.r_3), sizing.R_2)
        # Contraction Line from left, inner contraction arc to contraction arc before throat.
        .lineTo(sizing.z_4, sizing.r_4)
        # Arc from contraction line to throat
        .radiusArc((0, sizing.R_t), -sizing.R_4)
        # Arc from throat to nozzle line.
        .radiusArc((sizing.z_5, sizing.r_5), -sizing.R_5)
        # Nozzle line from throat to end of nozzle.
        .lineTo(nozzle_end_z, sizing.R_e)
        # We're now at the end of the inner nozzle wall.
        # Up to end of outer nozzle wall
        .lineTo(nozzle_end_z, sizing.R_e + sizing.wall_thickness)
        # Nozzle outer wall line
        .lineTo(sizing.z_5, sizing.r_5 + sizing.wall_thickness)
        # Arc from nozzle outer wall to throat
        .radiusArc((0, sizing.R_t + sizing.wall_thickness), sizing.R_5)
        # Arc from throat to contraction line
        .radiusArc((sizing.z_4, sizing.r_4 + sizing.wall_thickness), sizing.R_4)
        # Line to initial contraction arc
        .lineTo(sizing.z_3, sizing.r_3 + sizing.wall_thickness)
        # Arc from contraction line to chamber outer wall
        .radiusArc(
            (outer_leftmost_intersection[0], outer_leftmost_intersection[1]),
            -sizing.R_2,
        )
        # Outer chamber wall line
        .lineTo(-sizing.L_c, sizing.R_c + sizing.wall_thickness)
        # Back to leftmost point of the combustion chamber.
        .close()
    )

    # Revolve around X axis
    solid = profile.revolve(360, axisStart=(-999, 0, 0), axisEnd=(999, 0, 0))
    assembly = cq.Assembly()
    assembly.add(solid, color=cq.Color(0.5, 0.5, 0.5))  # gray solid

    # Show object
    show_object(assembly)
    return assembly


def main():
    base_params = Parameters(
        R_c=5.61770763 / 2 * 10,
        R_t=1.248379473 / 2 * 10,
        R_e=2.301477106 / 2 * 10,
        Lvp=1 / 3,
        contraction_diameter_ratio=4,
        contract_angle=70,
        nozzle_angle=15,
        L_c=5.836139169 * 10,
        wall_thickness=1,
    )

    print("=== Base Parameters ===")
    print(base_params)
    print("\n=== Sizing ===")
    sizing = calculate_sizing(base_params)
    print(sizing)

    asm = cad(sizing)
    asm.export(
        "rao_sizing.step",
    )
    print("Exported to rao_sizing.step")


main()
