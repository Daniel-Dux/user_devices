############################################################################
#                                                                          #
# ADwinProII/labscript_devices.py                                          #
#                                                                          #
# Copyright 2022, TU Vienna                                                #
#                                                                          #
# Implementation of the ADwin-Pro II for the labscript-suite,              #
# used in the Léonard lab for Experimental Quantum Information.            #
#                                                                          #
# Some parts of the code were adapted from an older implementation         #
# in the labscript-suite:                                                  # 
# https://github.com/labscript-suite/labscript/blob/2.1.0/devices/adwin.py #
#                                                                          #
############################################################################


from labscript import Pseudoclock, PseudoclockDevice, ClockLine, Device, LabscriptError, config, set_passed_properties, compiler
import numpy as np

from . import PROCESSDELAY_T12, PROCESSDELAY_TiCo, CLOCK_T12, CLOCK_TiCo, MAX_EVENTS, MAX_PID_EVENTS, A_IN_BUFFER
from .labscript_devices_ADwin_modules import _ADwinCard,ADwinAI8,ADwinAO8,ADwinDIO32
from .ADwin_utils import ADC

# Notes:
# The ADWin (T12) runs at 1 GHz. The cycle time should be specified in hardware programming in units of this clock speed.
# Subsequently, instruction timing must be specified in units of cycles.

# Voltages are specified with a 16 bit unsigned integer, mapping the range [-10,10) volts.
# There are 32 digital outputs on a card (DIO-32-TiCo)
# There are 8 analog outputs on a card (AOut-8/16)
# There are 8 analog inputs on a card (AIn-F-8/16)


class _ADwin_CPU(Pseudoclock):
    """Dummy Class to create the pseudoclock for a ADwin processor with a given PROCESSDELAY"""
    CPU_clock = None

    def __init__(self, name, pseudoclock_device, connection, PROCESSDELAY, **kwargs):
        pseudoclock_device.clock_limit = self.CPU_clock / PROCESSDELAY
        pseudoclock_device.clock_resolution = 1 / pseudoclock_device.clock_limit
        super().__init__(name, pseudoclock_device, connection, **kwargs)

    def add_device(self, device):
        if self.child_devices or not isinstance(device,ClockLine):
            raise LabscriptError("The ADwin CPU only supports one clockline, which is generated automatically.")
        Pseudoclock.add_device(self, device)
        self.clockline = device
        self.clockline.allowed_children = [_ADwinCard]



class _ADwin_CPU_T12(_ADwin_CPU):
    """Class for a ADwin T12 PseudoClock"""
    description = "ADwin-Pro 2 T12 Processor "
    CPU_clock = CLOCK_T12


    
class _ADwin_CPU_TiCo(_ADwin_CPU):
    """Class for a ADwin TiCo1 PseudoClock"""
    description = "TiCo1 Processor."
    CPU_clock = CLOCK_TiCo

    def collect_change_times(self, all_outputs, outputs_by_clockline):
        # Overwriting the default Pseudoclock.collect_change_times,
        # because I had floating point errors of the 'dt' variables.
        # Also simplified the original because there is only 1 clockline.

        all_change_times = []
        for output in all_outputs:
            output_change_times = output.get_change_times()
            all_change_times.extend(output_change_times)

        # Change to a set and back to get rid of duplicates:
        if not all_change_times:
            all_change_times.append(0)
        all_change_times.append(self.parent_device.stop_time)
        # include trigger times in change_times, so that pseudoclocks always
        # have an instruction immediately following a wait:
        all_change_times.extend(self.parent_device.trigger_times)

        # convert all_change_times to a numpy array
        all_change_times_numpy = np.array(all_change_times)

        # quantise the all change times to the pseudoclock clock resolution
        all_change_times_numpy = self.quantise_to_pseudoclock(
            all_change_times_numpy
        )

        # Get rid of duplicates:
        all_change_times = list(set(all_change_times_numpy))
        all_change_times.sort()  

        # Check that the pseudoclock can handle updates this fast
        for i, t in enumerate(all_change_times[:-1]):
            dt = all_change_times[i+1] - t
            if np.round(dt,10) < 1.0/self.clock_limit: # ADDED ROUNDING HERE
                raise LabscriptError(
                    "Commands have been issued to devices attached to "
                    f"{self.name} at t={t} and t={all_change_times[i+1]}. "
                    "This Pseudoclock cannot support update delays shorter "
                    f"than {1.0/self.clock_limit} seconds."
                )
        
        return all_change_times, {}



