from pcaspy import Driver, SimpleServer
from cheetah.particles import ParticleBeam
from cheetah.accelerator import Segment, Screen
import numpy as np
import torch
from scipy.stats import cauchy
import pprint
import math
from p4p.server.thread import SharedPV
from p4p.nt import NTScalar, NTNDArray, NTEnum
import p4p
from typing import Dict, Callable, Any
from virtual_accelerator.virtual_accelerator import VirtualAccelerator


class SimServer(SimpleServer):
    """
    Subclass of pcaspy.SimpleServer that also serves PVs via PVA
    """

    PV_ASSOC = {
        "HOPR": "display.limitHigh",
        "LOPR": "display.limitLow",
        "DRVH": "control.limitHigh",
        "DRVL": "control.limitLow",
        "DESC": "display.description",
        "EGU": "display.units",
    }

    DB_TO_PV = {
        "unit": "EGU",
        "value": "VAL",
        "lopr": "LOPR",
        "hopr": "HOPR",
        "prec": "PREC",
        "drvh": "DRVH",
        "drvl": "DRVL",
    }

    class UpdateHandler:
        """
        Handler for PV writes. Invokes the update callback to update the model outputs.
        This also maintains an association between a PV and a subfield in the parent PV. For example,
        if we have a .LOPR pv, that also needs to update the display.limitLow field in the parent.
        """

        def __init__(
            self, server, parent: SharedPV | None = None, subfield: str | None = None
        ):
            self.server = server
            self._parent = parent
            self._subfield = subfield

        def put(self, pv, op):
            pv.post(op.value())
            op.done()

            # Update the parent PV's subfield too
            if self._parent:
                val = self._parent._wrap(self._parent.current())
                val[self._subfield] = op.value()
                self._parent.post(val)

            if self.server._callback:
                self.server._callback(op.name(), op.value())

    def __init__(self, pvdb: dict, prefix: str = ""):
        """
        Parameters
        ----------
        pvdb : dict
            Dict describing all records and their fields
        prefix : str
            PV name prefix
        """
        self._pva: Dict[str, SharedPV] = {}
        self._callback = None
        self._db = pvdb

        # Create CA PVs
        self.createPV(prefix, pvdb)

        ""
        # Create PVA PVs
        for k, v in pvdb.items():
            if k.rfind(".") != -1:
                continue
            self._pva.update(self._build_pv(f"{prefix}{k}", v))

        super().__init__()

    def set_update_callback(self, callable: Callable[[str, Any], None]):
        """
        Sets the callback to be called every 0.1s in the processing loop (corresponds to fastest EPICS processing time)

        Parameters
        ----------
        callable : Callable
            Method to use, or none to clear
        """
        self._callback = callable

    def run(self):
        self._server = p4p.server.Server(providers=[self._pva])
        while True:
            self.process(0.1)

    @property
    def pva_pvs(self) -> Dict[str, SharedPV]:
        """Returns list of PVs served by PVA"""
        return self._pva

    @property
    def pvdb(self) -> dict:
        """Returns the PV database"""
        return self.pvdb

    def _type_desc(self, t) -> str:
        """
        Returns the type description of t for use with NTScalar and friends

        Parameters
        ----------
        t : Any
            object to describe

        Returns
        -------
        str
            Type code for use with NTScalar
        """
        if isinstance(t, int):
            return "i"
        elif isinstance(t, float):
            return "d"
        elif isinstance(t, bool):
            return "?"
        elif isinstance(t, str):
            return "s"
        else:
            raise Exception(f"Unsupported type {type(t)}")

    def _db_to_pv(self, name: str) -> str:
        """Convert pvdb field name to real EPICS field name"""
        try:
            return self.DB_TO_PV[name]
        except:
            raise ValueError(f"Unknown field name {name}, please add it to DB_TO_PV!")

    def _pv_assoc(self, field: str) -> str | None:
        """Returns the field association with a NT field in the parent, if any"""
        try:
            return self.PV_ASSOC[field.upper()]
        except:
            return None

    def _build_pv(self, name: str, desc: dict) -> Dict[str, SharedPV]:
        """
        Builds several PVs to form the record described by 'desc'

        Parameters
        ----------
        name : str
            PV base name
        desc : dict
            Description ordinarily passed to pcaspy

        Returns
        -------
        Dict[str, SharedPV]
            Dict mapping PV name -> SharedPV instance
        """
        r = {}
        if not "type" in desc:
            desc["type"] = "float"

        is_image = False
        match desc["type"]:
            case "enum":
                nt = NTEnum(control=True, display=True, valueAlarm=True)
                default = {
                    "index": desc["value"] if "value" in desc else 0,
                    "choices": desc["enums"],
                }
            case "int":
                nt = NTScalar("i", control=True, display=True, valueAlarm=True)
                default = desc["value"] if "value" in desc else 0
            case "float":
                # If we have count, it's actually an array (image)
                if "count" in desc and "n_col" in desc:
                    default = np.zeros((desc["n_col"], desc["n_row"]), dtype=float)
                    nt = NTNDArray()
                    is_image = True
                else:
                    nt = NTScalar("d", control=True, display=True, valueAlarm=True)
                    default = float(desc["value"]) if "value" in desc else 0.0
            case _:
                raise Exception(f'Unhandled type "{desc["type"]}"')

        # Special control fields
        controls = ["enums", "type", "value", "count", "n_col", "n_row"]

        # Add value field
        val_pv = SharedPV(
            nt=nt,
            initial=default,
            handler=SimServer.UpdateHandler(self),
        )
        r[f"{name}.VAL"] = val_pv
        r[f"{name}"] = val_pv

        # Get a Value out of SharedPV
        if desc["type"] != "enum" and not is_image:
            cur = nt.wrap(val_pv.current())
        else:
            cur = None

        # Build generic fields
        for k, v in desc.items():
            if k in controls:
                continue  # Skip special values

            field = self._db_to_pv(k.lower())

            # Determine any association with the "parent" (value) PV
            sub = self._pv_assoc(k)
            par_pv = val_pv if sub else None

            # Build a PV for each field
            r[f"{name}.{k.upper()}"] = SharedPV(
                nt=NTScalar(self._type_desc(v)),
                initial=v,
                handler=SimServer.UpdateHandler(self, parent=par_pv, subfield=sub),
            )

            if sub and cur:
                cur[sub] = v

        # Post the "real" value to the value PV, including all fields
        if cur:
            val_pv.post(cur)

        return r

    def set_pv(self, name: str, value):
        """
        Update a PVA PV with a new value

        Parameters
        ----------
        name : str
            Full name of PV including field
        value : Any
            Value to set
        """
        self._pva[name].post(value)


