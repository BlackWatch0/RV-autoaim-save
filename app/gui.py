
from autoaim import helpers, Camera, Config, Predictor
from toolz import pipe, curry
import cv2
import time
import numpy as np
from PyQt5.QtCore import Qt, pyqtSlot, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QMainWindow, QWidget, QPushButton, QVBoxLayout, QApplication, QSlider, QLabel, QHBoxLayout, QLineEdit


class CameraThread(QThread):
    signal = pyqtSignal(object)

    def __init__(self, camera_index):
        super().__init__()
        self.camera = Camera(camera_index)
        self.capture = self.camera.capture
        self.capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        self.capture.set(cv2.CAP_PROP_EXPOSURE, 1)
        self.delay = 200

    def run(self):
        while True:
            #     ret, img = self.capture.read()
            #     if ret:
            #         self.image = QImage(
            #             img.data, img.shape[1], img.shape[0], QImage.Format_RGB888).rgbSwapped()
            #         self.signal.emit(self.image)
            for i in range(0, 240):
                img_url = 'data/test19/img{}.jpg'.format(i)
                image = helpers.load(img_url)
                image = cv2.resize(image,(0,0),fx=2,fy=2)
                self.signal.emit(image)
                time.sleep(self.delay/1000)

class QSetting(QWidget):
    def __init__(self, name, scope, default, callback):
        super(QSetting, self).__init__()

        self.callback = callback

        self.layout = QHBoxLayout()
        # self.layout.addStretch(1)

        self.label = QLabel(name)
        self.layout.addWidget(self.label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setTickPosition(QSlider.TicksLeft)
        self.slider.setRange(*scope)
        self.slider.setValue(default)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.layout.addWidget(self.slider)

        self.textbox = QLineEdit(self)
        self.layout.addWidget(self.textbox)
        self.textbox.setFixedWidth(50)
        self.textbox.setText(str(default))
        self.textbox.textChanged.connect(self.textbox_value_changed)

        self.setLayout(self.layout)

        self.lock = False
    def slider_value_changed(self, value):
        self.textbox.setText(str(value))
        self.callback(value)
    def textbox_value_changed(self, value):
        self.slider.setValue(int(value))

class DisplayImageWidget(QWidget):
    def __init__(self, callback):
        super(DisplayImageWidget, self).__init__()

        self.layout = QVBoxLayout()

        self.start_button = QPushButton('Start')
        self.start_button.clicked.connect(self.start_capture)
        self.layout.addWidget(self.start_button)

        self.image_frame = QLabel()
        self.layout.addWidget(self.image_frame)

        self.setLayout(self.layout)

        self.config = Config(
            {'target_color': 'red', 'hsv_lower_value': 100})
        self.predictor = Predictor(self.config)
        self.toolbox = self.predictor.toolbox
        self.callback = callback

    def start_capture(self):
        self.callback()
        self.start_button.setParent(None)
        self.camera_thread = CameraThread(0)
        self.camera_thread.signal.connect(self.show_image)
        self.camera_thread.start()

    def set_delay(self, value):
        self.camera_thread.delay = 1000/value
        self.update()

    def set_hsv(self, value):
        self.config.hsv_lower_value = value
        self.update()

    def show_image(self, image):
        self.image = image
        image = self.process(image)
        image = QImage(
            image.data, image.shape[1], image.shape[0], QImage.Format_RGB888).rgbSwapped()
        self.image_frame.setPixmap(QPixmap.fromImage(image))

    def update(self):
        self.show_image(self.image)

    def process(self, img):
        self.predictor.predict(img)
        return pipe(img,
                    self.toolbox.draw_contours,
                    self.toolbox.draw_bounding_rects,
                    # self.toolbox.only_that_pair,
                    self.toolbox.draw_pair_bounding_rects
                    )


class StartWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutoAim Console")

        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        self.widget_image = DisplayImageWidget(self.show_settings)
        self.layout.addWidget(self.widget_image)

    def show_settings(self):
        self.delay_setting = QSetting('fps', (1,20), 5, self.widget_image.set_delay)
        self.layout.addWidget(self.delay_setting)

        self.hsv_setting = QSetting('hsv', (46,255), 100, self.widget_image.set_hsv)
        self.layout.addWidget(self.hsv_setting)


if __name__ == '__main__':
    app = QApplication([])
    window = StartWindow()
    window.show()
    app.exit(app.exec_())
