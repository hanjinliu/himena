# A simple example of using serial communication
# For example, you can connect an Arduino to your PC and use this widget to monitor the
# serial output from the Arduino, just like the Arduino IDE's Serial Monitor. You can
# try it out with simple hardware like a rotary encoder:
# https://arduinogetstarted.com/tutorials/arduino-rotary-encoder

import serial
from serial.tools.list_ports import comports
from qtpy import QtWidgets as QtW
from superqt.utils import thread_worker, GeneratorWorker
from himena import new_window

class QSerialMonitor(QtW.QWidget):
    """A widget that monitors a serial port and displays incoming data."""
    def __init__(self):
        super().__init__()
        self.text_area = QtW.QTextEdit(self)
        self.text_area.setReadOnly(True)
        self.start_stop_btn = QtW.QPushButton("Start", self)
        self.start_stop_btn.clicked.connect(self._toggle_monitoring)
        self.port = QtW.QLineEdit(self)
        self.port.setText("COM3")
        self.baudrate = QtW.QComboBox(self)
        self.baudrate.addItems(["9600", "19200", "38400", "57600"])
        self.device_info = QtW.QLabel()
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(labeled(self.port, "Port:"))
        layout.addWidget(labeled(self.baudrate, "Baudrate:"))
        layout.addWidget(labeled(self.device_info, "Device:"))
        layout.addWidget(self.text_area)
        layout.addWidget(self.start_stop_btn)
        self._worker: GeneratorWorker | None = None
        self.set_device_info()

    def _toggle_monitoring(self):
        if self._worker is None:
            self._worker = self.run_monitor()
            self._worker.start()
            self.start_stop_btn.setText("Stop")
            self._worker.yielded.connect(self._on_data_received)
            self.port.setEnabled(False)
            self.baudrate.setEnabled(False)
        else:
            self._worker.quit()
            self._worker = None
            self.start_stop_btn.setText("Start")
            self.port.setEnabled(True)
            self.baudrate.setEnabled(True)

    def _on_data_received(self, line: str):
        if self._worker is not None and line:
            self.text_area.append(line)

    @thread_worker
    def run_monitor(self):
        with serial.Serial(
            self.port.text(),
            int(self.baudrate.currentText()),
            timeout=0.2,
        ) as ser:
            while True:
                line = ser.readline().decode()
                yield line.strip()

    def set_device_info(self):
        for port in comports():
            if port.device == self.port.text():
                self.device_info.setText(f"<b>{port.description}</b>")
                return
        else:
            self.device_info.setText("Not detected")

def labeled(widget: QtW.QWidget, label: str) -> QtW.QWidget:
    container = QtW.QWidget()
    layout = QtW.QHBoxLayout(container)
    layout.addWidget(QtW.QLabel(label))
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    return container

if __name__ == "__main__":
    ui = new_window()
    mon = QSerialMonitor()
    ui.add_widget(mon, title="Serial Monitor")
    ui.show(run=True)
