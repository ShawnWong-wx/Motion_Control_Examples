# Scanning capture
import time
import numpy as np
from camera import Camera
import matplotlib.pyplot as plt
import os

from ptychography import spiral_pattern, save_config_to_file
from translation_stage import KinesisStage

plt.rcParams.update({'font.size': 12})


sys_params = {
    'file_type': 'tiff',
    'shifts': [0, 0],
    'wavelen': 405e-9,
    'pp_sensor': 2e-6,
    'z_ms': 0,
    'z_om': 0,
}


out_dir = "../../data/mask_usaf/raw"


if not os.path.exists(out_dir):
   os.makedirs(out_dir)
   save_config_to_file(sys_params, f'{out_dir}/config.yaml')
   print("directory is created!")

out_dir = f'{out_dir}/raw/'

# raster scanning, better to use odd numbers to center the scanning
Nx, Ny = 39, 39
scanning_step = 6e-6
# scanning_step = 8e-6

Num = Nx*Ny

############################################################
ss = KinesisStage('LST150')      # LST150, Z825, Z812
ss.open(axis_num=2)

print(ss.stage_pos)

ss.stage_pos = [7666288, 5555843]

# Camera could be pylon or opencv
c = Camera(camera_type='pylon', brightness=0.0, contrast=0.0, gain=0.0, framerate=30, pixelformat="Mono12",
           exposuretime=220)     # blue laser, 30mA

# c = Camera(camera_type='pylon', brightness=0.0, contrast=0.0, gain=0.0, framerate=30, pixelformat="Mono12",
#            exposuretime=8500)     # red laser, 70mA
# c = Camera(camera_type='opencv', brightness=0, contrast=0, gain=12, framerate=20, gamma=120,
#            exposuretime=1/250)
c.set_camera()

############################################################
# pos = line_pattern(Ny,Nx) * scanning_step / ss.step_in_m
# pos = zigzag_pattern(Ny,Nx) * scanning_step / ss.step_in_m
pos = spiral_pattern(Ny, Nx) * scanning_step / ss.step_in_m

pos[0, 1:] += 0.15*np.random.randn(Num-1) * scanning_step / ss.step_in_m
pos[1, 1:] += 0.15*np.random.randn(Num-1) * scanning_step / ss.step_in_m

fig, ax = plt.subplots(1, 1, sharey=False, figsize=(7,6))
ax.plot(pos[0,:]*1e6*ss.step_in_m, pos[1, :]*1e6*ss.step_in_m,'-bo', markersize=3)
ax.set_xlabel('x axis (um)')
ax.set_ylabel('y axis (um)')
ax.set_title('scanning routine')
plt.axis('scaled')
plt.show()

pos[0, :] += ss.stage_pos[0]
pos[1, :] += ss.stage_pos[1]

############################################################
ss.move_to_origin()

start = time.time()
for idx in range(Num):
    file_name = f'{out_dir}/img{idx+1:04}.tiff'
    print(f'{idx+1:04}/{Num} scanning position:({pos[1,idx]:02}, {pos[0,idx]:02})')

    ss.move_to(pos[:,idx])
    time.sleep(0.1)

    c.capture(file_name)
    # time.sleep(0.05)

c.close()
ss.close()

end = time.time()
print(f'Time cost is {end - start}')

