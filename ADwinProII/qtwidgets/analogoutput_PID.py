from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *

from labscript_utils.qtwidgets.analogoutput import AnalogOutput, NoStealFocusDoubleSpinBox


class NoStealFocusSpinBox(QSpinBox):
    """A QSpinBox that doesn't steal focus as you scroll over it with a
    mouse wheel."""
    def __init__(self, *args, **kwargs):
        QSpinBox.__init__(self, *args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def focusInEvent(self, event):
        self.setFocusPolicy(Qt.WheelFocus)
        return QSpinBox.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.setFocusPolicy(Qt.StrongFocus)
        return QSpinBox.focusOutEvent(self, event)

    def wheelEvent(self, event):
        if self.hasFocus():
            return QSpinBox.wheelEvent(self, event)
        else:
            event.ignore()

class ADwinAnalogOutPIDWidget(AnalogOutput):
    def hide_PID(self):
        for widget in self.hidden_widgets:
            widget.setVisible(False)
        self.setFixedHeight(self.sizeHint().height())
        self.parent()._layout_widgets(True)
        self.hide_button.setIcon(QIcon(':/qtutils/fugue/control-270'))
        self.hide_button.clicked.disconnect()
        self.hide_button.clicked.connect(self.show_PID)

    def show_PID(self):
        for widget in self.hidden_widgets:
            widget.setVisible(True)
        self.setFixedHeight(self.sizeHint().height())
        self.parent()._layout_widgets(True) # Calling function from labscript_utils.qtwidgets.ToolPalette
        self.hide_button.setIcon(QIcon(':/qtutils/fugue/control-090'))
        self.hide_button.clicked.disconnect()
        self.hide_button.clicked.connect(self.hide_PID)

    def __init__(self, hardware_name, connection_name='-', display_name=None, parent=None, props={}):
        AnalogOutput.__init__(self, hardware_name, connection_name, display_name, False, parent)
        # Create widgets
        self.hidden_widgets = list()
        if "min" in props and "max" in props:
            self.hidden_widgets.append(QLabel(f"Min = {props['min']}V"))
            self.hidden_widgets.append(QLabel(f"Max = {props['max']}V"))
            
        self.hidden_widgets.append(QLabel("PID Ch."))
        self.hidden_widgets[-1].setAlignment(Qt.AlignCenter)
        self.PID = {"Ch": NoStealFocusSpinBox()}
        self.hidden_widgets.append(self.PID['Ch'])
        for param in ["P","I","D"]:
            box = NoStealFocusDoubleSpinBox()
            box.setDecimals(4)
            box.setSingleStep(0.01)
            label = QLabel(param)
            label.setAlignment(Qt.AlignCenter)
            self.hidden_widgets.append(label)
            self.hidden_widgets.append(box)
            self.PID[param] = box
        
        # Add putton in parent layout to show and hide PID details
        self.hide_button = QPushButton()
        self.hide_button.setIcon(QIcon(':/qtutils/fugue/control-270'))
        self.hide_button.clicked.connect(self.show_PID)
        self._layout.addWidget(self.hide_button,1,1)

        # Make/change layout
        grid = QGridLayout()
        for i,widget in enumerate(self.hidden_widgets):
            grid.addWidget(widget,i//2,i%2) 
            widget.setVisible(False)       
        self._layout.removeItem(self._layout.itemAt(2)) # remove vertical spacer from AnalogOutput
        self._layout.addLayout(grid,2,0) 
        self._layout.addItem(QSpacerItem(0,0,QSizePolicy.Minimum,QSizePolicy.MinimumExpanding),3,0)  # add a vertival spacer again

        


        

    


# A simple test!
if __name__ == '__main__':
    import sys
    qapplication = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    button = ADwinAnalogOutPIDWidget("1", "AOUT TEST")
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec_())