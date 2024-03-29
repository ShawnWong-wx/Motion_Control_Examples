'''

Support cameras types:
  - Basler: https://github.com/basler/pypylon
  - ImagingSources: https://www.theimagingsource.com
  - OpenCV

Resources:
  - https://github.com/TheImagingSource/IC-Imaging-Control-Samples/tree/master/Python/tisgrabber/samples
  - bufferless VideoCapture: https://stackoverflow.com/questions/43665208/how-to-get-the-latest-frame-from-capture-device-camera-in-opencv

'''

import numpy as np

from pygrabber.dshow_graph import FilterGraph

import pylablib
from pylablib.devices import Basler
from pypylon import pylon

import platform
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import PercentFormatter
from time import sleep
import os

import cv2, queue, threading, time

import tisgrabber as tis

import ctypes
import imutils
import re

pylablib.par["devices/dlls/basler_pylon"] = "C:/Basler/pylon/Runtime/x64/"


############################################# Camera control ###########################################################
################################################ Constants #############################################################
# For cameras
# fourcc_names = ['CAP_PROP_POS_MSEC', 'CAP_PROP_POS_FRAMES', 'CAP_PROP_POS_AVI_RATIO', 'CAP_PROP_FRAME_WIDTH',
#                 'CAP_PROP_FRAME_HEIGHT', 'CAP_PROP_FPS', 'CAP_PROP_FOURCC', 'CAP_PROP_FRAME_COUNT', 'CAP_PROP_FORMAT',
#                 'CAP_PROP_MODE', 'CAP_PROP_BRIGHTNESS', 'CAP_PROP_CONTRAST', 'CAP_PROP_SATURATION', 'CAP_PROP_HUE',
#                 'CAP_PROP_GAIN', 'CAP_PROP_EXPOSURE', 'CAP_PROP_CONVERT_RGB', 'CAP_PROP_WHITE_BALANCE_BLUE_U',
#                 'CAP_PROP_RECTIFICATION', 'CAP_PROP_MONOCHROME', 'CAP_PROP_SHARPNESS', 'CAP_PROP_AUTO_EXPOSURE',
#                 'CAP_PROP_GAMMA', 'CAP_PROP_TEMPERATURE', 'CAP_PROP_TRIGGER', 'CAP_PROP_TRIGGER_DELAY',
#                 'CAP_PROP_WHITE_BALANCE_RED_V', 'CAP_PROP_ZOOM', 'CAP_PROP_FOCUS', 'CAP_PROP_GUID',
#                 'CAP_PROP_ISO_SPEED', 'CAP_PROP_BACKLIGHT', 'CAP_PROP_PAN', 'CAP_PROP_TILT', 'CAP_PROP_ROLL',
#                 'CAP_PROP_IRIS', 'CAP_PROP_SETTINGS', 'CAP_PROP_BUFFERSIZE', 'CAP_PROP_AUTOFOCUS']

fourcc_names = ['CAP_PROP_FPS',  'CAP_PROP_BRIGHTNESS', 'CAP_PROP_CONTRAST', 'CAP_PROP_SATURATION',
                'CAP_PROP_HUE', 'CAP_PROP_GAIN', 'CAP_PROP_EXPOSURE', 'CAP_PROP_GAMMA']


# class VideoCapture:
#     def __init__(self, name):
#         self.cap = cv2.VideoCapture(name)
#         self.q = queue.Queue()
#         t = threading.Thread(target=self._reader)
#         t.daemon = True
#         t.start()
#
#     # read frames as soon as they are available, keeping only most recent one
#     def _reader(self):
#         while True:
#             ret, frame = self.cap.read()
#             if not ret:
#                 break
#             if not self.q.empty():
#                 try:
#                     self.q.get_nowait()  # discard previous (unprocessed) frame
#                 except queue.Empty:
#                     pass
#             self.q.put(frame)
#
#     def read(self):
#         return self.q.get()


