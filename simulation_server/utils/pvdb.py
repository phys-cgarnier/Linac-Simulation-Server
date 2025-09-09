import pprint


def create_pvdb(device: dict, **default_params) -> dict:
    pvdb = {}
    # pprint.pprint(default_params)
    for key, device_info in device.items():
        pvs = device_info.get("pvs", {})  # Default to empty dict if 'pvs' is missing

        def get_pv(name: str) -> str:
            return pvs.get(name, f"{key}:missing_{name}")

        if "QUAD" in key:
            quad_params = {
                get_pv("bact"): {
                    "type": "float",
                    "value": 0.0,
                    "prec": 5,
                    "hopr": 20,
                    "lopr": -20,
                    "drvh": 20,
                    "drvl": -20,
                },
                get_pv("bctrl"): {
                    "type": "float",
                    "value": 0.0,
                    "prec": 5,
                    "hopr": 20,
                    "lopr": -20,
                    "drvh": 20,
                    "drvl": -20,
                },
                get_pv("bmax"): {"type": "float", "value": 20.0, "prec": 5},
                get_pv("bmin"): {"type": "float", "value": -20.0, "prec": 5},
                get_pv("bdes"): {
                    "type": "float",
                    "value": 0.0,
                    "prec": 5,
                    "hopr": 20,
                    "lopr": -20,
                    "drvh": 20,
                    "drvl": -20,
                },
                get_pv("bcon"): {
                    "type": "float",
                    "value": 0.0,
                    "prec": 5,
                    "hopr": 20,
                    "lopr": -20,
                    "drvh": 20,
                    "drvl": -20,
                },
                get_pv("ctrl"): {
                    "type": "enum",
                    "enums": ["Ready", "TRIM", "Perturb", "MORE_IF_NEEDED"],
                },
            }

            # Create DRVL/DRVH/HOPR/LOPR PVs, since pcaspy doesn't do that for us.
            new_pvs = {}
            for k, v in quad_params.items():
                for parm, val in v.items():
                    if parm in ["type", "value"]:
                        continue
                    new_pvs[f"{k}.{parm.upper()}"] = {"type": "float", "value": val}
            quad_params.update(new_pvs)

            pvdb.update(quad_params)

        elif "OTRS" in key:
            n_row = default_params.get("n_row", 1944)
            n_col = default_params.get("n_col", 1472)
            screen_params = {
                get_pv("image"): {
                    "type": "float",
                    "count": n_row * n_col,
                    "n_row": n_row,
                    "n_col": n_col,
                },
                get_pv("n_row"): {"type": "int", "value": n_row},
                get_pv("n_col"): {"type": "int", "value": n_col},
                get_pv("resolution"): {
                    "value": default_params.get("resolution", 23.33),
                    "unit": "um/px",
                },
                get_pv("pneumatic"): {"type": "enum", "enums": ["OUT", "IN"]},
            }
            # need to change screen class...... pneumatic is an enum not a thingy
            pvdb.update(screen_params)

        elif "TCAV" in key:
            tcav_params = {
                get_pv("amp_fbenb"): {"type": "enum", "enums": ["Disable", "Enable"]},
                get_pv("amp_fbst"): {
                    "type": "enum",
                    "enums": ["Disable", "Pause", "Feedforward", "Enable"],
                },
                get_pv("phase_fbenb"): {"type": "enum", "enums": ["Disable", "Enable"]},
                get_pv("phase_fbst"): {
                    "type": "enum",
                    "enums": ["Disable", "Pause", "Feedforward", "Enable"],
                },
                get_pv("rf_enable"): {"type": "enum", "enums": ["Disable", "Enable"]},
                get_pv("amp_set"): {
                    "value": 0.0,
                    "prec": 5,
                },
                get_pv("phase_set"): {
                    "value": 0.0,
                    "prec": 5,
                },
                get_pv("mode_config"): {
                    "type": "enum",
                    "enums": ["Disable", "ACCEL", "STDBY"],
                },
            }
            pvdb.update(tcav_params)

        elif "BPMS" in key:
            bpms_params = {
                get_pv("tmit"): {"type": "float", "value": 0.0, "prec": 5},
                get_pv("x"): {"type": "float", "value": 0.0, "prec": 5},
                get_pv("y"): {"type": "float", "value": 0.0, "prec": 5},
            }
            pvdb.update(bpms_params)

    return pvdb


# TODO: make defaults more robust
# TODO: ensure matching defaults are also passed to beamline.py correctly
# TODO: setup multiarea create_pvdb
