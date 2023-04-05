# import the necessary packages
from imutils import build_montages
from datetime import datetime
import numpy as np
import imagezmq
import argparse
import imutils
import cv2
import simplejpeg
import multiprocessing

class NodeMonitor:

    def __init__(self, mW, mH):
        self.stall_p = multiprocessing.Process(daemon=True,
                            args=((mW,mH,)),
                            target=self.node_monitor)
        self.stall_p.start()


    def node_monitor(self,mW, mH):
        # initialize the ImageHub object
        imageHub = imagezmq.ImageHub('tcp://*:5556',REQ_REP=True)
        print ('imagezmq for node monitoring initialized')

        # load our serialized model from disk

        frameDict = {}

        # initialize the dictionary which will contain  information regarding
        # when a device was last active, then store the last time the check
        # was made was now
        lastActive = {}
        lastActiveCheck = datetime.now()

        # stores the estimated number of Pis, active checking period, and
        # calculates the duration seconds to wait before making a check to
        # see if a device was active
        ESTIMATED_NUM_PIS = 4
        ACTIVE_CHECK_PERIOD = 10
        ACTIVE_CHECK_SECONDS = ESTIMATED_NUM_PIS * ACTIVE_CHECK_PERIOD

        stop = False
        count = 0
        detectframecount = 0
        # start looping over all the frames
        while True:
            # receive RPi name and frame from the RPi and acknowledge
            # the receipt
            (rpiName, jpg_buffer) = imageHub.recv_jpg()
            imageHub.send_reply(b'OK')
            frame = simplejpeg.decode_jpeg( jpg_buffer, colorspace='BGR')

            # if a device is not in the last active dictionary then it means
            # that its a newly connected device
            if rpiName not in lastActive.keys():
                print("[INFO] receiving data from {}...".format(rpiName))

            # record the last active time for the device from which we just
            # received a frame
            lastActive[rpiName] = datetime.now()

            # resize the frame to have a maximum width of 400 pixels, then
            # grab the frame dimensions and construct a blob
            frame = imutils.resize(frame, width=400)
            (h, w) = frame.shape[:2]
            # draw the sending device name on the frame
            cv2.putText(frame, rpiName, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # update the new frame in the frame dictionary
            frameDict[rpiName] = frame

            # build a montage using images in the frame dictionary
            montages = build_montages(frameDict.values(), (w, h), (mW, mH))

            # display the montage(s) on the screen
            for (i, montage) in enumerate(montages):
                cv2.imshow("Home pet location monitor ({})".format(i),
                    montage)

            # detect any kepresses
            key = cv2.waitKey(1) & 0xFF

            # if current time *minus* last time when the active device check
            # was made is greater than the threshold set then do a check
            if (datetime.now() - lastActiveCheck).seconds > ACTIVE_CHECK_SECONDS:
                # loop over all previously active devices
                for (rpiName, ts) in list(lastActive.items()):
                    # remove the RPi from the last active and frame
                    # dictionaries if the device hasn't been active recently
                    if (datetime.now() - ts).seconds > ACTIVE_CHECK_SECONDS:
                        print("[INFO] lost connection to {}".format(rpiName))
                        lastActive.pop(rpiName)
                        frameDict.pop(rpiName)

                # set the last active check time as current time
                lastActiveCheck = datetime.now()

            # if the `q` key was pressed, break from the loop
            if key == ord("q"):
                break

        # do a bit of cleanup
        cv2.destroyAllWindows()
