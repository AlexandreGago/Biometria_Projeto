import os
import time
import logging
from threading import Thread

import customtkinter as Ctk
import cv2
import numpy as np
import requests
from PIL import Image

import facedetection
import fingerprint
import utils
import nfc

gamma = 1.0
#DEFINE 
X_POS=187
Y_POS=97
WIDTH=483
HEIGHT=393

MAX_X=155
MAX_Y=65
MAX_WIDTH=515
MAX_HEIGHT=425

MIN_X=220
MIN_Y=130
MIN_WIDTH=450
MIN_HEIGHT=360



Ctk.set_appearance_mode("Dark")   
Ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(Ctk.CTk):
    def __init__(self,vid):
        super().__init__()

        #video feed
        self.vid = vid
        #image currently in the video label
        self.img = None
        self.index = 0
        #last drawn boxes
        self.boxes = None
        # configure window
        self.title("Biometria App")
        self.geometry(f"{1100}x{580}")
        self.resizable(False, False)

        self.frame = Ctk.CTkFrame(master=self,width=1100, height=580)
        self.frame.place(x=0, y=0)

        self.nfc()
        
        #!dont remove
        self.cancel_handle = None
        #!DEBUG
        # self.user = "0"
        # self.faceRecognition(register=True)
        # self.fingerprint(register=Tr0ue)
    
    def report_callback_exception(self, exc, val, tb):
        """
        Handles exceptions

        Args:
            exc (Exception): Exception type
            val (Exception): Exception value
            tb (traceback): traceback
        """
        pass
    
    def PopUp(self,msg):
        """
        PopUp window with a message

        Args:
            msg (str): Message to display
        """
        pop_up= Ctk.CTkToplevel(self)
        pop_up.geometry("250x150+865+465")
        pop_up.title("Warning")
        Ctk.CTkLabel(pop_up, text= msg, font=('Arial',16)).place(x=125,y=75,anchor="center")


    
    def nfc(self, register=False):
        """
        NFC page, can be used for login or register, requires the user to use the NFC reader

        Args:
            register (bool, optional): If true, register a new user. Defaults to False.
        """
        #keep track of user
        self.user=None

        #clear frame
        for widget in self.frame.winfo_children():
            widget.destroy()


        label = Ctk.CTkLabel(self.frame, text="Please use the NFC Reader to scan your card",font=("Arial", 20))
        #place this on top in the middle
        label.place(x=550, y=40, anchor="center")
        
        nfcImg = Ctk.CTkImage(light_image=Image.open("./img/nfc.png"), size=(300 , 180))
        nfc_label = Ctk.CTkLabel(master=self.frame, image=nfcImg, text='')
        #place it in the middle
        nfc_label.place(x=550, y=290, anchor="center")

        Thread(target=self.nfc_thread, daemon=True).start()
    
    def nfc_thread(self):
        """
        Check every second if a card has been scanned
        
        Args:
            None
        Returns:
            None
        """
        id = nfc.get_id()
        logging.info(f"ID: {id}")
        if id is not None:
            self.user = id
            #login
            if id in os.listdir("./db"):
                logging.info("Login")
                self.faceRecognition(register=False)
            #register
            else:
                logging.info("Register")
                self.faceRecognition(register=True)
        else:
            self.after(1000, self.nfc_thread)
            




    def faceRecognition(self, register=False):
        """
        Face recognition page, can be used for login or register, requires the user to use the camera

        Args:
            register (bool, optional): If true, register a new user. Defaults to False.
        """

        #clear frame
        for widget in self.frame.winfo_children():
            widget.destroy()

        #frame for the video feed
        self.video_label = Ctk.CTkLabel(self.frame, fg_color="transparent", bg_color="transparent", text="")
        #place on center
        self.video_label.place(x=550, y=290, anchor="center")
        self.open_camera(register=register)
        cancelBtn = Ctk.CTkButton(self.frame , text="Cancel", command=lambda: self.nfc() )
        self.nextBtn = Ctk.CTkButton(self.frame , text="Next")

        #place the buttons on the bottom
        cancelBtn.place(anchor="center", x=450, y=560)
        self.nextBtn.place(anchor="center", x=650, y=560)



        #start the face detection thread with arg register
        self.nextBtn.configure(command= lambda:Thread(target=self.face_detection, args=(register,),daemon=True).start())

    def face_detection(self, register):
        """
        Performs liveness test and face recognition or registration
        
        Args:
            register (bool): If true, register a new user. Defaults to False.
        Returns:
            None
        """
        user=self.user
        #disable button
        self.nextBtn.configure(state="disabled")

        #use the last captured frame
        last_image = self.img

        #calibrate eyes values
        start = time.time()
        average = 0
        count = 0
        fails = 0
        while time.time() - start < 1:
            #skip if no new image
            if self.img is last_image:
                continue
            #get eyes closed value
            ear , _, _ = facedetection.get_eyes_aspect_ratio(self.img)
            if ear == 0:
                fails += 1
            average += ear     
            count += 1
        if fails / count > 0.5:
            logging.info(f"fails: {fails} count: {count}")
            self.PopUp("Not enough values to calibrate eyes")
            self.nextBtn.configure(state="normal")
            return
        
        average = average/count
        logging.info(f"Eyes average: {average}")
        
        start = time.time()
        last_blink = start
        blinks = 0
        liveness = False
        
        while not liveness and time.time() - start < 10:
            #skip if no new image
            if self.img is last_image:
                continue

            blink_detected, left_eye, right_eye = facedetection.blink(self.img, average)
            #last blink was more than 0.5s ago
            if blink_detected and time.time() - last_blink > 0.5:
                logging.info("Blink detected")
                blinks += 1
                last_blink = time.time()
            
            #!DEBUG / RELATORIO #####################
            # self.video_label.after_cancel(self.cancel_handle)
            # #draw blinks
            # image = self.img            
            # leftEyeHull = cv2.convexHull(left_eye)
            # rightEyeHull = cv2.convexHull(right_eye)

            # cv2.drawContours(image, [leftEyeHull], -1, (255, 0, 0), 2)
            # cv2.drawContours(image, [rightEyeHull], -1, (255, 0, 0), 2)
            
            # self.video_label.configure(image=utils.convert_to_photoimage(image))
            
            # self.open_camera(debug=True)
            
            #!#################################
            
            
            #if 2 blinks detected in 10s
            # print(blinks)
            if blinks >= 2:
                liveness = True
                
        #!###dbeug
        # self.cancel_handle = self.open_camera()
        #!########
        
        if not liveness:
            self.PopUp("Liveness test failed")
            self.nextBtn.configure(state="normal")
            return
        else:
            #wait for image without eyes closed
            time.sleep(0.5)
            if register:
                success, error = facedetection.registerFace(self.img, user, average)
            else:
                success, error = facedetection.faceVerify(self.img, user)

            if success:
                self.fingerprint(register=register)
            else:
                self.PopUp(error)
                self.nextBtn.configure(state="normal")
                return


    def fingerprint(self, register=False):
        """
        Fingerprint page, can be used for login or register, requires the user to use the fingerprint reader

        Args:
            register (bool, optional): If true, register a new user. Defaults to False.
        """

        #clear frame
        #?this throws an exception but it is needed to clear the frame
        for widget in self.frame.winfo_children():
            widget.destroy()
            
        self.finger_label= Ctk.CTkLabel(self.frame, text="Place your finger on the sensor when it flashes green",font=("Arial", 20))
        self.finger_label.place(x=550, y=40, anchor="center")

        fingerImg = Ctk.CTkImage(light_image=Image.open("./img/finger.png"), size=(256 , 256))
        finger_label = Ctk.CTkLabel(master=self.frame, image=fingerImg, text='')
        finger_label.place(x=550, y=290, anchor="center")

        cancelBtn = Ctk.CTkButton(self.frame , text="Cancel", command=lambda: self.nfc())
        cancelBtn.place(x=450, y=540, anchor="center")

        nextBtn = Ctk.CTkButton(self.frame , text="Next", state="disabled")
        nextBtn.place(x=650, y=540, anchor="center")

        if register:
            Thread(target=self.fingerprint_thread, args=(nextBtn,True,),daemon=True).start()
        else:
            Thread(target=self.fingerprint_thread, args=(nextBtn,False,),daemon=True).start()
                            
        #! TESTS ONLY
        # nextBtntest = Ctk.CTkButton(self.frame , text="TEST NEXT", command= lambda: self.userPage())
        # nextBtntest.place(x=610,  y=510)
    
    def fingerprint_thread(self, nextbtn, register):
        """
        Performs fingerprint registration or login

        Args:
            nextbtn (Ctk.CTkButton): Next button
            register (bool): If true, register a new user. Defaults to False.
        Returns:
            None
        """
        user=self.user
        success = False
        while not success:
            try:
                if register:
                    success = fingerprint.fingerprint_register(user, self.finger_label, nextbtn)
                else:
                    success = fingerprint.fingerprint_login(user, self.finger_label, nextbtn)
            #runtime error
            except RuntimeError:
                self.PopUp("Fingerprint sensor disconnected")
                success = False
        
        if register:
            nextbtn.configure(command= lambda: self.registDone())
        else:
            nextbtn.configure(command= lambda: self.userPage())
        
        
    def registDone(self):
        """
        Registration done page
        """
        for widget in self.frame.winfo_children():
            widget.destroy()

        label = Ctk.CTkLabel(self.frame, text="Successfully registered!", text_color="green",font=("Arial", 20))
        label.place(x=550, y=40, anchor="center")

        userImg = Ctk.CTkImage(light_image=Image.open("./img/register.png"), size=(256 , 256))
        user_label = Ctk.CTkLabel(master=self.frame, image=userImg, text='')
        user_label.place(x=550, y=290, anchor="center")

        doneBtn = Ctk.CTkButton(self.frame , text="Done", command= lambda: self.nfc() )
        doneBtn.place(x=550, y=540, anchor="center")

    def userPage(self):
        """
        User page, shows user ID
        """
        for widget in self.frame.winfo_children():
            widget.destroy()

        label = Ctk.CTkLabel(self.frame, text="Authentication Successful!", text_color="green",font=("Arial", 20))
        label.place(x=550, y=40, anchor="center")

        userImg = Ctk.CTkImage(light_image=Image.open("./img/profile.png"), size=(256 , 256))
        user_label = Ctk.CTkLabel(master=self.frame, image=userImg, text='')
        user_label.place(x=550, y=290, anchor="center")

        doneBtn = Ctk.CTkButton(self.frame , text="Done", command= lambda: self.nfc() )
        doneBtn.place(x=550, y=540, anchor="center")
        self.open_camera()


    def open_camera(self, register = False, debug=False):
        """
        gets camera frame and puts it on video label, draw green rectangle if registering a new user

        Args:
            register (bool, optional): If true, draw green rectangle. Defaults to False.
            debug (bool, optional): If true, dont repeat and dont set video label. Defaults to False.
        """
        
        camera_frame = utils.capture_frame(vid,raw=True)
        #let this be acessible to other functions
        #!change brightness change second value
        # cv2.normalize(camera_frame, camera_frame, 0, 200, cv2.NORM_MINMAX)
        #!noise reduction

        # #adjust  gamma
        # invGamma = 1.0 / gamma
        # table = np.array([((i / 255.0) ** invGamma) * 255
        #     for i in np.arange(0, 256)]).astype("uint8")
        # camera_frame = cv2.LUT(camera_frame, table)

        
        self.img = camera_frame

        image = camera_frame.copy()
        if self.index % 8 == 0:
            self.boxes = facedetection.detect_faces(image)
            self.index +=1
        else:
            self.index += 1
        
        
        for (x,y,w,h) in self.boxes:
            cv2.rectangle(image,(x,y),(x+w,y+h),(0,0,255),3)

        if register:
            cv2.rectangle(image,(X_POS,Y_POS),(WIDTH,HEIGHT),(0,255,0),3)


        if not debug:
            image = utils.convert_to_photoimage(image)
            # put image in the label
            self.video_label.configure(image=image)
            #repeat every 15ms
            if register:
                self.cancel_handle = self.video_label.after(15, self.open_camera, True)
            else:
                self.cancel_handle = self.video_label.after(15, self.open_camera)



if __name__ == "__main__":
    vid = cv2.VideoCapture(0)
    #change exposure
    #show camera feed
    gamma = 1.0
    logging.basicConfig(level=logging.INFO)        
    cv2.destroyAllWindows()
    
    
    app = App(vid)

    app.mainloop()