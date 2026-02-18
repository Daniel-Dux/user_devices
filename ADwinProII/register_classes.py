#####################################################################
#                                                                   #
# ADwinProII/register_classes.py                                    #
#                                                                   #
# Copyright 2022, TU Vienna                                         #
#                                                                   #
# Implementation of the ADwin-Pro II for the labscript-suite,       #
# used in the Léonard lab for Experimental Quantum Information.     #
#                                                                   #
#####################################################################

import labscript_devices


labscript_device_name = 'ADwinProII'
blacs_tab = 'user_devices.ADwinProII.blacs_tabs.ADwinProIITab'
parser = 'user_devices.ADwinProII.runviewer_parsers.ADwinProIIParser'

labscript_devices.register_classes(
    labscript_device_name=labscript_device_name,
    BLACS_tab=blacs_tab,
    runviewer_parser=parser,
)