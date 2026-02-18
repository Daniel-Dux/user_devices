from numpy import log2

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from qtutils import *

#from labscript_utils.qtwidgets.analoginput import AnalogInput



class ADwinAnalogInput(QWidget):
    def __init__(self, device_name, hardware_name, connection_name='-', display_name=None, scale_factor=1, horizontal_alignment=False, parent=None):
        self.scale_factor = scale_factor
        
        QWidget.__init__(self, parent)

        #self.plot = None
        self._device_name = device_name
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        if scale_factor>1:
            self._hardware_name += f" (gain {int(log2(scale_factor))})"
        #self.win = None

        label_text = (self._hardware_name + '\n' + self._connection_name) if display_name is None else display_name
        self._label = QLabel(label_text)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self._line_edit = QLineEdit()
        self._line_edit.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        self._line_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._line_edit.setMaximumWidth(75)
        self._line_edit.setAlignment(Qt.AlignRight)
        self._line_edit.setReadOnly(True)


        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)

        # Create widgets and layouts
        if horizontal_alignment:
            self._layout = QHBoxLayout(self)
            self._layout.addWidget(self._label)
            self._layout.addWidget(self._line_edit)
        else:
            self._layout = QGridLayout(self)
            self._layout.setVerticalSpacing(0)
            self._layout.setHorizontalSpacing(0)
            self._layout.setContentsMargins(5, 5, 5, 5)

            self._label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
            self._layout.addWidget(self._label)
            self._layout.addItem(QSpacerItem(0, 0, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum), 0, 1)

            h_widget = QWidget()
            h_layout = QHBoxLayout(h_widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.addWidget(self._line_edit)

            self._layout.addWidget(self._label, 0, 0)
            self._layout.addWidget(h_widget, 1, 0)
            
        self.set_value(None)


    @inmain_decorator(True)
    def set_value(self, value):
        if value is not None:
            text = f"{value/self.scale_factor:0.4f}"
        else:
            text = "no value"
        self._line_edit.setText(text)
