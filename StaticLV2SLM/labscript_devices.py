from labscript import Device, set_passed_properties, LabscriptError

class StaticSLM(Device):
    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "device_address",
                "device_port",
                "mock",
            ],
        }
    )
    
    def __init__(self, name, device_address, device_port, mock=False, **kwargs):
        self.BLACS_connection = device_address + ":" + str(device_port)
        self.device_address = device_address
        self.device_port = device_port
        self.mock = mock
        self.coefficients = {}
        
        Device.__init__(self, name, None, None, self.BLACS_connection, **kwargs)
        
    def set_coefficient(self, coefficient_name, value):
        self.coefficients[coefficient_name] = value
    
    def generate_code(self, hdf5_file):
        
        group = self.init_device_group(hdf5_file)
        coefficient_names = list(self.coefficients.keys())
        coefficient_values = list(self.coefficients.values())
        
        group.create_dataset('coefficient_names', data=coefficient_names)
        group.create_dataset('coefficient_values', data=coefficient_values)
        
        return