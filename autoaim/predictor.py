# -*- coding: utf-8 -*-
"""Predictor Module

This module tell you the truth of the lamps.

Author:
    tccoin
"""


import math
import cv2
import numpy as np
from autoaim import helpers, feature, Feature, DataLoader, pipe
from toolz import curry


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


class Predictor():
    def __init__(self, lamp_weight, pair_weight):
        props, w_lamp = DataLoader().read_csv(lamp_weight)
        _, w_pair = DataLoader().read_csv(pair_weight)
        w_pair = np.array(w_pair).reshape(3, int(len(w_pair[0])/3))
        self.props = props
        self.w_lamp = np.array(w_lamp[0])
        self.w_pair = np.array(w_pair)

    def predict(self, img, mode='red', debug=True, timeout=50, lamp_threshold=0):
        w_lamp = self.w_lamp
        w_pair = self.w_pair
        calcdict = feature.calcdict
        # modes
        if mode == 'red':
            f = Feature(img)
        elif mode == 'blue':
            f = Feature(img, channel=lambda c: cv2.subtract(c[0], c[2]))
        elif mode == 'white':
            f = Feature(img, channel=lambda c: c[0])
        elif mode == 'old':
            f = Feature(img,
                        preprocess=False,
                        channel=lambda c: c[1],
                        binary_threshold_scale=lambda t: (255-t)*0.5+t)
        f.calc(self.props)
        # get x_keys
        x_keys = []
        for prop in self.props:
            for x_key in calcdict.get(prop, []):
                x_keys += [x_key]
        # get x and calc y
        for lamp in f.lamps:
            x = np.array([lamp.x[k] for k in x_keys] + [1])
            lamp.y = sigmoid(x.dot(w_lamp))  # score
        # lamp filter
        f.lamps = [l for l in f.lamps if l.y > lamp_threshold]
        # pairs
        f.calc_pairs()
        for pair in f.pairs:
            x = np.array(pair.x + [1])
            y = x.dot(np.transpose(w_pair))
            pair.y = np.max(y)  # score
            pair.label = np.argmax(y)  # label
        # lamp filter
        f.pairs = [l for l in f.pairs if l.label > 0]
        # debug
        if debug:
            pipe(
                img.copy(),
                # f.mat.copy(),
                # f.binary_mat.copy(),
                f.draw_contours,
                f.draw_bounding_rects,
                # f.draw_texts()(
                #     lambda l: '{:.2f}'.format(l.y)
                # ),
                f.draw_pair_bounding_rects,
                f.draw_pair_bounding_text()(
                    lambda l: '{:.2f}'.format(l.y)
                ),
                curry(helpers.showoff)(timeout=timeout, update=True)
            )
        return f


if __name__ == '__main__':
    for i in range(0, 300, 1):
        img_url = 'data/test12/img{}.jpg'.format(i)
        print('Load {}'.format(img_url))
        img = helpers.load(img_url)

        predictor = Predictor('weight9.csv', 'pair_weight.csv')
        predictor.predict(img, mode='red', timeout=100)
