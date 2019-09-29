# -*- coding: utf-8 -*-
import unittest
import os
import autoaim
from autoaim import *

data1 = [0xA5, 0x03, 0x00, 0x3E, 0x86, 0x01,
         0x00, 0x01, 0xBC, 0x02, 0x0F, 0x74]

isTravis = bool(os.environ.get('TRAVIS_PYTHON_VERSION'))


class AutoAimTestSuite(unittest.TestCase):

    def test_crc8_checksum(self):
        crc = telegram.get_crc8_checksum(data1[0:4])
        assert crc == data1[4]

    def test_crc16_checksum(self):
        crc = telegram.get_crc16_checksum(data1[0:10])
        assert crc == (data1[10]+(data1[11] << 8))

    def test_telegram_pack(self):
        test_packet = telegram.pack(
            0x0001, [bytes([0x01, 0xBC, 0x02])], seq=0x3E)
        assert bytes(data1) == test_packet

    def test_telegram_unpack(self):
        unpacker = telegram.Unpacker()
        info = {}
        for byte in bytes(data1):
            info = unpacker.send(byte)
        assert info['state'] == 'EOF'

    @unittest.skipUnless(telegram.port_list and (not isTravis), 'No serial port available.')
    def test_telegram_send(self):
        print('--- telegram ---')
        x = telegram.send(bytearray(data1))
        print(x)
        assert x

    def test_aimmat(self):
        '''calculate features using test8'''
        for i in range(0, 5, 1):
            img_url = 'data/test8/img{}.jpg'.format(i)
            img = helpers.load(img_url)
            aimmat = AimMat(img)
            aimmat.calc([
                'contours',
                'bounding_rects',
                'rotated_rects',
                'greyscales',
                'point_areas',
            ])

    def test_predictor(self):
        '''predicte using test8'''
        for i in range(0, 5, 1):
            img_url = 'data/test8/img{}.jpg'.format(i)
            img = helpers.load(img_url)
            predictor = Predictor(
                'weights/lamp.csv', 'weights/pair.csv', 'weights/angle.csv')
            aimmat = predictor.predict(img, mode='red', debug=False)
            lamps = aimmat.lamps
            lamps = [x for x in lamps if x.y > 0.5]

    @helpers.time_this
    def test_fps(self):
        '''predict 100 image from test9'''
        for i in range(0, 100, 1):
            img_url = 'data/test9/img{}.jpg'.format(i)
            img = helpers.load(img_url)
            # predictor = Predictor('weights/lamp.csv', 'weights/pair.csv', 'weights/angle.csv')
            # lamps = predictor.predict(img, mode='red', debug=False)
            # lamps = [x for x in lamps if x.y > 0.5]


if __name__ == '__main__':
    unittest.main()
