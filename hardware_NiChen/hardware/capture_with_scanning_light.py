'''
Scanning capture

- Make sure the scanning step is smaller than the pixel size of the camera
- Adjust the exposure time of the camera to avoid saturation

'''


import sys

from ptychography import save_config_to_file, spiral_pattern

sys.path.append("../function")
sys.path.append("../hardware")

from camera import *
from translation_stage import *
import matplotlib.pyplot as plt
import os


plt.rcParams.update({'font.size': 12})


sys_params = {
    'file_type': 'tiff',
    'shifts': [0, 0],
    'wavelen': 405e-9,
    'pp_sensor': 1.1e-6,
    'z_ms': 0,
    'z_om': 0,
}

# out_dir = "../../data/light_tillia_405nm_110um_far/raw/"
out_dir = "../../data/light_convallaria_405nm_110um_far/raw/"


if not os.path.exists(out_dir):
   os.makedirs(out_dir)
   save_config_to_file(sys_params, f'{out_dir}/config.yaml')
   print("directory is created!")

out_dir = f'{out_dir}/raw/'

# raster scanning, better to use odd numbers to center the scanning
Nx, Ny = 11, 11


Num = Nx*Ny

############################################################
ss = KinesisStage('LST150')     # LST150, Z825, Z812
ss.open(axis_num=2)

# ss.stage_pos = [10031337, -4359278]


# 405nm, 0.028A, pp=1.85um, z1=230mm
# scanning_step = 200e-6
# c = Camera(camera_mode='DFM 37UX226-ML', framerate=20, pixelformat="RGB32 (4000x3000)", exposuretime=1/40)

# 405nm, 0.028A, pp=1.1um, z1=230mm
scanning_step = 500e-6
c = Camera(camera_mode='See3CAM_CU135M_H03R1', gain=1.0, gamma=-1, framerate=20, exposuretime=-6)


# 470nm, 0.028A, pp=1.85um, z1=120mm
# scanning_step = 250e-6
# c = Camera(camera_mode='DFM 37UX226-ML', framerate=20, pixelformat="RGB32 (4000x3000)", exposuretime=1/20)

# c = Camera(camera_mode='Basler daA1920-160um', framerate=30, pixelformat="Mono12", exposuretime=7000)


c.set_camera()

############################################################
# pos = line_pattern(Ny,Nx) * scanning_step / ss.step_in_m
# pos = zigzag_pattern(Ny,Nx) * scanning_step / ss.step_in_m
pos = spiral_pattern(Ny, Nx) * scanning_step / ss.step_in_m

# pos[0, :] += ss.stage_pos[0] + 0.5*np.random.rand(Num) * scanning_step / ss.step_in_m
# pos[1, :] += ss.stage_pos[1] + 0.5*np.random.rand(Num) * scanning_step / ss.step_in_m

scale = 0.5
pos[0, :] += ss.stage_pos[0] + np.random.uniform(-scale, scale, Nx*Ny) * scanning_step / ss.step_in_m
pos[1, :] += ss.stage_pos[1] + np.random.uniform(-scale, scale, Nx*Ny) * scanning_step / ss.step_in_m


fig, ax = plt.subplots(1, 1, sharey=False, figsize=(4,4))
ax.plot(pos[0,:]*1e6*ss.step_in_m, pos[1, :]*1e6*ss.step_in_m, '-bo', markersize=3)
ax.set_xlabel('x axis (um)')
ax.set_ylabel('y axis (um)')
ax.set_title('scanning routine')
plt.show()



############################################################
ss.move_to_origin()

cam_name = re.sub(r'\s+', '_', c.camera_mode)

start = time.time()
for idx in range(Num):
    file_name = f'{out_dir}/{cam_name}_{idx+1:04}.tiff'
    print(f'{idx+1:04}/{Num} scanning position:({pos[1,idx]:02}, {pos[0,idx]:02})')

    ss.move_to(pos[:,idx])
    time.sleep(0.05)

    c.capture(file_name)
    time.sleep(0.05)

c.close()
ss.close()

end = time.time()
print(f'Time cost is {end - start}')

