from pcaspy import Driver, SimpleServer
from cheetah.particles import ParticleBeam
from cheetah.accelerator import Segment, Screen
import numpy as np
import torch
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, kmod_to_bdes
from scipy.stats import cauchy
import pprint
import math
from p4p.server.thread import SharedPV
from p4p.nt import NTScalar, NTNDArray, NTEnum
import p4p
from typing import Dict, Callable, Any

class SimServer(SimpleServer):
    """
    Subclass of pcaspy.SimpleServer that also serves PVs via PVA
    """

    PV_ASSOC = {
        'HOPR': 'display.limitHigh',
        'LOPR': 'display.limitLow',
        'DRVH': 'control.limitHigh',
        'DRVL': 'control.limitLow',
        'DESC': 'display.description',
        'EGU': 'display.units',
    }

    DB_TO_PV = {
        'unit': 'EGU',
        'value': 'VAL',
        'lopr': 'LOPR',
        'hopr': 'HOPR',
        'prec': 'PREC',
        'drvh': 'DRVH',
        'drvl': 'DRVL'
    }

    class UpdateHandler:
        """
        Handler for PV writes. Invokes the update callback to update the model outputs.
        This also maintains an association between a PV and a subfield in the parent PV. For example,
        if we have a .LOPR pv, that also needs to update the display.limitLow field in the parent.
        """
        def __init__(self, server, parent: SharedPV|None=None, subfield: str|None=None):
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

    def __init__(self, pvdb: dict, prefix: str = ''):
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

        # Create PVA PVs
        for k, v in pvdb.items():
            if k.rfind('.') != -1:
                continue
            self._pva.update(self._build_pv(f'{prefix}{k}', v))

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
            return 'i'
        elif isinstance(t, float):
            return 'd'
        elif isinstance(t, bool):
            return '?'
        elif isinstance(t, str):
            return 's'
        else:
            raise Exception(f'Unsupported type {type(t)}')

    def _db_to_pv(self, name: str) -> str:
        """Convert pvdb field name to real EPICS field name"""
        try:
            return self.DB_TO_PV[name]
        except:
            raise ValueError(f'Unknown field name {name}, please add it to DB_TO_PV!')

    def _pv_assoc(self, field: str) -> str|None:
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
        if not 'type' in desc:
            desc['type'] = 'float'

        is_image = False
        match desc['type']:
            case 'enum':
                nt = NTEnum(control=True, display=True, valueAlarm=True)
                default = {
                    'index': desc['value'] if 'value' in desc else 0,
                    'choices': desc['enums']
                }
            case 'int':
                nt = NTScalar('i', control=True, display=True, valueAlarm=True)
                default = desc['value'] if 'value' in desc else 0
            case 'float':
                # If we have count, it's actually an array (image)
                if 'count' in desc and 'n_col' in desc:
                    default = np.zeros((desc['n_col'], desc['n_row']), dtype=float)
                    nt = NTNDArray()
                    is_image=True
                else:
                    nt = NTScalar('d', control=True, display=True, valueAlarm=True)
                    default = float(desc['value']) if 'value' in desc else 0.0
            case _:
                raise Exception(f'Unhandled type "{desc["type"]}"')

        # Special control fields
        controls = ['enums', 'type', 'value', 'count', 'n_col', 'n_row']

        # Add value field
        val_pv = SharedPV(
            nt=nt,
            initial=default,
            handler=SimServer.UpdateHandler(self),
        )
        r[f'{name}.VAL'] = val_pv
        r[f'{name}'] = val_pv

        # Get a Value out of SharedPV
        if desc['type'] != 'enum' and not is_image:
            cur = nt.wrap(val_pv.current())
        else:
            cur = None

        # Build generic fields
        for k, v in desc.items():
            if k in controls:
                continue # Skip special values

            field = self._db_to_pv(k.lower())

            # Determine any association with the "parent" (value) PV
            sub = self._pv_assoc(k)
            par_pv = val_pv if sub else None

            # Build a PV for each field
            r[f'{name}.{k.upper()}'] = SharedPV(
                nt=NTScalar(self._type_desc(v)),
                initial=v,
                handler=SimServer.UpdateHandler(self, parent=par_pv, subfield=sub)
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
    def __init__(self,
                 server: SimServer,
                 screen: str,
                 devices: dict,
                 design_incoming_beam:dict = None,
                 particle_beam: ParticleBeam = None,
                 lattice_file: str = None,
                 beamline: Segment = None,
                 enum_init_values: dict = None):
        super().__init__()

        self.server = server
        self.devices = devices
        #pprint.pprint(devices)
        '''
            'OTRS:DIAG0:525': {'madname': 'otrdg04',
                    'metadata': {'area': 'DIAG0',
                                 'beam_path': ['SC_DIAG0'],
                                 'sum_l_meters': 61.871,
                                 'type': 'PROF'},
                    'pvs': {'image': 'OTRS:DIAG0:525:Image:ArrayData',
                            'n_bits': 'OTRS:DIAG0:525:N_OF_BITS',
                            'n_col': 'OTRS:DIAG0:525:Image:ArraySize1_RBV',
                            'n_row': 'OTRS:DIAG0:525:Image:ArraySize0_RBV',
                            'pneumatic': 'OTRS:DIAG0:525:PNEUMATIC',
                            'ref_rate': 'OTRS:DIAG0:525:ArrayRate_RBV',
                            'ref_rate_vme': 'OTRS:DIAG0:525:FRAME_RATE',
                            'resolution': 'OTRS:DIAG0:525:RESOLUTION',
                            'sys_type': 'OTRS:DIAG0:525:SYS_TYPE'}},
            'QUAD:DIAG0:190': {'madname': 'qdg001',
                    'metadata': {'area': 'DIAG0',
                                 'beam_path': ['SC_DIAG0'],
                                 'l_eff': 0.197,
                                 'sum_l_meters': 46.232,
                                 'type': 'QUAD'},
                    'pvs': {'bact': 'QUAD:DIAG0:190:BACT',
                            'bcon': 'QUAD:DIAG0:190:BCON',
                            'bctrl': 'QUAD:DIAG0:190:BCTRL',
                            'bdes': 'QUAD:DIAG0:190:BDES',
                            'bmax': 'QUAD:DIAG0:190:BMAX',
                            'bmin': 'QUAD:DIAG0:190:BMIN',
                            'ctrl': 'QUAD:DIAG0:190:CTRL'}},
            'TCAV:DIAG0:11': {'madname': 'tcxdg0',
                   'metadata': {'area': 'DIAG0',
                                'beam_path': ['SC_DIAG0'],
                                'l_eff': 0.8,
                                'rf_freq': 2856,
                                'sum_l_meters': 53.313,
                                'type': 'LCAV'},
                   'pvs': {'amp_fbenb': 'TCAV:DIAG0:11:AFBENB',
                           'amp_fbst': 'TCAV:DIAG0:11:AFBST',
                           'amp_set': 'TCAV:DIAG0:11:AREQ',
                           'mode_config': 'TCAV:DIAG0:11:MODECFG',
                           'phase_fbenb': 'TCAV:DIAG0:11:PFBENB',
                           'phase_fbst': 'TCAV:DIAG0:11:PFBST',
                           'phase_set': 'TCAV:DIAG0:11:PREQ',
                           'rf_enable': 'TCAV:DIAG0:11:RF_ENABLE'}}}
        '''
        self.screen = screen

        self._particle_beam = particle_beam
        self._design_incoming_beam = design_incoming_beam
        self._beamline = beamline
        self._lattice_file = lattice_file

        self.set_defaults_for_ctrl(0)
        self.set_defaults_for_pneumatic()

        # Do an initial evaluation with default values
        self._update_all_outputs()
        self.server.set_update_callback(self._on_update)

    def _update_all_outputs(self):
        """Updates all model outputs after an input was written to"""
        for k in self.server.pva_pvs.keys():
            # Skip PVs that have a field suffix, we only care about the 'main' PV
            if '.' in k:
                continue
            try:
                self.read(k)
            except:
                pass

    def _on_update(self, reason: str | None, value):
        """Updates the model outputs with new values, and updates PVA PVs"""
        self.write(reason, value)
        self._update_all_outputs()

    def set_param(self, reason, value):
        self.setParam(reason, value)
        self.server.set_pv(reason, value)

    def set_defaults(self, enum_init_values):
        for pv, init_value in enum_init_values.items():
            self.set_param(pv, init_value)
    
    def set_defaults_for_ctrl(self,default_value: int )->None:
        """Sets default quad ctrl value to ready state"""
        keys = [key for key in self.devices]
        for key in keys:
            if 'QUAD' in key:
                ctrl_pv = key + ":CTRL"
                self.set_param(ctrl_pv, default_value)

    def set_defaults_for_pneumatic(self):
        screens = { element.name: element.is_active for element
                   in self.sim_beamline.elements if isinstance(element,Screen)
        }
        pprint.pprint(screens)

        for screen in screens: 
            name = self.madname_to_control(screen)
            position = 1 if screens[screen] else 0
            print(f"{name} : {position}")
            pv = name + ":PNEUMATIC"
            self.set_param(pv , position)
            self.move_screen(name, screens[screen])

    def madname_to_control(self,madname):
        for name in self.devices:
            if self.devices[name]["madname"] == madname:
                return name

    @property
    def sim_beam(self) -> ParticleBeam:
        """Return the simulated beam, initializing if necessary."""
        if not hasattr(self, "_sim_beam") or hasattr(self,"_sim_beam") and self._sim_beam is None:
            if self._particle_beam:
                self._sim_beam = self._particle_beam
            elif self._design_incoming_beam:
                self._sim_beam = ParticleBeam.from_openpmd_file(**self._design_incoming_beam)
                self._sim_beam.particle_charges = torch.tensor(1.0)
            else:
                raise ValueError("Provide either a ParticleBeam instance or a beam configuration dictionary.")
        return self._sim_beam
    
    @sim_beam.setter
    def sim_beam(self,beam: ParticleBeam | None):
        """Sets sim_beam used by read and write functions,
        if set to None it will re-initialize to default value"""
        if not isinstance(beam, ParticleBeam):
            beam = None 
        self._sim_beam = beam

    @property
    def sim_beamline(self) -> Segment:
        """Return the beamline, initializing if necessary."""
        if not hasattr(self, "_sim_beamline") or hasattr(self,"_sim_beamline") and self._sim_beamline is None:
            if self._beamline:
                self._sim_beamline = self._beamline
            elif self._lattice_file:
                print(self._lattice_file)
                self._sim_beamline = Segment.from_lattice_json(self._lattice_file)
                self._sim_beamline.track(self.sim_beam)
            else:
                raise ValueError("Provide either a lattice file or a Segment instance.")
        return self._sim_beamline
    
    @sim_beamline.setter
    def sim_beamline(self,beamline: Segment | None):
        """Sets sim_beamline used by read and write functions,
        if set to None it will re-initialize to default value"""
        if not isinstance(beamline, Segment):
            beamline = None 
        self._sim_beamline = beamline

    @property
    def emittance_x(self) -> float:
        """Retrieve the horizontal beam emittance."""
        return self.sim_beam.emittance_x.item()

    @property
    def emittance_y(self) -> float:
        """Retrieve the vertical beam emittance."""
        return self.sim_beam.emittance_y.item()

    def get_madname(self, control_name):
        if control_name in self.devices:
            madname = self.devices[control_name]["madname"]
            return madname
        return None
    
    def reset_sim(self):
        """Resets sim_beam and sim_beamline to original state"""
        print('Resetting simulation')
        self.sim_beam = None
        self.sim_beamline = None


    def set_quad_value(self, quad_name: str, quad_value: float) -> None:
        """ Takes quad ctrl name and the k1 strength if the quad is in beamline"""
        names = [element.name for element in self.sim_beamline.elements]
        if quad_name in names:
            index_num = names.index(quad_name)
            length = (self.sim_beamline.elements[index_num].length).item()
            energy = self.sim_beam.energy.item()
            kmod = bdes_to_kmod(e_tot=energy, effective_length=length, bdes = quad_value)
            self.sim_beamline.elements[index_num].k1 = torch.tensor(kmod)
            print(f"""Quad in segment with name {quad_name}
                   set to kmod {kmod} with quad value {quad_value}""")
            
    def get_quad_value(self, quad_name: str)-> float:
        """Retrieve quadrupole strength from the simulation beamline."""
        names = [element.name for element in self.sim_beamline.elements]
        if quad_name in names:
            index_num = names.index(quad_name)
            kmod = self.sim_beamline.elements[index_num].k1.item()
            length = self.sim_beamline.elements[index_num].length.item()
            energy = self.sim_beam.energy.item()
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(energy)
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(type(energy))
            quad_value = kmod_to_bdes(e_tot= energy, effective_length = length, k = kmod)
            print(f"kmod is {kmod} with quad_value {quad_value}")
        else:
            print(f"""Warning {quad_name} not in Segment""")
            quad_value = 0
        return quad_value
    
    def set_tcav_amplitude(self, tcav_name, megavolts_amplitude):
        """ Set transverse cavity strength of simulation beamline takes Mega Volts and sets in Volts"""
        names = [element.name for element in self.sim_beamline.elements]
        if tcav_name in names:
            index_num = names.index(tcav_name)
            self.sim_beamline.elements[index_num].voltage = torch.tensor(megavolts_amplitude*1e6)
            print(f"""TCAV in segment with name {tcav_name}
                   set to {megavolts_amplitude*1e6 } volts""")
            
    def get_tcav_amplitude(self, tcav_name):
        """Retrieve transverse cavity strength (MV) from the simulation beamline."""
        names = [element.name for element in self.sim_beamline.elements]
        if tcav_name in names:
            index_num = names.index(tcav_name)
            voltage_amplitude = self.sim_beamline.elements[index_num].voltage.item()
            mega_voltage_amplitude = (voltage_amplitude/1e6)
            print(f"Voltage is is {mega_voltage_amplitude}")
        else:
            print(f"""Warning {tcav_name} not in Segment""")
            mega_voltage_amplitude = 0
        return mega_voltage_amplitude

    def set_tcav_phase(self, tcav_name, phase_in_degrees):
        """ Set the phase of simulation beamline transverse cavity"""
        names = [element.name for element in self.sim_beamline.elements]
        if tcav_name in names:
            index_num = names.index(tcav_name)
            phase_in_radians = phase_in_degrees * math.pi/180
            print(f'phase in radians {phase_in_radians}')
            self.sim_beamline.elements[index_num].phase= torch.tensor(phase_in_radians)
            print(f"""TCAV in segment with name {tcav_name}
                   set to {phase_in_degrees } degrees""")
            
    def get_tcav_phase(self, tcav_name):
        """Retrieve the phase of the transverse cavity in degrees from the simulation beamline."""
        names = [element.name for element in self.sim_beamline.elements]
        if tcav_name in names:
            index_num = names.index(tcav_name)
            phase_in_radians = self.sim_beamline.elements[index_num].phase.item()
            phase_in_degrees = phase_in_radians * 180 / math.pi
            print(f"Phase in degrees is {phase_in_degrees}")
        else:
            print(f"""Warning {tcav_name} not in Segment""")
            phase_in_degrees = 0.00
        return phase_in_degrees

    def get_screen_distribution(self, screen_name: str)-> torch.Tensor:
        """Retrieves image from simulation beamline and adds noise, has 
        a bug that the first time is called is not addding noise"""
        self.sim_beamline.track(self.sim_beam)
        names = [element.name for element in self.sim_beamline.elements]
        if screen_name in names:
            index_num = names.index(screen_name)
            image = self.sim_beamline.elements[index_num].reading
            #noise_std = 0.2 * (np.max(image) + .0001)
            #image += np.abs(np.random.normal(loc=0, scale= noise_std , size=image.shape))
            return image
        else: 
            print(f' else in screen probably returning none')
  
    def check_screen(self, screen_name):
        names = [element.name for element in self.sim_beamline.elements]
        if screen_name in names:
            index_num = names.index(screen_name)
            is_active_position = self.sim_beamline.elements[index_num].is_active
            print(f"screen is in active position: {is_active_position}")
            return 1 if is_active_position else 0
        else:
            print(f"screen device not found in simulated accelerator")
            return "OUT"
        
    def move_screen(self, screen_name: str, position:str) -> None:
        """Moves the position of the associated screen"""
        names = [element.name for element in self.sim_beamline.elements]
        if screen_name in names:
            index_num = names.index(screen_name)
            is_active_position = position == "IN"
            self.sim_beamline.elements[index_num].is_active = is_active_position
            print(f"set screen to position: {self.sim_beamline.elements[index_num].is_active}")
    

    def read(self, reason):
        #TODO: need logic for which screen is in and out, maybe if self.screen is out and other screen is in change
        # self.screen

        # For non-simulated PVs, read the value directly
        if reason.rfind('.') != -1:
            return self.getParam(reason)

        print(f' in read with {reason}')
        if 'Image:ArrayData' in reason and reason.rsplit(':',2)[0] == self.screen:
            print('reading screen')
            madname = self.devices[self.screen]["madname"]
            image_data = self.get_screen_distribution(screen_name = madname)
            value = image_data.flatten().tolist()
        elif 'PNEUMATIC' in reason:
            madname = self.devices[self.screen]["madname"]           
            value = self.check_screen(madname)
            print(value)
        elif 'QUAD' in reason and 'BCTRL' in reason or 'BACT' in reason:
            quad_name = reason.rsplit(':',1)[0]
            madname = self.devices[quad_name]["madname"]
            value = self.get_quad_value(madname)
        #can concat tcav stuff into just getter setters for both amp and phase or keep them separate
        elif 'TCAV' in reason and 'AREQ' in reason:
            print('reading areq')
            tcav_name = reason.rsplit(':',1)[0]
            madname = self.devices[tcav_name]["madname"]
            value = self.get_tcav_amplitude(madname)
        elif 'TCAV' in reason and 'PREQ' in reason:
            print('reading preq')
            tcav_name = reason.rsplit(':',1)[0]
            madname = self.devices[tcav_name]["madname"]
            value = self.get_tcav_phase(madname)
        elif 'VIRT:BEAM:EMITTANCES' == reason:
            value = [self.sim_beam.emittance_x,self.sim_beam.emittance_y]
        elif 'VIRT:BEAM:MU:XY' == reason:
            value = [self.sim_beam.mu_x,self.sim_beam.mu_y]
        elif 'VIRT:BEAM:SIGMA:XY' == reason:
            value = [self.sim_beam.sigma_x,self.sim_beam.sigma_y]
        else:
            value = self.getParam(reason)

        # Post PVA changes
        self.server.set_pv(reason, value)
        return value

    def write(self, reason, value):
        if 'QUAD' in reason and 'BCTRL' in reason:
            quad_name = reason.rsplit(':',1)[0]
            madname = self.devices[quad_name]["madname"]
            self.set_quad_value(madname,value)
        elif 'QUAD' in reason and 'BACT' in reason:
            pass
        elif 'QUAD' in reason:
            self.set_param(reason,value)
        elif 'PNEUMATIC' in reason:
            screen = reason.rsplit(':',1)[0]
            madname = self.devices[screen]["madname"]
            position = self.move_screen(madname)
        elif 'OTRS' in reason and 'PNEUMATIC' not in reason:
            print(f"""Write to OTRS pvs is disabled,
                  failed to write to {reason}""")
        elif 'TCAV' in reason and 'AREQ' in reason:
            tcav_name = reason.rsplit(':',1)[0]
            madname = self.devices[tcav_name]["madname"]
            self.set_tcav_amplitude(madname,value)
        elif 'TCAV' in reason and 'PREQ' in reason:
            tcav_name = reason.rsplit(':',1)[0]
            madname = self.devices[tcav_name]["madname"]
            self.set_tcav_phase(madname,value)
        elif 'VIRT:BEAM:RESET_SIM' == reason:
            self.reset_sim()
        self._update_all_outputs()


#TODO: add functionality to pop screens in and out
