import cv2
import mediapipe as mp
import numpy as np
import autopy
import math
import matplotlib.pyplot as plt

def index_thumb_pt(img,result):
    h, w = img.shape[0], img.shape[1]
    hand_dic = {}
    hand_21 = result.multi_hand_landmarks[0]
    thumb_x = hand_21.landmark[4].x * w
    thumb_y = hand_21.landmark[4].y * h
    index_x = hand_21.landmark[8].x * w
    index_y = hand_21.landmark[8].y * h
    choose_pt = (int((thumb_x + index_x)/2),int((thumb_y + index_y)/2))
    dst = np.sqrt(np.square(thumb_x - index_x) + np.square(thumb_y - index_y))
    click_state = False
    if dst < 30 and hand_21.landmark[3].x < hand_21.landmark[12].x < hand_21.landmark[17].x and \
            hand_21.landmark[3].x < hand_21.landmark[16].x < hand_21.landmark[17].x and \
            hand_21.landmark[3].x < hand_21.landmark[20].x < hand_21.landmark[17].x and \
            hand_21.landmark[6].y < hand_21.landmark[20].y < hand_21.landmark[0].y and \
            hand_21.landmark[6].y < hand_21.landmark[16].y < hand_21.landmark[0].y and \
            hand_21.landmark[6].y < hand_21.landmark[12].y < hand_21.landmark[0].y:
        click_state = True
        cv2.circle(img, choose_pt, 10, (0, 0, 255), -1)  # 绘制点击坐标，为轨迹的坐标
        cv2.circle(img, choose_pt, 5, (255, 220, 30), -1)

    hand_dic['pt'] = choose_pt
    hand_dic['click'] = click_state

    return img, hand_dic

def p_to_p_distance(p1,p2):
    return np.sqrt(np.square(p1[0] - p2[0]) + np.square(p1[1] - p2[1]))

def hand_point(result,h,w):
    handpoint_list = []
    hand_21 = result.multi_hand_landmarks[0]
    handpoint_list.append([int(hand_21.landmark[0].x * w), int(hand_21.landmark[0].y * h)])
    handpoint_list.append([int(hand_21.landmark[1].x * w), int(hand_21.landmark[1].y * h)])
    handpoint_list.append([int(hand_21.landmark[2].x * w), int(hand_21.landmark[2].y * h)])
    handpoint_list.append([int(hand_21.landmark[3].x * w), int(hand_21.landmark[3].y * h)])
    handpoint_list.append([int(hand_21.landmark[4].x * w), int(hand_21.landmark[4].y * h)])
    handpoint_list.append([int(hand_21.landmark[5].x * w), int(hand_21.landmark[5].y * h)])
    handpoint_list.append([int(hand_21.landmark[6].x * w), int(hand_21.landmark[6].y * h)])
    handpoint_list.append([int(hand_21.landmark[7].x * w), int(hand_21.landmark[7].y * h)])
    handpoint_list.append([int(hand_21.landmark[8].x * w), int(hand_21.landmark[8].y * h)])
    handpoint_list.append([int(hand_21.landmark[9].x * w), int(hand_21.landmark[9].y * h)])
    handpoint_list.append([int(hand_21.landmark[10].x * w), int(hand_21.landmark[10].y * h)])
    handpoint_list.append([int(hand_21.landmark[11].x * w), int(hand_21.landmark[11].y * h)])
    handpoint_list.append([int(hand_21.landmark[12].x * w), int(hand_21.landmark[12].y * h)])
    handpoint_list.append([int(hand_21.landmark[13].x * w), int(hand_21.landmark[13].y * h)])
    handpoint_list.append([int(hand_21.landmark[14].x * w), int(hand_21.landmark[14].y * h)])
    handpoint_list.append([int(hand_21.landmark[15].x * w), int(hand_21.landmark[15].y * h)])
    handpoint_list.append([int(hand_21.landmark[16].x * w), int(hand_21.landmark[16].y * h)])
    handpoint_list.append([int(hand_21.landmark[17].x * w), int(hand_21.landmark[17].y * h)])
    handpoint_list.append([int(hand_21.landmark[18].x * w), int(hand_21.landmark[18].y * h)])
    handpoint_list.append([int(hand_21.landmark[19].x * w), int(hand_21.landmark[19].y * h)])
    handpoint_list.append([int(hand_21.landmark[20].x * w), int(hand_21.landmark[20].y * h)])

    return handpoint_list

