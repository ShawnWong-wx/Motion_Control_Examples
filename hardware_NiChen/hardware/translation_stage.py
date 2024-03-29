import numpy as np
from pylablib.devices import Thorlabs, Basler
from pypylon import pylon     # https://github.com/basler/pypylon
import platform
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import PercentFormatter
from time import sleep
import os
# from pygrabber.dshow_graph import FilterGraph
import cv2, queue, threading, time
import pylablib

pylablib.par["devices/dlls/basler_pylon"] = "C:/Basler/pylon/Runtime/x64/"




############################################# Translation stage ########################################################
# - XY Stages: Thorlabs [Z825B](https://www.thorlabs.com/thorproduct.cfm?partnumber=Z825B) linear translation stage with [T-Cube DC Servo Controllers](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=5698)

class KinesisStage():
    def __init__(self, stage_type='LST150'):
        super().__init__()
        self.stages = []
        self.stage_pos = []

        # Set step size
        if stage_type == 'LST150':
            self.step_in_m = 150e-3 / 61440000  # in m, 150mm corresponds to 61440000 steps in Kinensis software

        elif stage_type == 'Z825':
            self.step_in_m = 25e-3 / 863874     # in m, 25mm corresponds to 863874 steps in Kinensis software

        elif stage_type == 'Z812':
            self.step_in_m = 12e-3 / 414660     # in m, 25mm corresponds to 863874 steps in Kinensis software
            
        else:
            raise ValueError(f'stage type {stage_type} is not supported')
        

    def open(self, axis_num=2):
        devices = Thorlabs.list_kinesis_devices()
        print(f'{devices}')

        assert len(devices) == axis_num, f'There should be at least {axis_num} device connected to the computer'
        for idx in range(axis_num):
            stage = Thorlabs.KinesisMotor(devices[idx][0])
            stage.setup_jog(stop_mode='profiled', mode='continuous', step_size=1)
            stage.setup_gen_move(backlash_distance=0)

            # get current position
            print(f'{idx}th stage: scale is {stage.get_scale()}, {stage.get_jog_parameters()}')

            p0 = stage.get_position()
            stage.move_to(p0)
            stage.wait_move()

            self.stages.append(stage)
            self.stage_pos.append(stage.get_position())


    def move_to_origin(self):
        for stage, p in zip(self.stages, self.stage_pos):
            stage.move_to(p)
            stage.wait_move()

        print("Reset the stages.")

    def move_to(self, pos):
        for stage, p in zip(self.stages, pos):
            stage.move_to(p)
            stage.wait_move()


    def close(self):
        for stage, pos in zip(self.stages, self.stage_pos):
            stage.move_to(pos)
            stage.wait_move()
            stage.close()

        print("Stages are closed.")


