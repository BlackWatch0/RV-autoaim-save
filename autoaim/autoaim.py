# -*- coding: utf-8 -*-
import cv2
import os

class Autoaim():

    def __init__(self, img):
        if isinstance(img, str):
            self.mat = cv2.imread(img)
        else:
            self.mat = img
        if len(self.mat.shape) == 3:
            self.b, self.g, self.r, = cv2.split(self.mat)

    def show(self):
        cv2.imshow('original image', self.mat)

    def threshold(self, mat=None, winname=None):
        if mat is None:
            mat = self.mat
        ret, thresh = cv2.threshold(mat, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        print('threshold: ', ret)
        if not winname is None:
            cv2.imshow(winname, thresh)
        return thresh

    def canny(self, mat=None, winname=None):
        if mat is None:
            mat = self.mat
        canny = cv2.Canny(mat, 50, 150)
        if not winname is None:
            cv2.imshow(winname, canny)
        return canny

    def getPossibleContours(self, mat=None, winname=None):
        if mat is None:
            mat = self.g
        # binarization
        thresh = self.threshold(mat)
        # find contours
        image,all_contours,hierarchy = cv2.findContours(thresh, cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE) #get the contour
        # find area between 50 and 100000
        possible_contours = []
        for i in range(0, len(all_contours)):
            contour = all_contours[i]
            x,y,w,h = cv2.boundingRect(contour)
            area = w*h
            if area>50 and area<100000:
                possible_contours.append(contour)
        # draw the contours
        if not winname is None:
            _mat = self.mat.copy()
            cv2.drawContours(_mat,possible_contours,-1,(0,255,0),1)
            cv2.imshow(winname, _mat)
        return possible_contours


if __name__ == '__main__':
    autoaim = Autoaim('../data/miao2.jpg')
    autoaim.getPossibleContours(autoaim.g, 'g')
    cv2.waitKey(0)
    cv2.destroyAllWindows()