class Camera():
    def __init__(self, camera_mode='DFM 37UX226-ML',
                       brightness=0.0, contrast=0.0, gain=0.0, gamma=1.0,
                       framerate=30, pixelformat="Mono12", exposuretime=4000):

        super().__init__()

        self.camera_mode = camera_mode

        self.cam = None
        self.width = None
        self.height = None

        self.brightness=brightness
        self.contrast = contrast
        self.gain=gain
        self.framerate=framerate
        self.pixelformat=pixelformat
        self.exposuretime=exposuretime
        self.gamma = gamma

        print(f'Available cameras: {self.get_available_cameras()}')

    def get_available_cameras(self,):
        if self.camera_mode in ['Sony imx179 8MP', 'See3CAM_CU135M_H03R1']:
            self.camera_type = 'opencv'

        elif self.camera_mode == 'DFM 37UX226-ML':
            self.camera_type = 'imaging_source'

        elif self.camera_mode in ['Basler daA3840-45uc', 'Basler daA3840-45um', 'Basler daA1920-160um']:
            self.camera_type = 'pylon'

        else:
            print("Camera mode is not implemented.")

        available_cameras = {}
        if self.camera_type == "opencv":
            devices_cv = FilterGraph().get_input_devices()
            for device_index in range(len(devices_cv)):
                available_cameras[device_index] = devices_cv[device_index]

        elif self.camera_type == "imaging_source":
            ic = ctypes.cdll.LoadLibrary("./tisgrabber_x64.dll")
            tis.declareFunctions(ic)
            ic.IC_InitLibrary(0)
            devicecount = ic.IC_GetDeviceCount()
            for device_index in range(0, devicecount):
                available_cameras[device_index] = tis.D(ic.IC_GetDevice(device_index))

        elif self.camera_type == "pylon":
            Basler.list_cameras()
            tlf = pylon.TlFactory.GetInstance()
            devices_pylon = tlf.EnumerateDevices()
            for device_index in range(len(devices_pylon)):
                available_cameras[device_index] = devices_pylon[device_index].GetDeviceFactory()

        return available_cameras

    def set_camera(self):
        if self.camera_type == 'pylon':
            tlf = pylon.TlFactory.GetInstance()
            devices = tlf.EnumerateDevices()
            try:
                self.cam = pylon.InstantCamera(tlf.CreateDevice(devices[0]))
                self.cam.Open()
                print("Camera is open.")
                
            except:
                print("Camera is not open.")
                self.cam.StopGrabbing()
                self.cam.DeviceReset.Execute()
                self.cam.Close()

            #########################  Camera setting #################################
            basler_names = ["AcquisitionFrameRate", "Width", "Height", "PixelFormat", "ExposureTime", "Gain",
                            "BslBrightness", "BslContrast"]

            str = f'Default settings: Avaible pixelformat: {self.cam.PixelFormat.Symbolics}; \n'
            for i in range(len(basler_names)):
                str = f'{str}{basler_names[i]}: {self.cam.GetNodeMap().GetNode(basler_names[i]).ToString()}; '
            print(str)

            self.cam.AcquisitionStop.Execute()        # cam stop
            self.cam.TLParamsLocked = False           # grab unlock

            self.cam.OffsetX, self.cam.OffsetY = 0, 0
            self.cam.Width, self.cam.Height = self.cam.Width.Max, self.cam.Height.Max
            self.width,self.height = self.cam.Width, self.cam.Height
            self.cam.AcquisitionFrameRateEnable = True
            self.cam.BslContrastMode = "Linear"
            self.cam.MaxNumBuffer = 150
            self.cam.AcquisitionFrameRate = self.framerate
            # set color space mode to "off" for mask camera since it's not mono camera
            # self.cam.BslHue = 0
            # self.cam.BslSaturation = 0
            # self.cam.BslColorSpace = "Off"
            self.cam.BslBrightness = self.brightness    # 0.1
            self.cam.BslContrast = self.contrast        # 0.3
            self.cam.PixelFormat = self.pixelformat     # "Mono12"
            self.cam.Gain = self.gain                   # 1
            self.cam.ExposureTime = self.exposuretime   # 4000ms
            self.cam.StaticChunkNodeMapPoolSize = self.cam.MaxNumBuffer.GetValue()

            self.cam.TLParamsLocked = True              # grab lock
            self.cam.AcquisitionStart.Execute()         # cam start

            str = 'New camera settings: \n'
            for i in range(len(basler_names)):
                str = f'{str}{basler_names[i]}: {self.cam.GetNodeMap().GetNode(basler_names[i]).ToString()}; '
            print(str)

            ############################## Test setting ##################################
            self.cam.StartGrabbing()
            result = self.cam.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException)   # Wait for an image and retrieve it. timeout of 2000 ms.

            if result.GrabSucceeded():
                frame_image = result.Array
                self.show_camera_image(frame_image)

            self.cam.StopGrabbing()
            # self.cam.DeviceReset.Execute()
            # self.cam.Close()

        elif self.camera_type == 'imaging_source':
            self.cam = ctypes.cdll.LoadLibrary("./tisgrabber_x64.dll")
            tis.declareFunctions(self.cam)
            self.cam.IC_InitLibrary(0)
            self.hGrabber = self.cam.IC_CreateGrabber()
            self.cam.IC_OpenVideoCaptureDevice(self.hGrabber,self.camera_mode.encode("utf-8"))

            ######################### Camera Open #################################   
            if(self.cam.IC_IsDevValid(self.hGrabber)):
                print("Camera is open make settings...")

                if self.camera_mode == 'DFM 37UX226-ML':
                    self.cam.IC_SetVideoFormat(self.hGrabber, "RGB64 (4000x3000)".encode("utf-8"))
                else:
                    print('Camera mode is not implemented.')

                self.cam.IC_SetFrameRate(self.hGrabber, ctypes.c_float(self.framerate))
                self.cam.IC_SetPropertyValue(self.hGrabber, tis.T("Partial scan"), tis.T("Y Offset"), 0)
                self.cam.IC_SetPropertyValue(self.hGrabber, tis.T("Partial scan"), tis.T("X Offset"), 0)
                
                self.cam.IC_SetFormat(self.hGrabber,  ctypes.c_int(1))   #???

                self.cam.IC_SetPropertySwitch(self.hGrabber, tis.T("Exposure"), tis.T("Auto"), 0)
                self.cam.IC_SetPropertyAbsoluteValue(self.hGrabber, tis.T("Exposure"), tis.T("Value"), ctypes.c_float(self.exposuretime))

                self.cam.IC_SetPropertySwitch(self.hGrabber, tis.T("Gain"), tis.T("Auto"), 0)
                self.cam.IC_SetPropertyValue(self.hGrabber, tis.T("Gain"), tis.T("Value"),  ctypes.c_float(self.gain))

                self.cam.IC_SetPropertySwitch(self.hGrabber, tis.T("Gamma"), tis.T("Auto"), 0)
                self.cam.IC_SetPropertyValue(self.hGrabber, tis.T("Gamma"), tis.T("Value"),  ctypes.c_float(self.gamma))

                self.cam.IC_SetPropertySwitch(self.hGrabber, tis.T("Contrast"), tis.T("Auto"), 0)
                self.cam.IC_SetPropertyValue(self.hGrabber, tis.T("Contrast"), tis.T("Value"), ctypes.c_float(0))

            else:
                print("Camera is not open.")

            ######################### Test capture #################################
            if self.cam.IC_IsDevValid(self.hGrabber):
                self.cam.IC_StartLive(self.hGrabber, 1)
                if self.cam.IC_SnapImage(self.hGrabber, 2000) == tis.IC_SUCCESS:
                    Width = ctypes.c_long()
                    Height = ctypes.c_long()
                    BitsPerPixel = ctypes.c_int()
                    colorformat = ctypes.c_int()   
                    self.cam.IC_GetImageDescription(self.hGrabber, Width, Height, BitsPerPixel, colorformat)
     
                    # Calculate the buffer size
                    bpp = int(BitsPerPixel.value / 8.0)
                    buffer_size = Width.value * Height.value * BitsPerPixel.value

                    # Get the image data
                    imagePtr = self.cam.IC_GetImagePtr(self.hGrabber)
                    imagedata = ctypes.cast(imagePtr, ctypes.POINTER(ctypes.c_uint16 *buffer_size))

                    # Create the numpy array
                    image = np.ndarray(buffer=imagedata.contents,dtype=np.uint8, shape=(Height.value, Width.value, bpp))        
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                    image = np.uint16(image)*256
                    image = imutils.rotate(cv2.flip(image, 1), angle=180)

                    self.show_camera_image(image)

                else:
                    print("No frame received in 2 seconds.")

                self.cam.IC_StopLive(self.hGrabber)

            else:
                self.cam.IC_MsgBox("No device opened".encode("utf-8"), "Simple Live Video".encode("utf-8"),)

            # self.cam.IC_ReleaseGrabber(self.hGrabber)

        elif self.camera_type == 'opencv':
            if self.camera_mode=='See3CAM_CU135M_H03R1':
                self.cam = cv2.VideoCapture(0)

                # print(f"OpenCV: {cv2.getVersionString()}")
                self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 4200)
                self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 3120)

            elif self.camera_mode == 'Sony imx179 8MP':
                self.cam = cv2.VideoCapture(0)   

                self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 4000)
                self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 3000)
            else:
                print('Camera model is not implemented.')

            # print(f'Camera frame size is:{cv2.CAP_PROP_FRAME_WIDTH} x {cv2.CAP_PROP_FRAME_HEIGHT}')
            print(f'Camera frame size is:{self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)} x {self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)}')

            if not (self.cam.isOpened()):
                print("Could not open camera.")
            else:
                print("Camera is opened. Old camera settings:")
                # print(cv2.getBuildInformation())
                # print('fourcc:', decode_fourcc(self.cam.get(cv2.CAP_PROP_FOURCC)))
                str = ''
                for i in range(len(fourcc_names)):
                    str = f'{str} {fourcc_names[i]}:{self.cam.get(i)};'
                print(str)

            # Set camera parameters
            # cam.set(cv2.CAP_PROP_MONOCHROME, 19.0)
            self.cam.set(cv2.CAP_PROP_MODE, 3.0)
            self.cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 3: auto; 1: manual
            # self.cam.set(cv2.CAP_PROP_SETTINGS, 1)

            self.cam.set(cv2.CAP_PROP_FPS, self.framerate)
            self.cam.set(cv2.CAP_PROP_EXPOSURE, self.exposuretime)
            self.cam.set(cv2.CAP_PROP_GAIN, self.gain)
            self.cam.set(cv2.CAP_PROP_GAMMA, self.gamma)
            self.cam.set(cv2.CAP_PROP_CONTRAST, self.contrast)
            self.cam.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
            self.cam.set(cv2.CAP_PROP_SATURATION, 0)
            self.cam.set(cv2.CAP_PROP_SHARPNESS, 0)
            self.cam.set(cv2.CAP_PROP_HUE, 0)
            # self.cam.set(cv2.CAP_PROP_IOS_DEVICE_WHITEBALANCE, 0)

            ######################## Retrieval raw data ########################
            # reference: https://stackoverflow.com/questions/70718890/how-to-retrieve-raw-data-from-yuv2-streaming
            # Disable the conversion to BGR by setting FOURCC to Y16 and `CAP_PROP_CONVERT_RGB` to 0.
            if self.camera_mode == 'See3CAM_CU135M_H03R1':
                # self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('G', 'R', 'E', 'Y'))
                # fmt = self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y','8',' ',' '))
                fmt = self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', '1', '6', ' '))

                self.cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)

                # Fetch undecoded RAW video streams
                self.cam.set(cv2.CAP_PROP_FORMAT, -1)  # value -1 to fetch undecoded RAW video streams (as Mat 8UC1)
                # cam.set(cv2.CAP_PROP_FORMAT, cv2.CV_8UC1)

            else:
                self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('Y', '1', '6', ' '))
                self.cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)

                # Fetch undecoded RAW video streams
                self.cam.set(cv2.CAP_PROP_FORMAT, -1)  # value -1 to fetch undecoded RAW video streams (as Mat 8UC1)

            # Check whether camera settings are applied
            print('New camera settings:')
            str = ''
            for i in range(len(fourcc_names)):
                str = f'{str} {fourcc_names[i]}:{self.cam.get(i)};'
            print(str)

            # Trigger camera and capture one image according to the camera frame rate.
            # success, frame = self.cam.read()  # combines both grab and retrieve into one command and returns the decoded frame
            time.sleep(1)
            self.cam.grab()    # "only" gets the image from the camera and holds it for further processing:
            time.sleep(0.5)
            success, frame = self.cam.retrieve(0)
            if success:
                print(f'frame.shape = {frame.shape}, frame.dtype = {frame.dtype}')
                if self.camera_mode == 'HD USB Camera':
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    frame = np.uint16(frame) * 256

                elif self.camera_mode == 'See3CAM_CU135M_H03R1':
                    frame = frame.astype(np.uint16) * 255

                elif self.camera_mode == 'Sony imx179 8MP':
                    frame = frame.reshape(self.height, self.width * 2)
                    frame = frame.astype(np.uint16)   # Convert uint8 elements to uint16 elements
                    frame = (frame[:, 0::2] << 8) + frame[:, 1::2]   # Convert from little endian to big endian (apply byte swap)
                    frame = frame.view(np.uint16)    # The data is actually signed 16 bits - view it as int16 (16 bits singed).

                else:
                    frame = frame.reshape(self.height, self.width * 2)
                    frame = frame.astype(np.uint16)   # Convert uint8 elements to uint16 elements
                    frame = (frame[:, 0::2] << 8) + frame[:, 1::2]   # Convert from little endian to big endian (apply byte swap)
                    frame = frame.view(np.uint16)    # The data is actually signed 16 bits - view it as int16 (16 bits singed).
                   
                self.show_camera_image(frame)
                
            else:
                print('failed to grab frame')

    def capture(self, out_file_name):
        if self.camera_type == 'pylon':
            # trigger the camera.
            img = pylon.PylonImage()
            self.cam.StartGrabbing()
            with self.cam.RetrieveResult(2000) as result:
                # Calling AttachGrabResultBuffer creates another reference to the grab result buffer.
                # This prevents the buffer's reuse for grabbing.
                if result.GrabSucceeded():
                    img.AttachGrabResultBuffer(result)

                    if platform.system() == 'Windows':
                        img.Save(pylon.ImageFileFormat_Tiff, out_file_name)
                        # img.Save(pylon.ImageFileFormat_Raw, filename)
                    else:
                        img.Save(pylon.ImageFileFormat_Png, out_file_name)

                    time.sleep(0.1)

            result.Release()
            self.cam.StopGrabbing()

        elif self.camera_type == 'imaging_source':
            # if self.camera_mode == 'DFM 37UX226-ML':
            # self.hGrabber = self.cam.IC_CreateGrabber()
            ######################### Test capture #################################
            if self.cam.IC_IsDevValid(self.hGrabber):
                self.cam.IC_StartLive(self.hGrabber, 1)
                if self.cam.IC_SnapImage(self.hGrabber, 2000) == tis.IC_SUCCESS:
                    Width = ctypes.c_long()
                    Height = ctypes.c_long()
                    BitsPerPixel = ctypes.c_int()
                    colorformat = ctypes.c_int()   
                    self.cam.IC_GetImageDescription(self.hGrabber, Width, Height, BitsPerPixel, colorformat)

                    # Calculate the buffer size
                    bpp = int(BitsPerPixel.value / 8.0)
                    buffer_size = Width.value * Height.value * BitsPerPixel.value

                    # Get the image data
                    imagePtr = self.cam.IC_GetImagePtr(self.hGrabber)
                    imagedata = ctypes.cast(imagePtr, ctypes.POINTER(ctypes.c_uint16 *buffer_size))

                    # Create the numpy array
                    frame = np.ndarray(buffer=imagedata.contents,dtype=np.uint8, shape=(Height.value, Width.value, bpp))        
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                    frame = np.uint16(frame)*256
                    frame = imutils.rotate(cv2.flip(frame, 1), angle=180)

                    cv2.imwrite(out_file_name, frame, [cv2.IMWRITE_TIFF_COMPRESSION, 1])

                else:
                    print("No frame received in 2 seconds.")
                # self.cam.IC_StopLive(self.hGrabber)

            else:
                print("No device opened.")
            # self.cam.IC_ReleaseGrabber(self.hGrabber)
           
        elif self.camera_type == 'opencv':
            # success, frame = self.cam.read()    # combines both grab and retrieve into one command and returns the decoded frame
            self.cam.grab()  # "only" gets the image from the camera and holds it for further processing:
            success, frame = self.cam.retrieve(0)
            assert success, 'failed to grab frame'

            if self.camera_mode == 'HD USB Camera':
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frame = np.uint16(frame) * 256

            elif self.camera_mode == 'See3CAM_CU135M_H03R1':
                frame = frame.astype(np.uint16) * 255

            elif self.camera_mode == 'Sony imx179 8MP':
                frame = frame.reshape(self.height, self.width * 2)
                frame = frame.astype(np.uint16)  # Convert uint8 elements to uint16 elements
                frame = (frame[:, 0::2] << 8) + frame[:, 1::2]  # Convert from little endian to big endian (byte swap)
                frame = frame.view(np.uint16)  # The data is signed 16 bits - view it as int16 (16 bits singed).

            else:
                frame = frame.reshape(self.height, self.width * 2)
                frame = frame.astype(np.uint16)  # Convert uint8 elements to uint16 elements
                frame = (frame[:, 0::2] << 8) + frame[:, 1::2]  # Convert from little endian to big endian (byte swap)
                frame = frame.view(np.uint16)  # The data is signed 16 bits - view it as int16 (16 bits singed).

                # Save the frame as a TIF image
            cv2.imwrite(out_file_name, frame, [cv2.IMWRITE_TIFF_COMPRESSION, 1])

    def close(self):
        if self.camera_type == 'pylon':
            self.cam.Close()

        elif self.camera_type == 'imaging_source':
            self.cam.IC_ReleaseGrabber(self.hGrabber)
            self.cam.IC_CloseVideoCaptureDevice(self.hGrabber)

        elif self.camera_type == 'opencv':
            self.cam.release()

        print('Camera is closed.')

    def show_camera_image(self, img_frame):
        plt.rcParams.update({'font.size': 18})
        fig, ax = plt.subplots(2, 1, sharey=False, figsize=(10, 12))
        h = ax[0].imshow(img_frame, cmap='gray')
        ax[0].axison = False
        ax[0].set_title('camera image')
        divider = make_axes_locatable(ax[0])
        cax = divider.append_axes("right", size="3%", pad=0.05)
        plt.colorbar(h, cax=cax, label='pixel value')

        img_flatten = img_frame.flatten()
        ax[1].hist(img_flatten, bins=256, weights=np.ones_like(img_flatten) / len(img_flatten))
        ax[1].set_ylabel('pixel count')
        ax[1].xlim = (0, 65535)
        ax[1].set_title('Histogram of the camera image')

        plt.show()

def decode_fourcc(v):
    v = int(v)
    return "".join([chr((v >> 8 * i) & 0xFF) for i in range(4)])
