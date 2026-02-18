import sys
import time
import logging
import numpy as np
import matplotlib.pyplot as plt
try:
    import ADwin
except ImportError:
    sys.path.append(r"C:\ADwin\Developer\Python")
    import ADwin

from user_devices.ADwinProII.ADwin_utils import ADC,DAC

RAISE_EXCEPTIONS = 1
NO_YES = ("no", "yes")

DEVICENUMBER = 0x1
PROCESSORTYPE = "12"
PROCESS_2 = r"C:\ADwin\LEOLAB\ADbasic_program_manual.TC2"

adw = ADwin.ADwin(DEVICENUMBER, RAISE_EXCEPTIONS)

def init():
    # Boot ADwin-System
    if adw.Test_Version():
        print("boot ADwin-system... ", end="", flush=True)
        BTL = adw.ADwindir + "adwin" + PROCESSORTYPE + ".btl"
        adw.Boot(BTL)
        print("ok")

    # Test_Version
    print("test_version()... ", end="", flush=True)
    if adw.Test_Version() == 0:
        print("ok")
    else:
        print("not ok")

    print("process is running:", NO_YES[adw.Process_Status(1)])
    print("processdelay:", adw.Get_Processdelay(1))

    # ProcessorType
    print("processor_type:", adw.Processor_Type())

def load_process(PROCESS,PROCESS_NO):
    # Load and start process
    print("load process... ", end="", flush=True)
    adw.Load_Process(PROCESS)
    time.sleep(0.2)
    print("ok")

def start_process(PROCESS_NO):
    print("start process... ", end="", flush=True)
    adw.Start_Process(PROCESS_NO)
    print("ok")
    time.sleep(0.2)
    print("process is running:", NO_YES[adw.Process_Status(PROCESS_NO)])

    print("workload... ", end="", flush=True)
    adw.Workload() # first call with invalid value
    print(adw.Workload(), "%")

    print("free memory, type cm:", adw.Free_Mem(5), "kbyte")
    print("free memory, type um:", adw.Free_Mem(6), "kbyte")

if __name__=="__main__":
    init()
    load_process(PROCESS_2,2)

    # Set AOut of Module 5, Channel 0 to 1V  
    output = ADC(0)
    adw.Set_Par(51,5)
    adw.Set_Par(52,1)
    adw.Set_Par(53,int(output))
    adw.Set_Par(54,3)
    adw.Set_Par(55,1)
    adw.Fifo_Clear(51)

    fifo = []
    # Start Process
    adw.Start_Process(2)
    for i in np.arange(0,5.1,0.5):
        adw.Set_Par(53,int(ADC(i)))
        time.sleep(1e-4)
        fifo.append(adw.GetFifo_Long(51,adw.Fifo_Full(51)))
        
    #fifo = np.ctypeslib.as_array(adw.GetFifo_Long(51,adw.Fifo_Full(51)))
    values = np.array([])
    for i in fifo:
        values = np.concatenate([values,np.ctypeslib.as_array(i)])
    time.sleep(1)
    adw.Stop_Process(2)

    values = DAC(values)
    times = np.arange(len(values)) * 1e-9 * adw.Get_Processdelay(2)
    print(values.size)
    print(ADC(0))
    plt.figure()
    plt.plot(times*1000,values)
    plt.xlabel("Time [ms]") 
    plt.ylabel("Voltage")
    plt.show()