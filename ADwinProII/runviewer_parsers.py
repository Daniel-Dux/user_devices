#####################################################################
#                                                                   #
# ADwin/runviever_parsers.py                                        #
#                                                                   #
# Copyright 2022, TU Vienna                                         #
#                                                                   #
# Implementation of the ADwin-Pro II for the labscript-suite,       #
# used in the Léonard lab for Experimental Quantum Information.     #
#                                                                   #
#####################################################################


from ast import mod
from labscript_utils import properties
import h5py
import numpy as np

from .ADwin_utils import DAC
from . import CLOCK_T12,CLOCK_TiCo

class ADwinProIIParser(object):

    def __init__(self, path, device):
        self.path = path
        self.name = device.name
        self.device = device


    def get_traces(self, add_trace, clock=None):
        file = h5py.File(self.path, 'r')
        group = file['devices/' + self.name]

        props = properties.get(file, self.name, 'connection_table_properties')

        clocklines_and_triggers = {}

        for pseudoclock in self.device.child_list.values():
            print(pseudoclock.name, type(pseudoclock))
            if "TiCo" in pseudoclock.name:
                for name,TiCo in pseudoclock.child_list.items():
                    pseudoclock = TiCo
            print(pseudoclock.name, type(pseudoclock))
            for clockline in pseudoclock.child_list.values():
                for module_name,module in clockline.child_list.items():
                    print(module_name)
                    module_props = properties.get(file, module_name, 'connection_table_properties')

                    if module.device_class == "ADwinAO8":
                        AO_props = properties.get(file, module_name, 'connection_table_properties')
                        res = AO_props["resolution_bits"]
                        min_V = AO_props["min_V"]
                        max_V = AO_props["max_V"]
                        module_idxshift = AO_props["start_index"]
                        for output_name,output in module.child_list.items():
                            channel = module_idxshift + int(output.parent_port)
                            mask = group["ANALOG_OUT/VALUES"]["channel"] == channel
                            trace = (
                                group["ANALOG_OUT/VALUES"]["n_cycles"][mask] / CLOCK_T12 * props["PROCESSDELAY"],
                                DAC(group["ANALOG_OUT/VALUES"]["value"][mask],res,min_V,max_V)
                            )
                            if np.sum(mask)<=1: # If channel is only set in the beginning, add a second point at stop_time such that a line is shown
                                trace = (list(trace[0])*2,list(trace[1])+[group.attrs["stop_time"]])
                            add_trace(output_name, trace, output_name, output.parent_port)

                    elif module.device_class == "ADwinDIO32":
                        table = group[f"DIGITAL_OUT/{module.name}"][:]
                        for output_name, output in module.child_list.items():
                            bit = int(output.parent_port)-1
                            bits_output = (table["bitfield"] & 2**bit) >> bit
                            trace = (
                                table["n_cycles"] / CLOCK_TiCo * module_props["PROCESSDELAY_TiCo"],
                                bits_output)
                            add_trace(output_name, trace, output_name, output.parent_port)
                            clocklines_and_triggers[output_name] = (trace)

                    elif module.device_class == "ADwinAI8":
                        table = group["ANALOG_IN/TIMES"]
                        module_idxshift = properties.get(file, module_name, 'connection_table_properties')["start_index"]
                        for input_name,input in module.child_list.items():
                            conn = int(input.parent_port)
                            i = conn-1+module_idxshift
                            trace = (
                                [table['start_time'][i]/ CLOCK_T12 * props["PROCESSDELAY"],
                                    table['stop_time'][i] / CLOCK_T12 * props["PROCESSDELAY"]],
                                [1,0]
                                )
                            add_trace(input_name, trace, input_name, input.parent_port)


        return clocklines_and_triggers