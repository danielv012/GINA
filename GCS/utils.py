def g_to_N(g: float) -> float:
    """
    Convert thrust from grams to Newtons.
    :param g: Thrust in grams.
    :return: Thrust in Newtons.
    """
    return g * 9.81 / 1000  # Convert grams to kg and multiply by gravity (9.81 m/s^2)
