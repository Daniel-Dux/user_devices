#####################################################################
#                                                                   #
# ADwinProII/ADwin_utils.py                                         #
#                                                                   #
# Copyright 2022, TU Vienna                                         #
#                                                                   #
# Implementation of the ADwin-Pro II for the labscript-suite,       #
# used in the Léonard lab for Experimental Quantum Information.     #
#                                                                   #
#####################################################################

import numpy as np
from labscript import config
from labscript_utils import connections
from labscript_utils import properties
from labscript_utils import h5_lock
import h5py
from . import CLOCK_T12

def ADC(voltage,resolution=16,min_V=-10,max_V=10):
    """Convert ADwin analog to digital.

    Convert analog voltage values to the digital format for ADwin AOut/AIn modules.
    The 16 bits (resolution) cover the range of [-10,10) Volts, with 0 := -10V.
    The step size therefore is 0.305mV and 32768 is used for 0V.
    
    Parameters
    ----------
    voltage : float
        Array or number of analog voltage to convert.
    resolotion : int, optional 
        Number of bits to represent the digital number.
    min_V : float, optional 
        Maximum analog voltage (returns 0 if voltage=min_V).
    max_V : float, optional 
        Minimum analog voltage.
    
    Returns
    -------
    output : numpy.int32 or numpy.ndarray
        Digital representation of voltage.
    """
    output = (voltage-min_V)/(max_V-min_V)*(1<<resolution)
    output = np.round(output).astype(np.int32)
    # The maximum digital value is 65535 (= 9.999695V).
    # For 10V the value is rounded to 65536, which is equivalent to -10V.
    # We correct this rounding error here by hand:
    if np.any(output==65536):
        if isinstance(output,np.ndarray):
            output[output==65536] = 65535
        elif isinstance(output,float) or isinstance(output,np.uint) or isinstance(output,np.int32):
            output = 65536
        else:
            raise NotImplementedError
    return output


def DAC(values,resolution=16,min_V=-10,max_V=10):
    """Convert ADwin digital to analog.

    Convert the digital representation in ADwin to the analog voltage.
    The 16 bits (resolution) cover the range of [-10,10) Volts, with 0 := -10V.
    The step size therefore is 0.305mV and 32768 is used for 0V.  

    Parameters
    ---------- 
    values: 
        Array or number of digital values.
    resolotion : int, optional
        Number of bits that represent the digital number.
    min_V : float, optional 
        Maximum analog voltage.
    max_V : float,optional
        Minimum analog voltage.
    
    Returns
    -------
    voltage : float
        Number or array with converted analog voltage.
    """
    voltage = (values.astype(np.float64))*(max_V-min_V)/(1<<resolution) + min_V
    return voltage


def get_channel_from_BLACS_name(BLACS_name):
    """ Returns channel name, e.g. 8 for "DIO32_1/8".

    Helper function to split the module name and channel number from the 
    BLACS hardware name and returns the channel number. This function is
    used to sort the widgets in the BLACS GUI by the channel number.

    Parameters
    ----------
    BLACS_name : str
        Name of the ADwin channel in BLACS, e.g. "AO8_2/1".
        
    Returns
    -------
    channel : int
        Integer number of the output/input channel.
    """
    card,channel = BLACS_name.split('/')
    return int(channel)


