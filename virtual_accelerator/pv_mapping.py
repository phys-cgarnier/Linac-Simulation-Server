import pandas as pd
import torch


class FieldAccessor:
    """
    A class to access and set arbitrary attributes of Cheetah elements when logic
    is more complex than simple attribute access (ie. nested attributes).

    This class is used to map process variable (PV) attributes to Cheetah element attributes.
    It allows both getting and setting values of the attributes by providing a getter and setter function.
    """

    def __init__(self, getter, setter=None):
        self.get = getter
        self.set = setter

    def __call__(self, element, energy, value=None):
        if value is None:
            return self.get(element,energy)
        else:
            if self.set is None:
                raise ValueError("Cannot set value for.")
            self.set(element, energy, value)


def get_magnetic_rigidity(energy):
    """
    Calculate the magnetic rigidity (Bρ) in kG-m given the beam energy in eV.
    """
    return 33.356 * energy / 1e9

# define mappings for different element types 

# -- include conversions for cheetah attributes to SLAC EPICS attributes
QUADRUPOLE_MAPPING = {
    "BCTRL": FieldAccessor(
        lambda e, energy: e.k1 * e.length * get_magnetic_rigidity(energy), 
        lambda e, energy, k1: setattr(e, "k1", k1 / get_magnetic_rigidity(energy) / e.length)
    ),
    "BACT": FieldAccessor(
        lambda e, energy: e.k1 * e.length * get_magnetic_rigidity(energy)
    ),
    "BMAX": FieldAccessor(lambda e, energy: 20.0),
    "BMIN": FieldAccessor(lambda e, energy: -20.0),
    "CTRL": FieldAccessor(lambda e, energy: "Ready"),
    "BCON": FieldAccessor(lambda e, energy: 1.0),
    "BDES": FieldAccessor(lambda e, energy: e.k1 * e.length * get_magnetic_rigidity(energy)),
}

SOLENOID_MAPPING = {
    "BCTRL": FieldAccessor(lambda e, energy: e.k * get_magnetic_rigidity(energy), lambda e, energy, k: setattr(e, "k", k / (2*get_magnetic_rigidity(energy)))),
    "BACT": FieldAccessor(lambda e, energy: e.k * get_magnetic_rigidity(energy))
}

CORRECTOR_MAPPING = {
    "BCTRL": FieldAccessor(lambda e, energy: e.angle * get_magnetic_rigidity(energy), lambda e, energy, a: setattr(e, "angle", a / get_magnetic_rigidity(energy))),
    "BACT": FieldAccessor(lambda e, energy: e.angle * get_magnetic_rigidity(energy))
}

TRANSVERSE_DEFLECTING_CAVITY_MAPPING = {
    "AREQ": "voltage",
    "PREQ": "phase",
}

BPM_MAPPING = {
    "X": FieldAccessor(lambda e, energy: e.reading[0]),
    "Y": FieldAccessor(lambda e, energy: e.reading[1]),
    "XSCDT1H": FieldAccessor(lambda e, energy: e.reading[0]),
    "YSCDT1H": FieldAccessor(lambda e, energy: e.reading[1]),
}

SCREEN_MAPPING = {
    "Image:ArrayData": FieldAccessor(lambda e, energy: e.reading),
    "PNEUMATIC": "is_active",
    "Image:ArraySize1_RBV": FieldAccessor(lambda e, energy: e.resolution[0]),
    "Image:ArraySize0_RBV": FieldAccessor(lambda e, energy: e.resolution[1]),
    "RESOLUTION": FieldAccessor(lambda e, energy: e.pixel_size[0]),
}

MAPPINGS = {
    "Quadrupole": QUADRUPOLE_MAPPING,
    "Solenoid": SOLENOID_MAPPING,
    "HorizontalCorrector": CORRECTOR_MAPPING,
    "VerticalCorrector": CORRECTOR_MAPPING,
    "BPM": BPM_MAPPING,
    "Screen": SCREEN_MAPPING,
    "TransverseDeflectingCavity": TRANSVERSE_DEFLECTING_CAVITY_MAPPING,
}


def access_cheetah_attribute(element, pv_attribute, energy, set_value=None):
    """

    Return or set a Cheetah element attribute based on the PV attribute.
    If `set_value` is provided, it sets the value of the Cheetah attribute.

    Args:
        element (Element): The name of the Cheetah element.
        pv_attribute (str): The process variable attribute to map.
        energy (float): The beam energy in eV.
        set_value (optional): If provided, sets the value of the Cheetah attribute.

    Returns:
        value: The corresponding Cheetah attribute value if `set_value` is None, otherwise sets the value and returns None.
    """

    element_type = type(element).__name__
    if element_type not in MAPPINGS:
        raise ValueError(f"Unsupported element type: {element_type}")

    mapping = MAPPINGS[element_type]
    if pv_attribute not in mapping:
        raise ValueError(
            f"Unsupported PV attribute: {pv_attribute} for element type: {element_type}"
        )

    accessor = mapping[pv_attribute]

    # convert to tensor if the value is a float or int
    if isinstance(set_value, (float, int)):
        set_value = torch.tensor(set_value)

    if isinstance(accessor, str):
        if set_value is None:
            return getattr(element, accessor)
        else:
            setattr(element, accessor, set_value)

    elif isinstance(accessor, FieldAccessor):
        return accessor(element, energy, set_value)


def get_pv_mad_mapping(fname):
    """
    Create a mapping from control system names to element names from a CSV file.

    Args:
        fname (str): Path to the CSV file containing the mapping.

    """
    mapping = (
        pd.read_csv(fname, dtype=str)
        .set_index("Control System Name")["Element"]
        .T.to_dict()
    )
    return mapping
