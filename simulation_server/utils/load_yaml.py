import yaml
import pprint


def load_yaml(yaml_file: str)-> dict:
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)
    return data

def deep_merge(a: dict, b: dict ) -> dict:
    """
    Recursively merge dictionary ``b`` into dictionary ``a``.

    For each key in ``b``:
      - If the key does not exist in ``a``, it is added.
      - If the key exists in both ``a`` and ``b`` and both values are dictionaries,
        the values are merged recursively.
      - Otherwise, the value from ``b`` replaces the value in ``a``.

    The merge is performed **in place** on ``a``.

    Parameters
    ----------
    a : dict
        Base dictionary to be updated. This dictionary is mutated in place.
    b : dict
        Dictionary whose values override or extend those in ``a``.

    Returns
    -------
    dict
        The updated dictionary ``a``.

    Notes
    -----
    - Non-dictionary values (e.g., lists, numbers, strings) are replaced, not merged.
    - Lists are not appended or merged by default.
    - No type coercion or validation is performed.
    - Later values always take precedence over earlier ones.

    Examples
    --------
    >>> base = {"a": {"x": 1, "y": 2}}
    >>> override = {"a": {"y": 3, "z": 4}}
    >>> deep_merge(base, override)
    {'a': {'x': 1, 'y': 3, 'z': 4}}
    """
        
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            deep_merge(a[k],v)
        else:
            a[k] = v
    return a

def load_relevant_controls(yaml_files: list[str]):
    """
    Load and aggregate relevant accelerator control definitions from multiple YAML files.

    This function loads a sequence of YAML configuration files, recursively merges their
    contents, and extracts a subset of device control information for supported device
    types. The resulting mapping is keyed by each device's control name and includes
    EPICS PV definitions, metadata, and a lowercase MAD-compatible device name.

    Supported devices and selection criteria:
      - Magnets: devices with metadata type ``"QUAD"``
      - Screens: devices with metadata type ``"PROF"``
      - Transverse cavities: devices with metadata type ``"LCAV"``
      - Beam position monitors: devices with metadata type ``"BPM"``

    Parameters
    ----------
    yaml_files : list[str]
        List of paths to YAML configuration files. Files are loaded in order, and later
        files override or extend earlier ones via a deep merge.

    Returns
    -------
    dict
        Dictionary mapping control names to control definitions. Each entry contains:
          - ``"pvs"``: EPICS PV definitions from ``controls_information["PVs"]``
          - ``"metadata"``: Device metadata dictionary
          - ``"madname"``: Lowercase device name suitable for MAD / lattice usage

    Notes
    -----
    - YAML files are merged using a recursive, last-write-wins strategy.
    - The function assumes a consistent YAML schema for all device entries.
    - Devices not matching the supported metadata types are ignored.
    - No validation is performed beyond key lookups; schema validation should be
      handled upstream (e.g., via Pydantic models).

    Examples
    --------
    >>> controls = load_relevant_controls(["base.yaml", "injector.yaml"])
    >>> controls["QUAD:IN20:121"]["pvs"]
    {...}
    """

    
    data = {}
    for yaml_file in yaml_files:
        contents = load_yaml(yaml_file)
        data = deep_merge(data, contents)

    relevant_controls = {}
    # Process magnets
    for name, info in data.get("magnets", {}).items():
        if info["metadata"]["type"] == "QUAD":
            control_name = info["controls_information"]["control_name"]
            relevant_controls[control_name] = {}
            relevant_controls[control_name]["pvs"] = info["controls_information"]["PVs"]
            relevant_controls[control_name]["metadata"] = info["metadata"]
            relevant_controls[control_name]["madname"] = name.lower()
    # Process screens
    for name, info in data.get("screens", {}).items():
        if info["metadata"]["type"] == "PROF":  # Assuming 'PROF' represents OTR
            control_name = info["controls_information"]["control_name"]
            relevant_controls[control_name] = {}
            relevant_controls[control_name]["pvs"] = info["controls_information"]["PVs"]
            relevant_controls[control_name]["metadata"] = info["metadata"]
            relevant_controls[control_name]["madname"] = name.lower()

    # Process tcav
    for name, info in data.get("tcavs", {}).items():
        if info["metadata"]["type"] == "LCAV":
            control_name = info["controls_information"]["control_name"]
            relevant_controls[control_name] = {}
            relevant_controls[control_name]["pvs"] = info["controls_information"]["PVs"]
            relevant_controls[control_name]["metadata"] = info["metadata"]
            relevant_controls[control_name]["madname"] = name.lower()

    for name, info in data.get("bpms", {}).items():
        if info["metadata"]["type"] == "BPM":
            control_name = info["controls_information"]["control_name"]
            relevant_controls[control_name] = {}
            relevant_controls[control_name]["pvs"] = info["controls_information"]["PVs"]
            relevant_controls[control_name]["metadata"] = info["metadata"]
            relevant_controls[control_name]["madname"] = name.lower()
    return relevant_controls


# TODO: multiarea
