import sys
import time
import h5py
import numpy as np
import matplotlib.pyplot as plt
try:
    import ADwin
except ImportError:
    sys.path.append(r"C:\ADwin\Developer\Python")
    import ADwin

from user_devices.ADwinProII.ADwin_utils import ADC,DAC
import ctypes

RAISE_EXCEPTIONS = 1

DEVICENUMBER = 0x1
PROCESSORTYPE = "12"
PROCESS_1 = r"C:\ADwin\LEOLAB\ADbasic_program_buffered.TC1"

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

def load_process(PROCESS):
    # Load and start process
    print("load process... ", end="", flush=True)
    adw.Load_Process(PROCESS)
    time.sleep(0.2)
    print("ok")

if __name__=="__main__":
    h5_start = time.perf_counter()
    file = h5py.File(r"C:\Users\labuser\labscript-suite\userlib\user_devices\ADwinProII\testing\2022-10-06_0028_test_experiment_0.h5")
    AOUT = file["devices/ADwin/ANALOG_OUT/VALUES"]
    PIDs = file["devices/ADwin/ANALOG_OUT/PID_CHANNELS"]
    DOUT = file["devices/ADwin/DIGITAL_OUT"]
    AIN = file["devices/ADwin/ANALOG_IN/TIMES"]
    init_start = time.perf_counter()
    # Start ADwin
    adw = ADwin.ADwin(DEVICENUMBER, RAISE_EXCEPTIONS)
    init()
    load_process(PROCESS_1)

    stop_time = file["devices/ADwin"].attrs["stop_time"]
    quantized_stop_time = int(np.round(stop_time * 1e9 / adw.Get_Processdelay(1)))
    transfer_start = time.perf_counter()
    # Transfer Data
    adw.SetData_Long(AOUT["n_cycles"].ctypes, 1, 1, AOUT.shape[0])
    adw.SetData_Long(AOUT["channel"].ctypes, 2, 1, AOUT.shape[0])
    adw.SetData_Long(AOUT["value"].ctypes, 3, 1, AOUT.shape[0])
    adw.SetData_Long(PIDs["n_cycles"].ctypes, 4, 1, PIDs.shape[0])
    adw.SetData_Long(PIDs["AOUT_channel"].ctypes, 5, 1, PIDs.shape[0])
    adw.SetData_Long(PIDs["PID_channel"].ctypes, 6, 1, PIDs.shape[0])
    adw.SetData_Long(AIN["start_time"].ctypes, 7, 1, AIN.shape[0])
    adw.SetData_Long(AIN["stop_time"].ctypes, 8, 1, AIN.shape[0])
    adw.SetData_Long(DOUT["DIO32_1"]["n_cycles"].ctypes, 10, 1, DOUT["DIO32_1"].shape[0])
    adw.SetData_Long(DOUT["DIO32_1"]["bitfield"].ctypes, 11, 1, DOUT["DIO32_1"].shape[0])
    adw.SetData_Long(DOUT["DIO32_2"]["n_cycles"].ctypes, 20, 1, DOUT["DIO32_2"].shape[0])
    adw.SetData_Long(DOUT["DIO32_2"]["bitfield"].ctypes, 21, 1, DOUT["DIO32_2"].shape[0])
    adw.Set_Par(2, quantized_stop_time)  # Set end time

    process_start = time.perf_counter()
    adw.Start_Process(1)
    end = 0
    start_time = time.time()
    time.sleep(stop_time)
    while adw.Get_Par(1) == 1: # Check if the 'busy' parameter in ADwin was set to 0
        time.sleep(0.00001)
    print(adw.Get_Par(10),adw.Get_Par(20))
    # adw.Stop_Process(1)
    print("Finished Process")
    AINtransfer_start = time.perf_counter()
    AI_count = file[f"devices/ADwin/ANALOG_IN"].attrs["AIN_count"]
    AINData = np.ctypeslib.as_array(adw.GetData_Long(9,1,int(AI_count)))
    end = time.perf_counter()

    print("TIMING:")
    print(f"Data from hdf5 file: {init_start-h5_start:.4f} s")
    print(f"Init ADwin: {transfer_start-init_start:.4f} s")
    print(f"Output data transfer to ADwin: {process_start-transfer_start:.4f} s")
    print(f"Process time: {AINtransfer_start-process_start:.4f} s")
    print(f"AIN data transfer from ADwin: {end-AINtransfer_start:.4f} s")
    print(f"TOTAL TIME: {end-h5_start:.4f} s")

    # seperate AIN channels
    AIN_measurements = {}
    meas_channels = (AIN["stop_time"] - AIN["start_time"])!=0
    for chan in np.where(meas_channels)[0]:
        print(f"{chan=}")
        start = AIN["start_time"][chan]
        stopp = AIN["stop_time"][chan]
        AIN_started = AIN[AIN["start_time"]<start]
        count_before_start = np.sum(
            (AIN_started["stop_time"] <= start)*(AIN_started["stop_time"]
            -
            AIN_started["start_time"]) + (AIN_started["stop_time"] > start)*(start-AIN_started["start_time"])
            )
        print(count_before_start)

        channel_count = np.sum(AIN["start_time"] <= AIN["start_time"][chan])
            
            

    # #times = np.arange(AINData.size)# * 1e-9 * adw.Get_Processdelay(1)
    # plt.figure()
    # plt.plot(DAC(AINData),label="AIN")
    # # plt.plot(AIN1,label="AIN1") 
    # # plt.plot(times,AIN3,label="AIN1") 
    # plt.legend(loc="best")
    # plt.xlabel("Time")
    # plt.ylabel("Voltage [V]")
    # plt.show()
    