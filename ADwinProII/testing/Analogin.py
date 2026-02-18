import h5py
import numpy as np
import matplotlib.pyplot as plt
from user_devices.ADwinProII.ADwin_utils import DAC
import time

file = h5py.File("./ADwinProII/testing/2022-10-06_0028_test_experiment_0.h5", "r+")
AIN_times = file["devices/ADwin/ANALOG_IN/TIMES"][:]
AI_count = file[f"devices/ADwin/ANALOG_IN"].attrs["AIN_count"]
AINData = file["data/ANALOG_IN"][:]
start = time.perf_counter()
AIN_values = [np.zeros(size,dtype=np.int32) for size in (AIN_times["stop_time"]-AIN_times["start_time"])]
times = sorted(set(AIN_times[["start_time","stop_time"]].view(np.int32)))

idx = 0
start_time = 0
times.remove(0)
for end_time in times:
    aqu_channels = np.nonzero((AIN_times["start_time"]<=start_time)&(AIN_times["stop_time"]>start_time))[0]
    end_idx = end_time*aqu_channels.size
    for i,channel in enumerate(aqu_channels): # aqu_channels is always sorted (because numpy.nonzero returns indices)!
        chan_idx = start_time - AIN_times["start_time"][channel]
        AIN_values[channel][chan_idx:chan_idx+end_time] = AINData[idx+i:idx+end_idx:aqu_channels.size]
    start_time = end_time
    idx = idx + end_idx
print("Without writing:",time.perf_counter()-start)
if "data/ADwinAnalogIn" in file:
    del file["data/ADwinAnalogIn"]
group = file.create_group("data/ADwinAnalogIn")
for i in range(len(AIN_values)):
    if AIN_values[i].size > 0:
        group.create_dataset(f"AIN{i+1}", compression="gzip", data=AIN_values[i])
print("With writing:",time.perf_counter()-start)
plt.figure()
for i in range(AIN_times.shape[0]):
    if AIN_values[i].size != 0:
        t = np.arange(AIN_times["start_time"][i], AIN_times["stop_time"][i])
        plt.plot(t,DAC(AIN_values[i]),label=f"AIN {i+1}")#, {AIN_times['label'][0]}")
#plt.plot(DAC(AINData))
plt.xlabel("time")
plt.ylabel("voltage")
plt.legend(loc="best")
plt.show()