def get_ain_traces(h5file, raw_data_name="ADwinAnalogIn_DATA", convert_data=True, device_name="ADwin", write_hdf5 = True):
    """ 
    Split raw (sorted!) data from ADwin analog inputs into aquisitions
    of channels and store the traces for each channel in the h5 file.

    Parameters
    ----------
    h5file : str
        Filename of the experiment shot (HDF5 file).
    raw_data_name : str, optional
        Name of the dataset with the raw acquisitions from BLACS.
    convert_data : bool, optional
        Set is the input voltage is stored as row value, or converted to volts.
    device_name : str, optional
        Name of the ADwin device.
    write_hdf5 : bool, optional
        Decides if the single traces are written to the hdf5 file or returned. 
    """
    return_dict = {}
    with h5py.File(h5file, 'r'+write_hdf5*'+') as f: # open with(out) write permission depending on argument
        group = f["data/traces"]
        if raw_data_name not in group:
            print(f"No raw acquisition data with name '{raw_data_name}' found!")
            return
        raw_data = group[raw_data_name][:]
        if convert_data:
            raw_data = DAC(raw_data)
            dtype = [("t",np.float32),("values",np.float32)]
        else:
            dtype = [("t",np.float32),("values",np.uint16)]

        clock_rate = CLOCK_T12 / properties.get(f, device_name, "connection_table_properties")["PROCESSDELAY"]
        acquisition_times = f[f"devices/{device_name}/ANALOG_IN/TIMES"]
        if "storage_rate" in acquisition_times.dtype.fields.keys():
            acquisitions_per_channel = np.ceil((acquisition_times["stop_time"] - acquisition_times["start_time"]).astype(np.float64) * acquisition_times["storage_rate"] / clock_rate)
            split_indices = np.cumsum(acquisitions_per_channel).astype(int)[:-1]
        else:
            split_indices = np.cumsum(acquisition_times["stop_time"] - acquisition_times["start_time"])[:-1]


        for i,acquisition in enumerate(np.split(raw_data,split_indices)):
            if not acquisition.size:
                continue
            if convert_data:
                acquisition = acquisition / (2**f[f"devices/{device_name}/ANALOG_IN/TIMES"][i]["gain_mode"])
            label =  f[f"devices/{device_name}/ANALOG_IN"].attrs[str(i+1)]
            if label in group:
                print(f"Dataset with name '{label}' already exists, skipping channel.")
                continue
            if "storage_rate" in acquisition_times.dtype.fields.keys():
                times = np.arange(acquisition_times["start_time"][i],acquisition_times["stop_time"][i],int(clock_rate//acquisition_times["storage_rate"][i])) / clock_rate
            else:
                times = np.arange(acquisition_times["start_time"][i],acquisition_times["stop_time"][i]) / clock_rate
            if "waits" in f["data"]:
                # There was a wait in the experiment, let's offset the times such that they are accurate
                waits = f["data/waits"][:]
                for i in range(len(waits)):
                    times[times > waits["time"][i]] += waits["duration"][i]
            if write_hdf5:
                data = np.rec.fromarrays([times, acquisition], dtype=dtype)
                group.create_dataset(label, compression = config.compression, data = data)
            else:
                return_dict[label] = times, acquisition
    if not write_hdf5:
        return return_dict



def get_aout_trace(h5file, output):
    """ ADwin analog output as function of the time.

    Function to return the output trace [s],[V] determined from the 
    ADwin instruction array in the h5file.

    Parameters
    ----------
    h5file : str
        Filename of the experiment shot (HDF5 file).
    output : str
        Name of the analog output.

    Returns
    -------
    t : numpy.ndarray
        Times when the output changes in seconds.
    values : numpy.ndarray
        Values of the output at times in volts.

    Raises
    ------
    RuntimeError
        If no output channel is found with the given name.
    """
    conn_table = connections.ConnectionTable(h5file)
    conn = conn_table.find_by_name(output)
    port = int(conn.parent_port) + conn.parent.properties["start_index"]
    PROCESSDELAY = conn_table.find_by_name("ADwin").properties["PROCESSDELAY"]
    if port is None:
        raise RuntimeError(f"No output found with name '{output}' in the connnection table.")
    with h5py.File(h5file, 'r') as f:
        data = f["devices/ADwin/ANALOG_OUT/VALUES"][:]
        mask = (data["channel"] == port)
        t = np.round(PROCESSDELAY / CLOCK_T12 * data["n_cycles"][mask], 9)
        if "data" in f and "waits" in f["data"]:
                # There was a wait in the experiment, let's offset the times such that they are accurate
                waits = f["data/waits"][:]
                for i in range(len(waits)):
                    t[t > waits["time"][i]] += waits["duration"][i]
        values = DAC(data["value"][mask])
    return t, values