class _ADwin_TiCO_PseudoclockDevice_dummy(PseudoclockDevice):
    description = 'Dummy Pseudoclock for allowing TiCos getting attached to the ADwinProII class'
    @set_passed_properties(property_names = {})
    def __init__(self, name, parent_device, **kwargs):
        Device.__init__(self, name, parent_device, connection="internal", **kwargs)
        self.trigger_times = [0]
        self.wait_times = []
        self.initial_trigger_time = 0
        self.trigger_device = parent_device
        self.trigger = lambda *args: None



class ADwinProII(PseudoclockDevice):
    """Main class for using the ADwin-Pro II in labscript"""
    description = 'ADWin-Pro II'
    CPU_clock_T12 = CLOCK_T12
    allowed_children = [_ADwin_CPU_T12,_ADwin_TiCO_PseudoclockDevice_dummy]

    @set_passed_properties(
        property_names={
            "connection_table_properties": ["device_no","PROCESSDELAY","process_buffered","process_manual", "mock"],
            "device_properties": [],
        }
    )
    def __init__(self,name="adwin",device_no=1,process_buffered="",process_manual="",PROCESSDELAY=PROCESSDELAY_T12, mock=False, **kwargs):
        PseudoclockDevice.__init__(self, name, None, None, **kwargs)
        self.BLACS_connection = name + "_" + str(device_no)
        self.process_buffered = str(process_buffered)
        self.process_manual = str(process_manual)
        
        self.PROCESSDELAY = PROCESSDELAY

        self._pseudoclock_T12 = _ADwin_CPU_T12(
            name=f'{name}_T12',
            pseudoclock_device=self,
            connection='internal',
            PROCESSDELAY=PROCESSDELAY_T12
        )
        self._clockline_T12 = ClockLine(
            name=f'{name}_clockline_T12',
            pseudoclock=self._pseudoclock_T12,
            connection='internal'
        )
        self.TiCos = {}

    @property
    def pseudoclock_T12(self):
        return self._pseudoclock_T12
    
    @property
    def clockline_T12(self):
        return self._clockline_T12



    def add_TiCo(self, device_name, module_address, PROCESSDELAY, TiCo_Class = _ADwin_CPU_TiCo):
        """Adding a new TiCo pseudoclock and clockline, for DIO32-TiCo modules.
        
        Parameters
        ----------
        device_name : str
            Name of the ADwin-Pro II.
        module_address : int
            Number of the module with TiCo, set in the ADwin configuration.
        PROCESSDELAY : int
            Determines the clock rate.
        TiCo_Class : _ADwin_CPU
            Class of the PseudoClock for the TiCo, where the CPU rate is defined.
        
        Returns
        -------
        self.TiCos[device_name] : TiCo_Class
            Device instance of the PseudoClock (for saving it in the module instance, too)
        """
        # Create the dummy PseudoclockDevice, which is child device of the ADwin and has no Triggers
        pseudoclock_device = _ADwin_TiCO_PseudoclockDevice_dummy(f"{device_name}_TiCo_PseudoclockDevice",self)
        self.TiCos[device_name] = TiCo_Class(
            name = f"{device_name}_TiCo",
            pseudoclock_device=pseudoclock_device,
            connection=module_address,
            PROCESSDELAY=PROCESSDELAY
        )
        ClockLine(
            name = f"{device_name}_clockline_TiCo",
            pseudoclock=self.TiCos[device_name],
            connection="internal"
        )
        return self.TiCos[device_name]
    

    def do_checks(self, outputs):
        if len(self.trigger_times)>1:
            # Either only one software trigger (for starting shot as master pseudoclock), or two (where the second one is for the 'wait')
            wait_times = [round(wait_time,9) for wait_time in compiler.wait_table]
            if len(self.trigger_times)==2 and self.trigger_times[1] not in wait_times:
                raise NotImplementedError('ADwin does not support retriggering, and only supports one "wait" in the current implementation.')
        for output in outputs:
            output.do_checks(self.trigger_times)


    def collect_all_modules(self):
        """ Creates a list of all ADwin-Pro modules sorted by the module address."""
        modules = []
        # Modules of T12 main CPU
        for device in self.clockline_T12.child_devices:
            modules.append(device)
        # Modules of TiCos
        for TiCo in self.TiCos.values():
            for device in TiCo.clockline.child_devices:
                modules.append(device)
        self.modules = sorted(modules, key=lambda mod:int(mod.module_address))


    def collect_card_instructions(self, hdf5_file):
        """Write all module instruction data to HDF5 file.
        
        This function iterates over all ADwin modules and saves the data
        of output and input channels in the correct format depending on
        the module type. If new modules are implemented, they have to be
        inclueded here.
        """
        group = hdf5_file.require_group('/devices/%s'%self.name)
        AO_group = group.require_group('ANALOG_OUT')
        AI_group = group.require_group('ANALOG_IN')

        # Lists to collect instructions of analog channels
        analog_output = []
        PID_channels = []
        PID_config = []
        analog_input = []
 
        for device in self.modules: 
            if isinstance(device,ADwinAO8):
                analog_output.append(device.outputs)
                PID_channels.append(device.PID_table)
                PID_config.append(device.PID_config)
            elif isinstance(device,ADwinDIO32):
                group.create_dataset("DIGITAL_OUT/"+device.name, data=device.digital_data)
                if compiler.wait_table:
                    group["DIGITAL_OUT/"+device.name].attrs["wait_time"] = round( list(compiler.wait_table)[0] * device.parent_clock_line.clock_limit )
            elif isinstance(device,ADwinAI8):
                # For the AIN table it's required that self.modules is sorted correctly!
                analog_input.append(device.AIN_times)
            else:
                raise AssertionError(f"Invalid child device {device.name} of type {type(device).__name__}, shouldn't be possible")
        
        # Add final values to analog outputs and PID settings
        last_values = self.stop_time*self._pseudoclock_T12.clock_limit + 1
        analog_output.append(np.full(1,last_values,dtype=analog_output[0].dtype))
        PID_channels.append(np.full(1,last_values,dtype=PID_channels[0].dtype))
        # Concatenate arrays
        PID_channels = np.concatenate(PID_channels)
        PID_config = np.concatenate(PID_config)
        analog_output = np.concatenate(analog_output)
        analog_input = np.concatenate(analog_input)
        # Sort analog outputs and PID settings
        analog_output = np.sort(analog_output, axis=0, order="n_cycles")
        PID_channels = np.sort(PID_channels, axis=0, order="n_cycles")
        PID_config = np.sort(PID_config, axis=0, order="PID_channel")
        # Save datasets
        AO_group.create_dataset('VALUES', compression=config.compression, data=analog_output)
        AO_group.create_dataset('PID_CHANNELS', compression=config.compression, data=PID_channels)
        AO_group.create_dataset('PID_CONFIG', compression=config.compression, data=PID_config)
        AI_group.create_dataset('TIMES', data=analog_input)

        AI_datapoints = analog_input["stop_time"] - analog_input["start_time"]
        AI_group.attrs["AIN_count"] = int(np.sum(AI_datapoints))

        # Check array sizes from ADbasic
        AO_events = analog_output.shape[0]
        if AO_events > MAX_EVENTS:
            raise LabscriptError(
                f"The number of analog outputs ({AO_events}) is larger than the array size in ADbasic ({MAX_EVENTS})!"
                )
        AI_num = AI_group.attrs["AIN_count"]
        if AI_num > A_IN_BUFFER:
            raise LabscriptError(
                f"The number of analog inputs measured ({AI_num}) is larger than the array size in ADbasic ({A_IN_BUFFER})!"
            )
        PID_events = PID_channels.shape[0]
        if PID_events > MAX_PID_EVENTS:
            raise LabscriptError(
                f"The number of changing the PID settings ({PID_events}) is larger than the array size in ADbasic ({MAX_PID_EVENTS})!"
            )

    
    def generate_code(self, hdf5_file):
        self.collect_all_modules()
        outputs = self.get_all_outputs()      

        # These functions do some checks and make sure the timings are rounded to a value
        # that the clocks can handle (even if there is no trigger offset).
        self.do_checks(outputs)
        self.offset_instructions_from_trigger(outputs)

        # We don't need to call generate_code for the Pseudoclocks, because for the
        # outputs we only need the list when each output changes and don't have a
        # real clock. All code creation is done on module level.
        for module in self.modules:
            module.generate_code(hdf5_file)
            module.do_checks()
        # After all modules created their output, we collect the digital and analog 
        # data and store them in the hdf5 file.
        self.collect_card_instructions(hdf5_file)

        # Save stop time to ADwin device properties
        self.set_property("stop_time", self.stop_time, "device_properties")
        # Save list of module names to connection table properties
        module_dict = {str(module.module_address) : module.name for module in self.modules}
        self.set_property("modules", module_dict, "connection_table_properties")

        # Add wait time and timeout in units of ADwin process cycles
        if len(compiler.wait_table)>1:
            raise LabscriptError("ADwin supports only a sinlge wait for now!")
        for time,args in compiler.wait_table.items():
            hdf5_file[f"devices/{self.name}"].attrs["wait_time"] = round(time * self._pseudoclock_T12.clock_limit)
            hdf5_file[f"devices/{self.name}"].attrs["wait_timeout"] = round(args[1] * self._pseudoclock_T12.clock_limit)
            for TiCo in self.TiCos:
                hdf5_file[f"devices/{self.name}/DIGITAL_OUT/"].attrs["wait_time"] = round(time * self.TiCos[TiCo].clock_limit)
        