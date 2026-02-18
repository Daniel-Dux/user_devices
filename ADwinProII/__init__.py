############################################################################
#                                                                          #
# ADwinProII/__init__.py                                                   #
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

# T12 Processor has 1GHz clock rate
PROCESSDELAY_T12 = 2000
CLOCK_T12 = 1e9

# TiCo1 Processor has 50MHz clock rate
PROCESSDELAY_TiCo = 25
CLOCK_TiCo = 50e6

# The TiCos are started a few cycles after the T12 process, 
# to ensure real-time outputs (the fisrt T12 cycle might take 
# longer than the T12 processdelay). 
# These two values are set in the ADwin code and must be the same
# physical timespan in terms of each clock's rate and processdelay.
TiCo_start_cycles = 80
TiCo_start_in_T12_cycles = 20

# For the Analog Input and Output values, we use combined arrays 
# for the modules in the ADwin code. To keep track which channel
# of the modules has which index in the array, we explicitly define
# where we have the start indices (ZERO INDEXED FOR PYTHON!).
module_start_index = {
    3:0, # AI8 1
    4:8, # AI8 2
    5:0, # AOUT8 1
    6:8, # AOUT8 2
}
# BEWARE: In collect_card_instructions the start_index and 
# module_index of each module type must have to same sorting order!

# Array sizes in the ADbasic process
MAX_EVENTS      = 200000      # Max number of events that can be stored
MAX_PID_EVENTS  = 2000        # Max number of changing the AIN channel for PID feedback to AOUT
MAX_TICO_EVENTS = 3000        # Max number of Digital Output events
A_IN_BUFFER     = 30000000    # Size of Array to transmit AIN values to the runner PC
PIDNO           = 100         # Max Number of PIDs