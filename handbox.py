import cv2

class Handbox():
    def __init__(self) -> None:
        self.color = (0,255,0) # Green Color
        self.screenHeight, self.screenWidth = (640,480)
        self.spacement = 30

    def draw(self,landmarks,img):
        
        max_x = 0
        max_y = 0
        min_x = self.screenHeight
        min_y = self.screenWidth

        for _,x,y in landmarks:
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
        
        if max_x != 0 and max_y != 0:
            self.point1 = (min_x - self.spacement, min_y - self.spacement)
            self.point2 = (max_x + self.spacement, max_y + self.spacement)
            
            cv2.rectangle(img, self.point1 , self.point2 , self.color  , 2)

        
    def get_area(self):
        rect_height = self.point2[1] - self.point1[1]
        rect_width = self.point2[0] - self.point1[0]
        area = rect_height * rect_width
        return area