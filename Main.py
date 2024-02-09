import cv2
import mediapipe as mp
import math
from handbox import Handbox
from time import perf_counter
from enum  import Enum
import pyautogui

class Main():
    def __init__(self) -> None:
        self.cap = cv2.VideoCapture(0)


        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands()
        self.mpDraw = mp.solutions.drawing_utils



        self.box = Handbox()

        self.click_mode = 1

        self.keyboard_mode = 1
        self.last_mode_change = 1

        self.time_last_click = 0
        self.click_timeout = 0.6

        self.main()

    def auth_click(self):
        time_click = perf_counter()
        delta_time = time_click - self.time_last_click
        if delta_time > self.click_timeout:
            return True
        else:
            return False

    def get_distance(self, x1,y1,x2,y2):
        distance = math.hypot(x2 - x1, y2 - y1)
        return distance

    def detect_click(self,Landmarks,mode = 0,Threshold = 25):

        if Landmarks:
            if mode == 0: # Using Index fingertip and middle fingertip
                static_finger_ID = 8
                aux_finger_ID = 12 
            
            if mode == 1: # Using thumb fingertip and base of index finger
                static_finger_ID = 6
                aux_finger_ID = 4 

            if mode == 2:
                static_finger_ID = 12 # Using middle fingertip and thumb
                aux_finger_ID = 4 

            if mode == 3:
                static_finger_ID = 8 # Using middle fingertip and thumb
                aux_finger_ID = 4 

            index_X = Landmarks[static_finger_ID][1] 
            index_Y = Landmarks[static_finger_ID][2] 
            aux_X = Landmarks[aux_finger_ID][1] 
            aux_Y = Landmarks[aux_finger_ID][2] 
            distance = self.get_distance(index_X,index_Y,aux_X,aux_Y)
            if distance < Threshold:
                return True
            else:
                return False
        

    def draw_cursor(self, img , Landmarks):
        if Landmarks:
                cursor_finger_ID = 8
                index_X = Landmarks[cursor_finger_ID][1] 
                index_Y = Landmarks[cursor_finger_ID][2] 

                cv2.circle(img,(index_X,index_Y),5,(0,255,0),-1)


    def draw_cursors(self,img,Landmarks, fingers_IDs):
        if Landmarks:
            for finger_ID in fingers_IDs:
                index_X = Landmarks[finger_ID][1] 
                index_Y = Landmarks[finger_ID][2] 

                cv2.circle(img,(index_X,index_Y),5,(0,255,0),-1)



    def scroll(self, landmarks, pixels = 30):
        index_Y = landmarks[8][2] 
        aux_Y = landmarks[5][2] 


        if(index_Y < aux_Y):
            pyautogui.scroll(pixels)
        else:
            pyautogui.scroll(-pixels)


    def main(self):

        # black_img = cv2.imread("black.jpg")
        # black_img = black_img[0:480,0:640]

        while True:
            sucess, img = self.cap.read()
            if sucess:
                img = cv2.flip(img,1)
                h, w, _ = img.shape
                
                imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Draw Hand Landmarks
                results = self.hands.process(imgRGB)
                self.Landmarks = []
                if(results.multi_hand_landmarks):
                    for handLms in results.multi_hand_landmarks:
                        # self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
                        pass

                    for id, landmark in enumerate(handLms.landmark):
                        px, py = int(landmark.x * w), int(landmark.y * h)
                        self.Landmarks.append((id,px,py))
                    self.draw_cursors(img, self.Landmarks, [8,12,5])
                    
                

                if self.detect_click(self.Landmarks,0):
                    self.scroll(self.Landmarks)
                


                cv2.imshow("Hand Gesture Detection", img)


                if cv2.waitKey(5) & 0xFF==27: # Esc to exit
                    self.cap.release()
                    cv2.destroyAllWindows()
                    break
                
            else:
                print("Can't get video frame, retrying...")
                self.cap.release()
                cv2.destroyAllWindows()



main = Main()
