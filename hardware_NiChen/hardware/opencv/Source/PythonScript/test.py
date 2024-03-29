import re

import cv2
import numpy as np
import sys
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from pygrabber.dshow_graph import FilterGraph


out_dir = "./"

def show_camera_image(img_frame):
   plt.rcParams.update({'font.size': 14})
   fig, ax = plt.subplots(1, 2, sharey=False, figsize=(15, 3))
   h = ax[0].imshow(img_frame, cmap='gray')
   ax[0].axison = False
   ax[0].set_title('camera image')
   divider = make_axes_locatable(ax[0])
   cax = divider.append_axes("left", size="3%", pad=0.05)
   plt.colorbar(h, cax=cax, label='pixel value', location='left')

   img_flatten = img_frame.flatten()
   ax[1].hist(img_flatten, bins=256, weights=np.ones_like(img_flatten) / len(img_flatten), edgecolor='none')
   ax[1].set_ylabel('pixel count')
   ax[1].xlim = (0, 65535)
   ax[1].set_title('Histogram of the camera image')

   plt.show()




fourcc_names = ['CAP_PROP_POS_MSEC', 'CAP_PROP_POS_FRAMES', 'CAP_PROP_POS_AVI_RATIO', 'CAP_PROP_FRAME_WIDTH',
                'CAP_PROP_FRAME_HEIGHT', 'CAP_PROP_FPS', 'CAP_PROP_FOURCC', 'CAP_PROP_FRAME_COUNT', 'CAP_PROP_FORMAT',
                'CAP_PROP_MODE', 'CAP_PROP_BRIGHTNESS', 'CAP_PROP_CONTRAST', 'CAP_PROP_SATURATION', 'CAP_PROP_HUE',
                'CAP_PROP_GAIN', 'CAP_PROP_EXPOSURE', 'CAP_PROP_CONVERT_RGB', 'CAP_PROP_WHITE_BALANCE_BLUE_U',
                'CAP_PROP_RECTIFICATION', 'CAP_PROP_MONOCHROME', 'CAP_PROP_SHARPNESS', 'CAP_PROP_AUTO_EXPOSURE',
                'CAP_PROP_GAMMA', 'CAP_PROP_TEMPERATURE', 'CAP_PROP_TRIGGER', 'CAP_PROP_TRIGGER_DELAY',
                'CAP_PROP_WHITE_BALANCE_RED_V', 'CAP_PROP_ZOOM', 'CAP_PROP_FOCUS', 'CAP_PROP_GUID',
                'CAP_PROP_ISO_SPEED', 'CAP_PROP_BACKLIGHT', 'CAP_PROP_PAN', 'CAP_PROP_TILT', 'CAP_PROP_ROLL',
                'CAP_PROP_IRIS', 'CAP_PROP_SETTINGS', 'CAP_PROP_BUFFERSIZE', 'CAP_PROP_AUTOFOCUS']

def decode_fourcc(v):
    v = int(v)
    return "".join([chr((v >> 8 * i) & 0xFF) for i in range(4)])

devices_cv = FilterGraph().get_input_devices()
available_cameras = {}
for device_index in range(len(devices_cv)):
    available_cameras[device_index] = devices_cv[device_index]
print(f'Available camera: {available_cameras}\n')


cam = cv2.VideoCapture(0)
# cam = cv2.VideoCapture(0, cv2.CAP_MSMF) 
# cam = cv2.VideoCapture(0, cv2.CAP_V4L2) 
# cam = cv2.VideoCapture(0, cv2.CAP_FFMPEG)
# cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not (cam.isOpened()):
    print("Could not open camera.")
    sys.exit()
else:
    print("Backend Name:", cam.getBackendName())
    str = 'Old Camera settings: '
    for i in range(len(fourcc_names)):
        str = f'{str}{fourcc_names[i]}:{cam.get(i)}; '
    print(f'{str}')


cam.set(cv2.CAP_PROP_FRAME_WIDTH, 4200)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 3120)
width, height = cam.get(cv2.CAP_PROP_FRAME_WIDTH), cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
width, height = int(width), int(height)

cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('G','R','E','Y'))
# fmt = cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y','8',' ',' '))
# fmt = cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', '1', '6', ' '))


cam.set(cv2.CAP_PROP_CONVERT_RGB, 0)
# cam.set(cv2.cvtColor(cv2.COLOR_YUV2GRAY_Y422))

# Fetch undecoded RAW video streams
cam.set(cv2.CAP_PROP_FORMAT, -1)  # value -1 to fetch undecoded RAW video streams (as Mat 8UC1)
# cam.set(cv2.CAP_PROP_FORMAT, cv2.CV_8UC1)

cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # 3: auto; 1: manual
# cam.set(cv2.CAP_PROP_SETTINGS, 1)

cam.set(cv2.CAP_PROP_FPS, 20)
cam.set(cv2.CAP_PROP_EXPOSURE, -8)
cam.set(cv2.CAP_PROP_GAIN, 0)
cam.set(cv2.CAP_PROP_GAMMA, 1)


# Check whether camera settings are applied
str = 'New camera settings: '
for i in range(len(fourcc_names)):
    str = f'{str}{fourcc_names[i]}:{cam.get(i)}; '
print(str)


success, frame = cam.read()
print(success)
if success:
    print(f'frame.shape = {frame.shape}, frame.dtype = {frame.dtype}')

    frame = frame.astype(np.uint16)*255

    show_camera_image(frame)

    cam_name = re.sub(r'\s+', '_', available_cameras[0])

    cv2.imwrite( f'{out_dir}{cam_name}_test_image.tiff', frame, [cv2.IMWRITE_TIFF_COMPRESSION, 1])

else:
    print('failed to grab frame')


cam.release()
cv2.destroyAllWindows()