def judge_handpose(handpoint_list):
    if handpoint_list[4][1] < handpoint_list[3][1] and p_to_p_distance(handpoint_list[8],handpoint_list[5]) < 50 and \
         p_to_p_distance(handpoint_list[12],handpoint_list[9]) < 50 and p_to_p_distance(handpoint_list[16],handpoint_list[13]) < 50 and \
         p_to_p_distance(handpoint_list[20],handpoint_list[17]) < 50 and \
         abs(handpoint_list[4][0] - handpoint_list[3][0]) < 5 and abs(handpoint_list[5][0] - handpoint_list[17][0]) < 5:
        return 'Thumb_up'

    elif handpoint_list[8][1] < handpoint_list[7][1] < handpoint_list[6][1] and \
         handpoint_list[10][1] < handpoint_list[11][1] < handpoint_list[12][1]  and \
         handpoint_list[14][1] < handpoint_list[15][1] < handpoint_list[16][1]  and \
         handpoint_list[18][1] < handpoint_list[19][1] < handpoint_list[20][1] and \
            p_to_p_distance(handpoint_list[4],handpoint_list[12])< 50:
        return 'Index_up'

    elif handpoint_list[12][1] < handpoint_list[11][1] < handpoint_list[10][1] and \
        handpoint_list[8][1] < handpoint_list[7][1] < handpoint_list[6][1] and \
        handpoint_list[14][1] < handpoint_list[15][1] < handpoint_list[16][1] and \
        handpoint_list[18][1] < handpoint_list[19][1] < handpoint_list[20][1] and \
            p_to_p_distance(handpoint_list[4],handpoint_list[16]) < 50:
        return 'Index_middle_up'

    elif handpoint_list[20][1] < handpoint_list[19][1] < handpoint_list[18][1] and \
        handpoint_list[10][1] < handpoint_list[11][1] < handpoint_list[12][1] and \
        handpoint_list[14][1] < handpoint_list[15][1] < handpoint_list[16][1] and \
        handpoint_list[6][1] < handpoint_list[7][1] < handpoint_list[8][1] and \
            p_to_p_distance(handpoint_list[4],handpoint_list[12]) < 50:
        return 'Pinky_up'

    elif p_to_p_distance(handpoint_list[8],handpoint_list[12]) < 40 and \
         p_to_p_distance(handpoint_list[12],handpoint_list[16]) < 40 and \
         p_to_p_distance(handpoint_list[16],handpoint_list[20]) < 40 and \
         p_to_p_distance(handpoint_list[4],handpoint_list[8]) < 40:
        return 'Fingers_together'

    elif p_to_p_distance(handpoint_list[4],handpoint_list[0]) > p_to_p_distance(handpoint_list[5],handpoint_list[0]) and \
         p_to_p_distance(handpoint_list[8],handpoint_list[5]) > 4 * p_to_p_distance(handpoint_list[5],handpoint_list[9]) and \
         p_to_p_distance(handpoint_list[12],handpoint_list[9]) > 4 * p_to_p_distance(handpoint_list[5],handpoint_list[9]) and \
         p_to_p_distance(handpoint_list[16],handpoint_list[13]) > 4 * p_to_p_distance(handpoint_list[5],handpoint_list[9]) and \
         p_to_p_distance(handpoint_list[20], handpoint_list[17]) > 3 * p_to_p_distance(handpoint_list[5],handpoint_list[9]):
        return 'GiveMeFive'

    else:
        return None


def draw_character(gesture_lines,img):
    if len(gesture_lines) >= 2:
        pt1 = gesture_lines[-1]
        pt2 = gesture_lines[-2]
        if np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2) < 30:
            cv2.line(img, pt1, pt2, (0,0,255), thickness=6)

def according_area_sort(elem):
    return cv2.contourArea(elem)

def flit_sort_area_contours(contours,n):
    contours.sort(key=according_area_sort,reverse=True)
    return contours[:n]

def get_angle_plot(line1, line2):

    l1xy = line1.get_xydata()

    # Angle between line1 and x-axis
    slope1 = (l1xy[1][1] - l1xy[0][1]) / float(l1xy[1][0] - l1xy[0][0])
    angle1 = abs(math.degrees(math.atan(slope1))) # Taking only the positive angle

    l2xy = line2.get_xydata()

    # Angle between line2 and x-axis
    slope2 = (l2xy[1][1] - l2xy[0][1]) / float(l2xy[1][0] - l2xy[0][0])
    angle2 = abs(math.degrees(math.atan(slope2)))

    theta1 = min(angle1, angle2)
    theta2 = max(angle1, angle2)

    angle = theta2 - theta1

    return angle

