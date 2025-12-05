import time
from pcaspy import Driver, SimpleServer
from cheetah.particles import ParticleBeam
import numpy as np
from p4p.server.thread import SharedPV
from p4p.nt import NTScalar, NTNDArray, NTEnum
import p4p
from typing import Dict, Callable, Any
from simulation_server.virtual_accelerator import VirtualAccelerator
import threading
from .utils.timer import Timer

class SimServer(SimpleServer):
    """
    Subclass of pcaspy.SimpleServer that also serves PVs via PVA
    """

    # Mapping record field names to NT structure field names
    PV_ASSOC = {
        "HOPR": "display.limitHigh",
        "LOPR": "display.limitLow",
        "DRVH": "control.limitHigh",
        "DRVL": "control.limitLow",
        "DESC": "display.description",
        "EGU": "display.units",
    }

    # Mapping pcas PV attributes to record field names
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
            pv.post(op.value(), timestamp=time.time())
            op.done()

            # Update the parent PV's subfield too
            if self._parent:
                val = self._parent._wrap(self._parent.current())
                val[self._subfield] = op.value()
                self._parent.post(val, timestamp=time.time())

            if self.server._callback:
                self.server._callback(op.name(), op.value())

    def __init__(self, pvdb: dict, prefix: str = "", threading: bool = True):
        """
        Parameters
        ----------
        pvdb : dict
            Dict describing all records and their fields
        prefix : str
            PV name prefix
        threading : bool
            When set to True, enables threading and SIMULATE PV behavior
        """
        self._pva: Dict[str, SharedPV] = {}
        self._callback = None
        self._db = pvdb
        self._threaded = threading

        # Add a PV to indicate both simulation status and to trigger simulation
        self.sim_pv_name = "VIRT:BEAM:SIMULATE"
        self._db[self.sim_pv_name] = {
            "value": 0
        }
        self.sim_timeout_name = "VIRT:BEAM:SIMULATE_TIMEOUT"
        self._db[self.sim_timeout_name] = {
            "value": 0
        }

        # Create CA PVs
        self.createPV(prefix, self._db)

        # Create PVA PVs
        for k, v in self._db.items():
            if k.rfind(".") != -1:
                continue
            self._pva.update(self._build_pv(f"{prefix}{k}", v))

        self.sim_pv = self._pva[self.sim_pv_name]

        super().__init__()

    def set_update_callback(self, callable: Callable[[str, Any], None]):
        """
        Sets the PV update callback. This will be invoked when any PV is written to using PVA

        Parameters
        ----------
        callable : Callable
            Method to use, or none to clear
        """
        self._callback = callable

    def run(self):
        self._server = p4p.server.Server(providers=[self._pva])
        while True:
            self.process(0.001)

    @property
    def threaded(self) -> bool:
        return self._threaded

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

        # Special control fields and status fields
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
            val_pv.post(cur, timestamp=time.time())

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
        self._pva[name].post(value, timestamp=time.time())


