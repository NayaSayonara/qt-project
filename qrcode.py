import os, sys, struct
import pyqrcode
import io

'''

qr = Qrcode('www.google.com')

pixmap = QPixmap()
pixmap.loadFromData(qr.render2ram(), 'png')

lbl = QLabel(self)
lbl.setPixmap(pixmap)


'''


class Qrcode:

    def __init__(self, data):
        self._data = data
        self._qr = pyqrcode.create(str(self._data), error='M')

    def render2ram(self):
        buffer = io.BytesIO()
        self._qr.png(buffer, scale=10)
        return buffer.getvalue()

    def render2file(self, filename):
        self._qr.png(filename, scale=5)



