# ADwin-Pro II for the labscript-suite

This is the implemetation of the [ADwin-Pro II](https://www.adwin.de/de/produkte/proII.html) to be used with labscript for our experiment control system.
For usage of this project, also the code for the ADwin processes is necessary, which can be found in an separate repository [here](https://gitlab.tuwien.ac.at/quantuminfo/experiment-control/adwin).

The implemetation and usage of the ADwin with labscript is descriped in [this Master thesis](https://doi.org/10.34726/hss.2023.104001) in more detail.

## Expample for the connection table

In the following snippet, the code to create instances of the ADwin and its modules in the connection table and experiment scripts is given.
The `process_buffered` and `process_manual` have to be replaced (or defined as *globals*) by the path to the complied [ADwin processes](https://gitlab.tuwien.ac.at/quantuminfo/experiment-control/adwin).
Note that instead of the usual `AnalogOut` class, `ADwinAnalogOut` is used (for PID control and redefined ramp samplerates).

```
from labscript import DigitalOut, AnalogIn
from user_devices.ADwinProII.labscript_devices import ADwinProII
from user_devices.ADwinProII.labscript_devices_ADwin_modules import ADwinAI8,ADwinAO8,ADwinDIO32

# Create ADwin-Pro II Hardware
ADwinProII("ADwin", process_buffered, process_manual)
ADwinDIO32("DIO32_1", ADwin, module_address=1, TiCo=True)
ADwinDIO32("DIO32_2", ADwin, module_address=2, TiCo=True)
ADwinAO8  ("AO8_1", ADwin, module_address=5)
ADwinAO8  ("AO8_2", ADwin, module_address=6)
ADwinAI8  ("AI8_1", ADwin, module_address=3)
ADwinAI8  ("AI8_2", ADwin, module_address=4)

# Digital Outputs
DigitalOut("DigitalOutName", parent_device=DIO32_1, connection="1")
...
# Analog Outputs
ADwinAnalogOut("AnalogOutName", parent_device=AO8_1, connection="1")
...
# Analog Inputs
AnalogIn("AnalogInName", parent_device=AI8_1, connection="1")
...
```

## Known limitations and issues

* With the current implemetation the ADwin can be only used as *Master Pseudoclock* in labscript. In principle, the ADwin can also support timing from an external trigger.
* `waits` in labscript are not supported (yet?).
* The digital PID control can be active for not more than 13 channels, otherwise the CPU commands are not in real-time (see Figure 3.3 [here](https://doi.org/10.34726/hss.2023.104001)).