class SimDriver(Driver):
    def __init__(
        self, server: SimServer, virtual_accelerator: VirtualAccelerator
    ):
        super().__init__()
        self.virtual_accelerator = virtual_accelerator

        self.server = server

        self.server.set_update_callback(self.write)

        # PV data cache and associated primitives
        self.pv_cache = {}
        self.pv_guard = threading.Lock()
        self.write_guard = threading.Lock()
        self.thread_cond = threading.Condition(self.write_guard)
        self.thread = threading.Thread(target=self._model_update_thread)
        self.new_data = {}
        self.omitted = []

        # Configure for instant simulation by default
        self.timer = Timer(0, self._trigger_sim, periodic=True, manual=True)

        # get list of pvs that should be updated every time we write to a PV
        self.measurement_pvs = self.get_measurement_pvs()

        # init PV cache with all variables (including informational ones)
        key_list = list(self.server.pva_pvs.keys())
        for k in key_list:
            self.pv_cache[k] = self.server.pva_pvs[k].current()

        # Run an initial update of simulated variables
        self.update_cache(self.measurement_pvs, True)

        self.thread.start()
        if self.server.threaded:
            self.timer.start()

    def _trigger_sim(self):
        with self.write_guard:
            self.thread_cond.notify_all()

    def _set_and_simulate(self, new_data: dict):
        """Updates PVs on the model, then updates the PV cache with results"""
        start = time.time()

        for k in new_data.keys():
            if k in self.omitted:
                continue
            try:
                self.virtual_accelerator.set_pvs({k: new_data[k]})
            except AttributeError:
                pass # Added to the omitted list later

        # update PV cache with new values, pump monitors
        self.update_cache(self.measurement_pvs, True)

        print(f"Simulation took {time.time() - start:.3f} seconds")

    def _model_update_thread(self):
        while True:
            # Unlocked by thread_cond.wait()
            self.write_guard.acquire()

            # Wait for a trigger if no additional data is ready (unlocks write_guard)
            if len(self.new_data.keys()) == 0:
                self.thread_cond.wait()

            # Grab updated data
            new_data = self.new_data.copy()
            self.new_data = {}

            # Done with the write guard
            self.write_guard.release()

            print(f'Simulation triggered')

            start = time.time()

            # run simulation
            self._set_and_simulate(new_data)

            # Indicate that we're done simulating
            self.set_cached_value(self.server.sim_pv_name, 0, True)


    def get_measurement_pvs(self):
        """Get a list of PVs that should be updated every time we write to a PV"""
        key_list = list(self.server.pva_pvs.keys())

        # filter out keys with attributes
        key_list = [k for k in key_list if not "." in k]

        # filter out keys that will not be updated
        ignore_flags = [
            "BMAX",
            "BMIN",
            "BDES",
            "BCON",
            "ArraySize0_RBV",
            "ArraySize1_RBV",
            "RESOLUTION",
            "ENB",
            "BST",
            "MODE",
            "ENABLE",
            "SIMULATE",
            "REQ",
            "CTRL",
            "TMIT",
        ]
        key_list = [k for k in key_list if not any(flag in k for flag in ignore_flags)]
        
        return key_list

    def update_cache(self, pv_list: list, post_monitors: bool):
        """
        Updates the PV cache for the list of PVs, optionally updating monitors along the way.
        Locks the PV cache for you.

        Parameters
        ----------
        pv_list : list[str]
            List of PVs to update
        post_monitors : bool
            If true, update PV monitors
        """
        self.pv_guard.acquire()
        for name in pv_list:
            if name in self.omitted:
                continue
            try:
                value = self.virtual_accelerator.get_pvs([name])[name]
            except AttributeError as e:
                # Attributes that error out should be omitted in subsequent runs
                if name not in self.omitted:
                    self.omitted.append(name)
                    print(f'Error getting param "{name}": {e}, do not use {name}')
                continue
            self.pv_cache[name] = value
            if post_monitors:
                self.server.set_pv(name, value)
                self.setParam(name, value)
        if post_monitors:
            self.updatePVs()
        self.pv_guard.release()

    def set_cached_value(self, pv: str, value: Any, post_monitors: bool):
        """
        Sets a value in the PV cache, optionally updating monitors/PVs.
        Locks the PV cache for you.
        """
        self.pv_guard.acquire()
        self.pv_cache[pv] = value

        if post_monitors:
            self.server.set_pv(pv, value)
            self.setParam(pv, value)
            self.updatePV(pv)

        self.pv_guard.release()

    def cached_value(self, reason: str) -> Any|None:
        """
        Fetches the latest value of the PV from the cache

        Parameters
        ----------
        reason : str
            Name of the PV

        Returns
        -------
        Any|None
            Value fetched from cache, or None if it doesn't exist
        """
        with self.pv_guard:
            try:
                value = self.pv_cache[reason]
            except KeyError:
                print(f'{reason} had no entry in the cache: {self.pv_cache}')
                return None
        return value

    def read(self, reason):
        # grab latest value from the cache
        value = self.cached_value(reason)

        try:
            self.setParam(reason, value)
        except Exception as e:
            print(f"Error setting param for {reason}: {e}")

        self.updatePV(reason)
        return value

    def write(self, reason, value):
        """write to a PV, run the simulation, and then update all other PVs"""
        print(f"Writing {value} to {reason}")

        # Update internal values quickly so readbacks dont fail
        self.set_cached_value(reason, value, True)

        # Halt countdown
        self.timer.cancel()

        # Re-run the entire simulation if requested
        if reason == self.server.sim_pv_name:
            with self.write_guard:
                self.thread_cond.notify_all()
            return

        # Adjust simulation timeout
        if reason == self.server.sim_timeout_name:
            self.timer.interval = int(value)
            return

        # Single threaded mode; do all updates immediately
        if not self.server.threaded:
            # Set changed PVs, and update the new values
            self._set_and_simulate({reason: value})
            return

        with self.write_guard:
            # this is sent to the updater thread
            self.new_data[reason] = value

            # Begin simulation timeout period
            self.timer.reset()
