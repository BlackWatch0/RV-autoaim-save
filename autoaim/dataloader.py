# -*- coding: utf-8 -*-
"""Data Loader Module

This module save the features to a csv file.

Author:
    tccoin
"""

import os
import csv
import math
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import random
from toolz import pipe, curry
from autoaim import feature, Feature, helpers

data_path = os.path.abspath(__file__ + '/../../data')


class DataLoader():

    def __init__(self, debug=False):
        self.debug = debug

    # ===================
    # Dataset Function
    # ===================

    def load_datasets(self, datasets, props, filename='test', cut=0.8):
        '''Example input:
        datasets = ['test0', 'test1', ...]
        props = ['contour', 'bounding_rect', ...]
        '''
        self.props = props
        header = self.generate_header()
        self.filename = filename
        self.new_csv(self.join('lamp', 'train'), header)
        self.new_csv(self.join('pair', 'train'), header)
        self.new_csv(self.join('lamp', 'test'), header)
        self.new_csv(self.join('pair', 'test'), header)
        for dataset in datasets:
            dataset_path = data_path+'/'+dataset
            files = [x for x in os.listdir(
                dataset_path) if os.path.isfile(dataset_path+'/'+x)]
            random.shuffle(files)
            cut_len = int(cut*len(files))
            self.load_images('train', dataset, files[0:cut_len])
            self.load_images('test', dataset, files[cut_len:-1])

    def load_images(self, data_type, dataset, images):
        for image in images:
            feature = self.load_img(dataset, image)
            if feature:
                for lamp in feature.lamps:
                    row = [x for x in lamp.x.values()] + [int(lamp.bingo)]
                    self.append_csv(self.join('lamp', data_type), row)
                for pair in feature.pairs:
                    row = pair.x + [int(pair.bingo)]
                    self.append_csv(self.join('pair', data_type), row)

    def load_img(self, dataset, image):
        '''return `exit`'''
        props = self.props + ['bounding_rect']
        # load labels
        labels = self.load_label(dataset, image)
        # load image
        img_path = os.path.join(data_path, dataset, image)
        img = helpers.load(img_path)
        # calc features
        feature = Feature(img)
        feature.calc(props)
        feature.calc_pairs()
        # label the lamps
        lamps = feature.lamps
        pairs = feature.pairs
        for lamp in lamps:
            lamp.bingo = False
            for labeled_lamp in labels[0]:
                if self.__is_in(lamp.bounding_rect, labeled_lamp):
                    lamp.bingo = True
                    break
        for pair in pairs:
            pair.bingo = 0
            for labeled_pair in labels[1]:
                if self.__is_in(pair.bounding_rect, labeled_pair):
                    pair.bingo = 1
                    break
            for labeled_pair in labels[2]:
                if self.__is_in(pair.bounding_rect, labeled_pair):
                    pair.bingo = 2
                    break
        print(
            '{}/{}: {} lamps, {} pairs'
            .format(dataset, image, len(lamps), len(pairs))
        )
        if self.debug:
            pipe(img.copy(),
                 # feature.draw_contours,
                 feature.draw_bounding_rects,
                 self.draw_labeled_lamps()(lamps),
                 self.draw_bingo_lamps()(feature),
                 helpers.showoff
                 )
        return feature

    def load_label(self, dataset, file):
        labels = [[], [], []]  # lamp, small, large

        # load xml
        label = os.path.splitext(file)[0]
        label_path = os.path.join(
            data_path, dataset, 'label', label+'.xml')
        try:
            tree = ET.ElementTree(file=label_path)
        except:
            print('>  Label file "{}"  not found!'.format(label_path))
            return labels
        root = tree.getroot()

        # classify
        for child in root:
            if child.tag == 'object':
                name = child[0].text
                rect = (child[4][0], child[4][2], child[4][1],
                        child[4][3])  # xmin,xmax,ymin,ymax
                rect = [int(x.text) for x in rect]
                if name == 'lamp':
                    labels[0].append(rect)
                elif name == 'pair1':
                    labels[1].append(rect)
                elif name == 'pair2':
                    labels[2].append(rect)
        return labels

    def __is_in(self, rect, labeled_rect):
        margin = 20
        x, y, w, h = rect
        diff = abs(np.array([x, x+w, y, y+h]) - np.array(labeled_rect))
        return len(np.where(diff > margin)[0]) == 0

    def join(self, str1, str2):
        return self.filename+'_'+str1+'_'+str2+'.csv'

    def generate_header(self):
        '''This method works together with feature.calcdict.'''
        row = []
        for props in self.props:
            if props in feature.calcdict:
                row += feature.calcdict[props].keys()
        row += ['bingo']
        return row

    # ===================
    # Debug Function
    # ===================

    def draw_bingo_lamps(self):
        '''Usage:dataloader.draw_bingo_lamps()(feature)'''
        def draw(feature, img):
            lamps = feature.lamps
            boom_rects = [x.bounding_rect for x in lamps if not x.bingo]
            bingo_rects = [x.bounding_rect for x in lamps if x.bingo]
            for rect in boom_rects:
                x, y, w, h = rect
                cv2.rectangle(img, (x, y), (x+w, y+h), (200, 0, 200), 1)
            for rect in bingo_rects:
                x, y, w, h = rect
                cv2.rectangle(img, (x, y), (x+w, y+h), (200, 0, 0), 2)
            return img
        return curry(draw)

    def draw_labeled_lamps(self):
        '''Usage:dataloader.draw_labeled_lamps()(rects)'''
        def draw(rects, img):
            for rect in rects:
                xmin, xmax, ymin, ymax = rect
                cv2.rectangle(img, (xmin, ymin), (xmax, ymax),
                              (0, 0, 200), 3)
            return img
        return curry(draw)

    # ===================
    # CSV Function
    # ===================

    def new_csv(self, filename, row):
        '''Create a new scv file and write the table's header to it.'''
        with open(data_path + '/'+filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(row)

    def append_csv(self, filename, row):
        with open(data_path + '/'+filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=' ',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(row)

    def read_csv(self, filename):
        with open(data_path + '/'+filename, 'r') as csvfile:
            rows = list(csv.reader(csvfile))
            header = rows[:1][0][0].split(' ')
            table = [[float(item) for item in row[0].split(' ')]
                     for row in rows[1:]]
            return header, table


if __name__ == '__main__':
    props = feature.enabled_props
    datasets = [
        'test12',
    ]
    dataloader = DataLoader(debug=False)
    dataloader.load_datasets(datasets, props)
