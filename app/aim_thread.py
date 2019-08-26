import autoaim
import cv2
import time
import threading
import sys
from toolz import curry, pipe


# Global var
new_img = None
new_packet = None
aim = True
ww = 1280
hh = 720
# ww = 640
# hh = 360

def miao(val,minval,maxval):
    return min(max(val,minval),maxval)


def predict_movement(last, new):
    del last[0]
    last += [new]
    return sum(last)/len(last)


def predict_clear(last):
    return [0 for i in range(len(last))]


def moving_average(last, new):
    empty = False
    for x in last:
        if not x == 0:
            empty = True
    if empty:
        for i in range(len(last)):
            last[i] = new
    else:
        del last[0]
        last += [new]
    return sum(last)/len(last)


def dead_region(val, range):
    # dead region
    if val > -range and val < range:
        return 0
    else:
        return val


pid_output_i = 0
last_error = None


def pid_control(target, feedback, pid_args=None):
    global pid_output_i, last_error
    if pid_args is None:
        pid_args = (1, 0.01, 4, 0.5)
    p, i, d, i_max = pid_args
    error = target-feedback
    if last_error is None:
        last_error = error
    pid_output_p = error*p
    pid_output_i += error*i
    pid_output_i = min([max([pid_output_i, -i_max]), i_max])
    pid_output_d = (error - last_error)*d
    return pid_output_p+pid_output_i+pid_output_d


def load_img():
    # set up camera
    global aim, new_img, ww, hh
    camera = autoaim.Camera(0)
    capture = camera.capture
    capture.set(3, ww)
    capture.set(4, hh)
    capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
    capture.set(cv2.CAP_PROP_EXPOSURE, 1)
    while aim:
        suc, new_img = capture.read()


def send_packet():
    global new_packet
    while True:
        if new_packet is None:
            time.sleep(0.001)
            continue
        packet = new_packet
        new_packet = None
        # print(packet)
        autoaim.telegram.send(packet, port='/dev/ttyUSB0')

