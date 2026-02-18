#####################################################################
#                                                                   #
# ADwinProII/blacs_tabs.py                                          #
#                                                                   #
# Copyright 2022, TU Vienna                                         #
#                                                                   #
# Implementation of the ADwin-Pro II for the labscript-suite,       #
# used in the Léonard lab for Experimental Quantum Information.     #
#                                                                   #
#####################################################################

import os
from labscript import LabscriptError
from blacs.device_base_class import DeviceTab, define_state, MODE_BUFFERED, MODE_MANUAL, MODE_TRANSITION_TO_BUFFERED, MODE_TRANSITION_TO_MANUAL
from blacs.output_classes import DO
from labscript_utils.qtwidgets.digitaloutput import DigitalOutput, InvertedDigitalOutput
from .qtwidgets.analoginput import ADwinAnalogInput
from .qtwidgets.analogoutput_PID import ADwinAnalogOutPIDWidget
from .ADwin_utils import get_channel_from_BLACS_name
from qtutils.qt import QtWidgets, QtGui
from qtutils import UiLoader


class ADwinProIITab(DeviceTab):
    def initialise_GUI(self):
        # self.event_queue.logging_enabled = True
        connection_table = self.settings['connection_table']
        props = connection_table.find_by_name(self.device_name).properties

        DO_widgets = []
        AO_widgets = []
        AI_widgets = []
        self._AI = {}
        DIO_ADwin_DataNo = [] # Get the DIO modules and their address to know which data to write in ADwin

        # We cannot use all predefined functions of DeviceTab for creating the widgets, becasue
        # the outputs are no child devices of the ADwin directly, but from its modules.
        module_properties = {} # collect all module properties for Worker 
        for address, module_name in props["modules"].items():
            module = connection_table.find_by_name(module_name)
            module_props = module.properties
            module_properties[address] = module_props
            module_widgets = {}

            if module.device_class == "ADwinDIO32":
                # Create widget for digital outputs
                DIO_ADwin_DataNo.append((module_name,10*int(module_props["module_address"])))
                for DO_channel in module_props["DO_ports"]:
                    BLACS_name = f"{module_props['module_address']}/{DO_channel}"
                    device = self.get_child_from_connection_table(module_name,DO_channel)
                    inverted = bool(device.properties.get('inverted', False)) if device else False
                    connection_name = device.name if device else '-'
                    self._DO[BLACS_name] = DO(BLACS_name, connection_name, module_name, self.program_device, self.settings)
                    if not inverted:
                        widget = DigitalOutput('%s\n%s'%(DO_channel,connection_name))
                    else:
                        widget = InvertedDigitalOutput('%s\n%s'%(DO_channel,connection_name))
                    self._DO[BLACS_name].add_widget(widget, inverted=inverted)
                    module_widgets[BLACS_name] = widget
                DO_widgets.append((module_name + " Digital Outputs",module_widgets,get_channel_from_BLACS_name))

            elif module.device_class == "ADwinAO8":
                # Create widget for analog outputs (with custom PID control for manual mode)
                for AO_channel in range(1,module_props["num_AO"]+1):  
                    output = module.find_child(module_name,str(AO_channel))
                    if output is not None:
                        limits = output.properties["limits"]
                    else:
                        limits = (module_props["min_V"],module_props["max_V"])
                    AO_props = {
                        'base_unit': 'V',
                        'min': limits[0],
                        'max': limits[1],
                        'step': module_props["step_size"],
                        'decimals': 5
                    }

                    BLACS_name = f"{module_props['module_address']}/{AO_channel}"              
                    self._AO[BLACS_name] = self._create_AO_object(module_name,BLACS_name,str(AO_channel),AO_props)
                    display_name=f"{str(AO_channel)}\n{self._AO[BLACS_name]._connection_name}"
                    module_widgets[BLACS_name] = ADwinAnalogOutPIDWidget(BLACS_name, display_name=display_name, props=AO_props)
                    self._AO[BLACS_name].add_widget(module_widgets[BLACS_name])
                    for PID_widget in module_widgets[BLACS_name].PID.values():
                        PID_widget.valueChanged.connect(lambda: self.program_device())
                AO_widgets.append((module_name + " Analog Outputs",module_widgets,get_channel_from_BLACS_name))

            elif module.device_class == "ADwinAI8":
                # Create widget for analog inputs
                for AI_channel in range(1,module_props["num_AI"]+1):
                    BLACS_name = f"{module_props['module_address']}/{AI_channel}"
                    device = self.get_child_from_connection_table(module_name,str(AI_channel))
                    connection_name = device.name if device else '-'
                    scale_factor = device.properties["scale_factor"] if device else 1
                    module_widgets[BLACS_name] = ADwinAnalogInput(BLACS_name,str(AI_channel),connection_name,scale_factor=scale_factor)
                    self._AI.setdefault(module_props['module_address'],{},)
                    self._AI[int(module_props['module_address'])][AI_channel] = module_widgets[BLACS_name]
                AI_widgets.append((module_name + " Analog Inputs", module_widgets, get_channel_from_BLACS_name))


        self.create_worker(
            "main_worker",
            "user_devices.ADwinProII.blacs_workers.ADwinProIIWorker",
            {
                "process_buffered" : props["process_buffered"],
                "process_manual" : props["process_manual"],
                "DIO_ADwin_DataNo" : DIO_ADwin_DataNo,
                "modules" : props["modules"],
                "module_props" : module_properties,
                "mock" : props["mock"]
            }
        )
        self.primary_worker = "main_worker"

        # Set the capabilities of this device
        self.supports_remote_value_check(False)
        self.supports_smart_programming(True)

        # Load UI for workload
        self.ui_workload = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),"./qtwidgets/Workload.ui"))
        
        # Load UI for ADwin processes
        ui = UiLoader().load(os.path.join(os.path.dirname(os.path.realpath(__file__)),"./qtwidgets/Process.ui"))
        # Set process files from props (from globals) and set button behaviour
        ui.lineEdit_buffered_file.setText(props["process_buffered"])
        ui.lineEdit_manual_file.setText(props["process_manual"])
        self.process_files_location = os.path.dirname(props["process_buffered"])
        ui.toolButton_buffered_file.clicked.connect(lambda: self.on_select_process_file_clicked(ui.lineEdit_buffered_file))
        ui.toolButton_manual_file.clicked.connect(lambda: self.on_select_process_file_clicked(ui.lineEdit_manual_file))
        # Connect signals for buttons
        ui.pushButton_load_buffered.clicked.connect(lambda: self.load_process(ui.lineEdit_buffered_file.text(),"buffered"))
        ui.pushButton_start_buffered.clicked.connect(lambda: self.start_process(ui.lineEdit_buffered_file.text()))
        ui.pushButton_stop_buffered.clicked.connect(lambda: self.stop_process(ui.lineEdit_buffered_file.text()))
        ui.pushButton_load_manual.clicked.connect(lambda: self.load_process(ui.lineEdit_manual_file.text(),"manual"))
        ui.pushButton_start_manual.clicked.connect(lambda: self.start_process(ui.lineEdit_manual_file.text()))
        ui.pushButton_stop_manual.clicked.connect(lambda: self.stop_process(ui.lineEdit_manual_file.text()))
        # Add icons
        ui.toolButton_buffered_file.setIcon(QtGui.QIcon(':/qtutils/fugue/folder-open-document'))
        ui.toolButton_manual_file.setIcon(QtGui.QIcon(':/qtutils/fugue/folder-open-document'))
        ui.pushButton_load_buffered.setIcon(QtGui.QIcon(':/qtutils/fugue/arrow-transition'))
        ui.pushButton_start_buffered.setIcon(QtGui.QIcon(':/qtutils/fugue/control'))
        ui.pushButton_stop_buffered.setIcon(QtGui.QIcon(':/qtutils/fugue/control-stop-square'))
        ui.pushButton_load_manual.setIcon(QtGui.QIcon(':/qtutils/fugue/arrow-transition'))
        ui.pushButton_start_manual.setIcon(QtGui.QIcon(':/qtutils/fugue/control'))
        ui.pushButton_stop_manual.setIcon(QtGui.QIcon(':/qtutils/fugue/control-stop-square'))
        self.ui_process = ui

        # Place UI widgets
        hardware_widgets = {"Workload":self.ui_workload, "Process":self.ui_process}
        all_widgets = [*DO_widgets,*AO_widgets, *AI_widgets, ("Hardware Control", hardware_widgets)]
        if props["mock"]:
            for i,group in enumerate(all_widgets):
                all_widgets[i] = (f"MOCK: {group[0]}", *group[1:])
        self.auto_place_widgets(*all_widgets)


        # Create dict for reading analog input values (fill them with None)
        self.AIN_values = {}
        for module in self._AI:
            for port in self._AI[module]:
                self.AIN_values.setdefault(module, {})
                self.AIN_values[module][port] = None
        
        # Start AIN acquisition in manual mode (read values every 3 seconds)
        self.statemachine_timeout_add(3000, self.update_AIN_values)
    

    @define_state(MODE_BUFFERED,True)
    def start_run(self,notify_queue):
        """Start run if the ADwin is the master pseudoclock"""
        yield(self.queue_work(self._primary_worker,'start_run'))
        self.wait_until_done(notify_queue)
        # TODO: If not master pseudocock, the process would have to be somewhere else.


    @define_state(MODE_BUFFERED, True)
    def wait_until_done(self, notify_queue):
        done = yield(self.queue_work(self.primary_worker, 'wait_until_done'))
        # Experiment is over. Tell the queue manager about it:
        if done:
            notify_queue.put('done')
        else:
            raise LabscriptError("ADwin was not finished after waiting expected time for shot execution!")


    def get_front_panel_values(self):
        # Call function from base class
        values = super().get_front_panel_values()
        # Extended by getting the GUI settings for the PIDs
        for channel,item in self._AO.items():
            PID = item._widgets[0].PID
            values[channel] = {"output":values[channel]}
            for subch in PID:
                values[channel][subch] = PID[subch].value()
            values[channel]["min"] = item._limits[0]
            values[channel]["max"] = item._limits[1]
        return values


    @define_state(MODE_MANUAL,True)
    def update_AIN_values(self):
        """Query for current analog inputs from worker and update them in the wigdets."""
        self.AIN_values = yield(self.queue_work(self._primary_worker, "get_AIN_values", self.AIN_values))
        # Set labels to returned values
        for module in self._AI:
            for port in self._AI[module]:
                self._AI[module][port].set_value(self.AIN_values[module][port])


    @define_state(MODE_BUFFERED,False)
    def transition_to_manual(self,notify_queue,program=False):
        DeviceTab.transition_to_manual(self,notify_queue,program=False)
        # Get workload during shot and display it in the hardware widget.
        workload,free_cachable,free_uncachable = yield(self.queue_work(self._primary_worker, "get_workload"))
        self.ui_workload.workload_label.setText(f"{workload*100:.2f} %")
        self.ui_workload.free_cachable_label.setText(f"{free_cachable} kByte")
        self.ui_workload.free_uncachable_label.setText(f"{free_uncachable*1e-3:.3f} MByte")
        self.statemachine_timeout_add(3000, self.update_AIN_values)


    @define_state(MODE_MANUAL,True)
    def transition_to_buffered(self,h5_file,notify_queue): 
        self.statemachine_timeout_remove(self.update_AIN_values)
        DeviceTab.transition_to_buffered(self,h5_file,notify_queue)


    # Functions for manual GUI control
    @define_state(MODE_MANUAL,False)
    def load_process(self, process, process_type):
        yield(self.queue_work(self._primary_worker,'load_process',process,process_type))

    @define_state(MODE_MANUAL,False)
    def start_process(self, process):
        yield(self.queue_work(self._primary_worker,'start_process',process))

    @define_state(MODE_MANUAL,False)
    def stop_process(self, process):
        yield(self.queue_work(self._primary_worker,'stop_process',process))

    @define_state(MODE_MANUAL,False)
    def on_select_process_file_clicked(self,lineEdit):
        file = QtWidgets.QFileDialog.getOpenFileName(self.ui_process,
                                                    'Select ADwin process file',
                                                    self.process_files_location,
                                                    "ADwin binary files (*.TC*)")
        if type(file) is tuple:
            file, _ = file

        if not file:
            # User cancelled selection
            return
        # Convert to standard platform specific path, otherwise Qt likes forward slashes:
        file = os.path.abspath(file)
        if not os.path.isfile(file):
            error_dialog("No such file %s." % file)
            return
        # Save the containing folder for use next time we open the dialog box:
        self.process_files_location = os.path.dirname(file)
        # Write the file to the lineEdit:
        lineEdit.setText(file)