# TODO: set defaults for all tcav enum pvs
#
class SimDriver(Driver):
    def __init__(
        self,
        server: SimServer,
        devices: dict,
        mapping_file: str,
        particle_beam: ParticleBeam = None,
        lattice_file: str = None,
        monitor_overview: bool = False
    ):
        super().__init__()
        self.virtual_accelerator = VirtualAccelerator(
            lattice_file=lattice_file,
            initial_beam_distribution=particle_beam,
            mapping_file=mapping_file,
            monitor_overview=monitor_overview,
        )
        self.server = server
        self.devices = devices
        # pprint.pprint(devices)

        # get list of pvs that should be updated every time we write to a PV
        self.measurement_pvs = self.get_measurement_pvs()

        # initialize ALL pvs with values
        key_list = list(self.server.pva_pvs.keys())
        key_list = [k for k in key_list if not "." in k]  # filter out keys with attributes
        self.update_pvs(key_list)

    def get_measurement_pvs(self):
        """ Get a list of PVs that should be updated every time we write to a PV """
        key_list = list(self.server.pva_pvs.keys())

        # filter out keys with attributes
        key_list = [k for k in key_list if not "." in k]

        # filter out keys that will not be updated
        ignore_flags = [
            "BMAX", "BMIN", "BDES", "BCON", "ArraySize0_RBV", "ArraySize1_RBV",
            "RESOLUTION", "ENB", "BST", "MODE", "ENABLE", "REQ", "CTRL", "TMIT"
        ]
        key_list = [k for k in key_list if not any(flag in k for flag in ignore_flags)]

        return key_list

    def update_pvs(self, pv_list):
        # NOTE: Slowing down this function will cause timeout issues when accessing PV values
        print("Updating PVs...")
        # print("Measurement PVs: ", self.measurement_pvs)
        # read all the pvs
        values = self.virtual_accelerator.get_pvs(pv_list)
        for name,val in values.items():
            # Post PVA changes
            if not "Array" in name:
                print(f"Setting {name} to {val}")
            self.server.set_pv(name, val)   

    def read(self, reason):
        try:
            print("reading " + reason)
            value =  self.virtual_accelerator.get_pvs([reason])[reason]
            self.server.set_pv(reason, value)
        except ValueError as e:
            print(e)

    def write(self, reason, value):
        try:
            self.virtual_accelerator.set_pvs({reason: value})
            self.server.set_pv(reason, value)
            self.update_pvs(self.measurement_pvs)

        except ValueError as e:
            print(e)


# TODO: add functionality to pop screens in and out
