import pprint


def create_pvdb(device: dict, default_params) -> dict:
    pvdb = {}
    # pprint.pprint(default_params)
    for key, device_info in device.items():
        pvs = device_info.get("pvs", {})  # Default to empty dict if 'pvs' is missing

        def get_pv(name: str) -> str:
            return pvs.get(name, f"{key}:missing_{name}")

        if "QUAD" in key:
            device_params = {
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

        elif "OTRS" in key:
            n_row = default_params.get("n_row", 1944)
            n_col = default_params.get("n_col", 1472)
            device_params = {
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
                get_pv("target_control"): {"type": "enum", "enums": ["OUT", "IN"]},
            }

        elif "TCAV" in key:
            device_params= {
                get_pv("amplitude_fbenb"): {"type": "enum", "enums": ["Disable", "Enable"]},
                get_pv("amplitude_fbst"): {
                    "type": "enum",
                    "enums": ["Disable", "Pause", "Feedforward", "Enable"],
                },
                get_pv("phase_fbenb"): {"type": "enum", "enums": ["Disable", "Enable"]},
                get_pv("phase_fbst"): {
                    "type": "enum",
                    "enums": ["Disable", "Pause", "Feedforward", "Enable"],
                },
                get_pv("rf_enable"): {"type": "enum", "enums": ["Disable", "Enable"]},
                get_pv("amplitude"): {
                    "type": "float",
                    "value": 0.0,
                    "prec": 5,
                },
                get_pv("phase"): {
                    "type": "float",
                    "value": 0.0,
                    "prec": 5,
                },
                get_pv("mode_config"): {
                    "type": "enum",
                    "enums": ["Disable", "ACCEL", "STDBY"],
                },
            }


        elif "BPMS" in key:
            device_params = {
                get_pv("tmit"): {"type": "float", "value": 0.0, "prec": 5},
                get_pv("x"): {"type": "float", "value": 0.0, "prec": 5},
                get_pv("y"): {"type": "float", "value": 0.0, "prec": 5},
            }

        #check in the key had missing pv values if so omit it since lcls_elements.csv did not agree with yaml
        if any('missing' in pkey for pkey in device_params.keys()):
            continue

        # Create DRVL/DRVH/HOPR/LOPR PVs, since pcaspy doesn't do that for us.
        new_pvs = {}
        for k, v in device_params.items():
            if "type" in v and v["type"] not in ["float", "int"]:
                continue
            for parm, val in v.items():
                if parm in ["type", "value"]:
                    continue
                new_pvs[f"{k}.{parm.upper()}"] = {"type": "float", "value": val}
        device_params.update(new_pvs)

        #update pvdb with device pvs
        pvdb.update(device_params)

    return pvdb


# TODO: make defaults more robust
# TODO: ensure matching defaults are also passed to beamline.py correctly
# TODO: setup multiarea create_pvdb