if __name__ == '__main__':


    wScr, hScr = autopy.screen.size()
    wCam, hCam = 640, 480
    smoothening = 12
    initial_length = 100

    plocX, plocY = 0, 0
    clocX, clocY = 0, 0

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False,
                           max_num_hands=2,
                           min_detection_confidence=0.7,
                           min_tracking_confidence=0.5)
    mpDraw = mp.solutions.drawing_utils

    gesture_lines = []

    cap = cv2.VideoCapture(0)
    cap.open(0)
    img_black = np.zeros((hCam,wCam,3),dtype='uint8')
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print('error')
        h, w, c = frame.shape[0], frame.shape[1],frame.shape[2]
        # print(h,w,c)
        frame = cv2.flip(frame, 1)
        img_RGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(img_RGB)
        if results.multi_hand_landmarks:
            mpDraw.draw_landmarks(frame,results.multi_hand_landmarks[0],mp_hands.HAND_CONNECTIONS)
            handpoint_list = hand_point(results,h,w)
            hand_pose = judge_handpose(handpoint_list)

            if hand_pose == 'Thumb_up' and len(gesture_lines) > 10:
                cv2.imwrite('picture/character.jpg', img_black)
                gesture_lines = []
                img_black = np.zeros((h, w, c),dtype='uint8')

            elif hand_pose =='Index_up':
                index_x,index_y = handpoint_list[8]
                screen_x = np.interp(index_x, (0, wCam),(0, wScr))
                screen_y = np.interp(index_y, (0, hCam), (0, hScr))
                clocX = plocX + (screen_x - plocX) / smoothening
                clocY = plocY + (screen_y - plocY) / smoothening
                autopy.mouse.move(clocX,clocY)
                cv2.circle(frame,(index_x,index_y),10,(255,0,255),cv2.FILLED)
                plocX, plocY = clocX, clocY

            elif hand_pose == 'Index_middle_up':
                if p_to_p_distance(handpoint_list[8],handpoint_list[12]) < 50:
                    index_x, index_y = handpoint_list[8]
                    middle_x, middle_y = handpoint_list[12]
                    click_x, click_y = int((index_x + middle_x)/2), int((index_y + middle_y)/2)
                    cv2.circle(frame, (click_x, click_y), 10, (0, 255, 0), cv2.FILLED)
                    autopy.mouse.click()

            elif hand_pose == 'Pinky_up':
                pinky_x, pinky_y = handpoint_list[20]
                cv2.circle(frame, (pinky_x, pinky_y), 15, (0, 255, 0), cv2.FILLED)
                cv2.circle(img_black, (pinky_x, pinky_y), 15, (0, 0, 0), cv2.FILLED)

            # elif hand_pose == 'Fingers_together':
            #     gray = cv2.cvtColor(img_black,cv2.COLOR_BGR2GRAY)
            #     _, imgBinary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
            #     contours,_ = cv2.findContours(imgBinary,cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            #     if contours :
            #         contours_sorted = flit_sort_area_contours(contours,1)
            #         img_black = cv2.drawContours(img_black,contours_sorted,-1,(0, 0, 255),cv2.FILLED)

            # elif hand_pose == 'GiveMeFive':
            #     img_black_copy = img_black.copy()
            #     x1 = (handpoint_list[8][0], handpoint_list[5][0])
            #     y1 = (handpoint_list[8][1], handpoint_list[5][1])
            #     line1 = plt.plot(x1, y1)
            #     x2 = (100, 100)
            #     y2 = (100, 200)
            #     line2 = plt.plot(x2, y2)
            #     angle = get_angle_plot(line1[0], line2[0])
            #     angle = round(angle, 2)
            #     gray = cv2.cvtColor(img_black_copy, cv2.COLOR_BGR2GRAY)
            #     _, imgBinary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
            #     contours, _ = cv2.findContours(imgBinary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
            #     if contours:
            #         contours_sorted = flit_sort_area_contours(contours, 1)
            #         min_rect = cv2.minAreaRect(contours_sorted[0])
            #         scale_size = p_to_p_distance(handpoint_list[8],handpoint_list[5])/ initial_length
            #         mat = cv2.getRotationMatrix2D(min_rect[0], -angle * 2, scale_size)
            #         # 这里有三个参数 分别是中心位置，旋转角度，缩放程度
            #         img_black_copy = cv2.warpAffine(img_black_copy, mat, (h, w))
            #         img_black_copy = cv2.resize(img_black_copy,(w,h))
            #         cv2.imshow('window', img_black_copy)


            frame,hand_list = index_thumb_pt(frame,results)
            if hand_list['click']:
                draw_character(gesture_lines, img_black)
                gesture_lines.append(hand_list["pt"])


        img_gray = cv2.cvtColor(img_black,cv2.COLOR_BGR2GRAY)
        _, imgInv = cv2.threshold(img_gray,50, 255, cv2.THRESH_BINARY_INV)
        imgInv = cv2.cvtColor(imgInv,cv2.COLOR_GRAY2BGR)
        img = cv2.bitwise_and(frame,imgInv)
        img = cv2.bitwise_or(img,img_black)
        
        # 创建全屏窗口
        cv2.namedWindow('my_window', cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty('my_window', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.imshow('my_window',img)

        if cv2.waitKey(1) in [ord('q'),27]:
            break

    cap.release()
    cv2.destroyAllWindows()