def aim_enemy():
    def aim(serial=True, lamp_weight='weight9.csv', pair_weight='pair_weight.csv', angle_weight='angle_weight.csv', mode='red', gui_update=None):
        ##### set up var #####
        global aim, new_img, new_packet, ww, hh
        # config
        threshold_target_changed = 0.5
        distance_to_laser = 12
        x_fix = -15
        threshold_shoot = 0.03
        threshold_position_changed = 70
        # autoaim
        track_state = 1  # 0:tracking, 1:lost
        predictor = autoaim.Predictor(lamp_weight, pair_weight, angle_weight)
        last_pair = None
        pair = None
        height_record_list = ([0 for i in range(10)])
        predict_list = ([0 for i in range(1)], [0 for i in range(1)])
        y_fix = 0
        predict1 = (0, 0)
        predict2 = (0, 0)
        packet_seq = 0
        shoot_it = 0
        target = (ww/2, hh/2)
        target_yfix = (ww/2, hh/2)
        target_yfix_pred = (ww/2, hh/2)
        output = (0, 0)
        camera_movement = (0, 0)

        # fps
        fps_last_timestamp = time.time()
        fpscount = 0
        fps = 0
        while True:
            ##### load image #####

            if new_img is None:
                time.sleep(0.001)
                continue
            img = new_img
            new_img = None

            ##### locate target #####

            feature = predictor.predict(
                img,
                mode=mode,
                debug=False,
                lamp_threshold=0.01
            )
            # filter out the true lamp
            lamps = feature.lamps
            pairs = feature.pairs
            # sort by confidence
            lamps.sort(key=lambda x: x.y)
            pairs.sort(key=lambda x: x.y)

            ##### analysis target #####

            # estimate camera movement
            _x = output[0]
            camera_movement_x = 76.498*_x*_x + 9.5919*_x
            camera_movement_y = 0
            if _x<0:
                camera_movement_x *= -1
            camera_movement = (camera_movement_x,camera_movement_y)

            # logic of losing target
            if len(lamps) == 0:
                # target lost
                track_state = 1
                x, y, w, h = (0, 0, 0, 0)
                last_pair = None
                last_target = target
                target = (ww/2, hh/2)
                target_yfix = (ww/2, hh/2)
                target_yfix_pred = (ww/2, hh/2)
                shoot_it = 0
            else:
                # target found
                x, y, w, h = (0, 0, 0, 0)
                pair = None
                if len(pairs) > 1:
                    pair = None
                    # get track score
                    pairid = 0
                    for pair in pairs:
                        pairid += 1
                        x1, y1, w1, h1 = pair.bounding_rect
                        x_diff = abs(target[0]-camera_movement[0]-(x1+w1/2))
                        y_diff = abs(target[1]-camera_movement[1]-(y1+h1/2))
                        target_distance = -(x_diff*x_diff + y_diff*y_diff)/5000
                        x_diff = abs(x1+w1/2-ww/2)
                        y_diff = abs(y1+h1/2-hh/2)
                        center_distance = -(x_diff*x_diff + y_diff*y_diff)/5000
                        distance = h1/30
                        angle = -abs(pair.angle)/35
                        label = pair.label*-2
                        score = 0
                        if track_state == 0:
                            score = pair.y*5+target_distance+label+distance
                        else:
                            score = pair.y*5+center_distance+label+distance+angle
                        pair.score = score
                        pair.pairid = pairid
                        # print([pairid, pair.y, target_distance, angle,label, distance, score])
                    # reset track state
                    track_state = 0
                    # decide the pair
                    pairs = sorted(pairs,key=lambda x:x.score)
                    last_pair = pair
                    pair = pairs[-1]
                    x, y, w, h = pair.bounding_rect
                    feature.pairs = [p for p in pairs if p.label==0]
                    feature.pairs = [pair]
                elif len(pairs) == 1:
                    track_state = 0
                    last_pair = pair
                    pair = pairs[0]
                    pair.score = 6.66
                    pair.pairid = 1
                    x, y, w, h = pair.bounding_rect
                elif len(lamps) > 1:
                    track_state = 1
                    x1, y1, w1, h1 = lamps[-1].bounding_rect
                    x2, y2, w2, h2 = lamps[-2].bounding_rect
                    x = (x1+x2)/2
                    y = (y1+y2)/2
                    w = (w1+w2)/2
                    h = (h1+h2)/2
                elif len(lamps) == 1:
                    track_state = 1
                    x, y, w, h = lamps[0].bounding_rect

                # detect pair changed
                if not last_pair is None and not pair is None:
                    _ = abs(last_pair.y-pair.y)
                    over_threshold = _ > threshold_target_changed
                    type_changed = not pair.label == last_pair.label
                    _1 = last_pair.bounding_rect[0] + last_pair.bounding_rect[2]/2
                    _2 = pair.bounding_rect[0]+pair.bounding_rect[2]/2
                    position_changed = abs(_1-_2) > threshold_position_changed
                    if over_threshold or type_changed or position_changed:
                        track_state = 1

                h = moving_average(height_record_list, h)

                # distance
                if ww == 1280:
                    # d = 106.56*(h**-1.127) # 0802早热身赛 (blue)
                    # 英雄
                    # if mode == 'blue':
                    #     d = 73.7*(h**-0.972)
                    # else:
                    #     d = 72.472*(h**-1.027)
                    # 步兵 (just for my robot)
                    d = 257.28*(h**-1.257)


                # antigravity
                y_fix = 0
                # y_fix -= (2.75*d*d -1.6845*d - 0.4286)/5.5*h # hero
                y_fix -= min(1.4777*d*d + -3.532*d - 2.1818,8)/5.5*h # infantry
                # y_fix -= min(1.4777*d*d + -3.532*d - 2.1818,8)/5.5*h # infantry
                print(d, y_fix)

                # distance between camera and barrel
                y_fix -= h/5.5*distance_to_laser

                # set target
                last_target = target
                target = (x+w/2, y+h/2)
                target_yfix = (x+w/2+x_fix, y+h/2+y_fix)

                # motion predict
                if not predict1[0] == 0:
                    lastPredict1 = predict1
                    predict1 = (
                        predict_movement(
                            predict_list[0],
                            target[0] - last_target[0]
                        ),
                        0
                    )
                    predict2 = (predict1[0]-lastPredict1[0],0)
                else:
                    predict1 = (
                        predict_movement(
                            predict_list[0],
                            target[0] - last_target[0]
                        ),
                        0
                    )
                    predict2 = (0,0)

                target_yfix_pred = (target_yfix[0]+predict1[0]*10+predict2[0]*5, target_yfix[1])

                # update track state
                if track_state == 1:
                    predict_clear(predict_list[0])
                    predict_clear(height_record_list)
                    print('Target lost')

                ##### set kinestate #####
                # x = target_yfix[0]/ww - 0.5
                # y = target_yfix[1]/hh - 0.5
                x = target_yfix_pred[0]/ww - 0.5
                y = target_yfix_pred[1]/hh - 0.5

                # decide to shoot
                if abs(x)<threshold_shoot and abs(y)<threshold_shoot and track_state==0:
                    shoot_it = 1
                else:
                    shoot_it = 0

            ##### serial output #####
            if serial:
                output = [float(x*5), float(-y*3.5)]
                output = [miao(output[0], -1.5, 1.5),miao(output[1], -1.2, 1.2)]
                print(output)
                new_packet = autoaim.telegram.pack(
                    0x0401, [*output, bytes([shoot_it])], seq=packet_seq)
                packet_seq = (packet_seq+1) % 256

            ##### calculate fps #####
            fpscount = fpscount % 10 + 1
            if fpscount == 10:
                fps = 10/(time.time() - fps_last_timestamp)
                fps_last_timestamp = time.time()
                # print("fps: ", fps)

            ##### GUI #####
            if (not gui_update is None) and gui_update(fpscount):
                # print("out: ", x, y, shoot_it)
                # print("height: ", h, w)
                pipe(
                    img.copy(),
                    # feature.mat.copy(),
                    # feature.binary_mat.copy(),
                    feature.draw_contours,
                    feature.draw_bounding_rects,
                    feature.draw_texts()(lambda l: '{:.2f}'.format(l.bounding_rect[3])),
                    # feature.draw_texts()(
                    #     lambda l: '{:.2f}'.format(l.bounding_rect[3])),
                    feature.draw_pair_bounding_rects,
                    # feature.draw_pair_bounding_text()(
                    #     lambda l: '{:.2f}'.format(l.angle)
                    # ),
                    curry(feature.draw_centers)(center=(ww/2, hh/2)),
                    # curry(feature.draw_centers)(center=target_yfix_pred),
                    # feature.draw_target()(target_yfix_pred),
                    # feature.draw_target()(((x+0.5)*ww, (y+0.5)*hh)),
                    feature.draw_fps()(int(fps)),
                    curry(autoaim.helpers.showoff)(timeout=1, update=True)
                )
    return curry(aim)


if __name__ == '__main__':
    if len(sys.argv) > 2:
        target_color = sys.argv[2]
        print(target_color)
        def gui_update(x): return x % 10 == 0
        if sys.argv[1] == 'production':
            threading.Thread(target=load_img).start()
            threading.Thread(target=send_packet).start()
            threading.Thread(target=aim_enemy()(
                serial=True,
                mode=target_color,
                gui_update=None)).start()
        else:
            threading.Thread(target=load_img).start()
            threading.Thread(target=send_packet).start()
            threading.Thread(target=aim_enemy()(
                serial=True,
                mode=target_color,
                gui_update=lambda x: x % 10 == 0)).start()
        print("THE END.")
    else:
        print("Zha hui shier? No target set.")
