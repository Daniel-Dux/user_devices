from labscript_utils.unitconversions.UnitConversionBase import UnitConversion

class OffsetField(UnitConversion):
    base_unit = "V"
    derived_units = "G"

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters
        UnitConversion.__init__(self, self.parameters)

    def G_to_base(self, value_in_G):
        """Convert Gauss to Volts using linear calibration."""
        slope = self.parameters.get('slope', 167.75)  # G/V
        offset = self.parameters.get('offset', 0.0)  # G
        value_in_V = (value_in_G - offset) / slope
        return value_in_V
    
    def G_from_base(self, value_in_V):
        """Convert Volts to Gauss using linear calibration."""
        slope = self.parameters.get('slope', 167.75)  # G/V
        offset = self.parameters.get('offset', 0.0)  # G
        value_in_G = slope * value_in_V + offset
        return value_in_G
    
class Photodiode(UnitConversion):
    base_unit = "V"
    derived_units = ["W", "mW", "uW", "nW"]

    def __init__(self, parameters=None):
        self.parameters = parameters
        UnitConversion.__init__(self, self.parameters)

    def W_to_base(self, value_in_mW):
        slope = self.parameters.get('slope', 0.5)/1000  # mW/V
        offset = self.parameters.get('offset', 0.0)/1000  # mW
        value_in_V = (value_in_mW - offset) / slope
        # value_in_V = slope * value_in_mW + offset
        return value_in_V
    
    def W_from_base(self, value_in_V):
        slope = self.parameters.get('slope', 0.5)/1000  # mW/V
        offset = self.parameters.get('offset', 0.0)/1000  # mW
        value_in_W = slope * value_in_V + offset
        # value_in_mW = (value_in_V - offset) / slope
        return value_in_W
    
    def uW_to_base(self, value_in_uW):
        value_in_W = value_in_uW / 1e6
        return self.W_to_base(value_in_W)
    
    def uW_from_base(self, value_in_V):
        value_in_W = self.W_from_base(value_in_V)
        return value_in_W * 1e6
    
    def nW_to_base(self, value_in_nW):
        value_in_W = value_in_nW / 1e9
        return self.W_to_base(value_in_W)
    
    def nW_from_base(self, value_in_V):
        value_in_W = self.W_from_base(value_in_V)
        return value_in_W * 1e9
    
    def mW_to_base(self, value_in_mW):
        value_in_W = value_in_mW / 1e3
        return self.W_to_base(value_in_W)
    
    def mW_from_base(self, value_in_V):
        value_in_W = self.W_from_base(value_in_V)
        return value_in_W * 1e3