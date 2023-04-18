# -*- coding: utf-8 -*-
"""保存图像

Author:
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__))+'/../')
from autoaim import Camera, helpers
import cv2
import time


camera = Camera(0, 'daheng')
camera.init((1280, 1024))
count = 0
maxcount = 100
interval = 0.2
print('push F to capturing')
lasttime = time.time()
fps_last_timestamp = time.time()
fpscount = 0
fps = 0
while count < maxcount:
    success, image = camera.get_image()
    if success:
        key = helpers.uccu(image, 1, update=True)
        if time.time()-lasttime >= interval and key==102:
            lasttime = time.time()
            cv2.imwrite('data/capture/img{}.jpg'.format(count), image)
            count += 1

        fpscount = fpscount % 100 + 1
        if fpscount == 100:
            fps = 100/(time.time() - fps_last_timestamp+0.0001)
            fps_last_timestamp = time.time()
            print('fps: ', fps)
    else:
        print('ERROR')
        break
