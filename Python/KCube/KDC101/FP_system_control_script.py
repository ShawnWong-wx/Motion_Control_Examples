"""
created by Xiao Wang 
2:42 AM April 1 2024
University of Arizona, Tucson, AZ
"""

import inspect, functools, time, sys, glob, math, traceback, random
import cv2
from pylablib.devices import Thorlabs
import pypylon.pylon as py
import numpy as np
from typing import Any


class FP_system_control(object):
    """
    Class for Fourier Ptychography system control
    devices: MTS50-Z8 (thorlabs), Balser camera acA3088-57um
    dependencies: pylablib, pypylon, OpenCV
    """

    def __init__(
        self,
        scale=(34555.0, 772970.0, 264.0),
        move_min_velocity=0,
        move_max_velocity=1,
        acceleration=1,
        home_direction="reverse",
        *args,
        **kwargs,
    ) -> None:
        """
        initialize the whole system: translation stages and cameras
        """

        self.motor_SN = [
            device[0] for device in Thorlabs.list_kinesis_devices()
        ]  # translation stage serial number
        print(f"detected translation stage(s) S/N:\n{self.motor_SN}\n")

        self.stage = {}  # store translation stage objects

        ## axis name 'x', 'y', 'z', and 'θ' for renaming translation stages
        self.axis = [chr(97 + 23 + i) for i in range(len(self.motor_SN))]
        if len(self.axis) > 3:
            self.axis[3] = str("\u03B8")

        ## config translation stage parameters
        self.scale = scale  # device unit in [1 mm / scale]
        self.move_min_velocity = move_min_velocity
        self.move_max_velocity = move_max_velocity
        self.acceleration = acceleration
        self.home_direction = home_direction

        print("start to initialize all translation stages:")
        self.init_all_stage()  # initialize all translation stages

        self.tlf = (
            py.TlFactory.GetInstance()
        )  # get instance of the pylon TransportLayerFactory
        self.cam_devices = self.tlf.EnumerateDevices()
        # self.camera_SN = [cam_device.GetSerialNumber() for cam_device in cam_devices] # Basler camera serial number
        self.camera = {}  # store Basler camera objects

    def __str__(self) -> str:
        """
        brief introduction
        """
        return "Fourier Ptychography camera system control"

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        """
        decorator
        """
        pass

    @staticmethod
    def check_name(dict_, name) -> bool:
        """
        check if "name" is in "dict_"
        """
        if name in dict_.keys():
            return True
        else:
            return False

    @staticmethod
    def list_members(obj) -> None:
        """
        list all attributes and methods of "obj"
        """
        # Get members of obj using inspect
        members = inspect.getmembers(obj)

        # Separate attributes and methods
        attributes = []
        methods = []

        for member in members:
            if not inspect.isroutine(member[1]):
                attributes.append(member)
            else:
                methods.append(member)

        # Print labeled attributes and methods
        print("Attributes:")
        for attr in attributes:
            print(f" - {attr[0]}")

        print("\nMethods:")
        for method in methods:
            print(f" - {method[0]}")

    def _search_cam_name(func):
        """
        decorator: check whether the input names are existed or not
        """

        @functools.wraps(func)  # keep original function name
        def wrapper(self, *name_list, **new_name_dict):

            name_list = list(name_list)
            if name_list == []:  # choose all stages if name_list == []
                name_list = list(self.camera.keys())

            exist_list = list(
                map(
                    self.check_name,
                    [self.stage.copy() for _ in range(len(name_list))],
                    name_list,
                )
            )

            if new_name_dict == {}:
                return func(self, name_list, exist_list)
            else:
                return func(self, name_list, list(new_name_dict.values()), exist_list)

        return wrapper

    def _search_stage_name(func):
        """
        decorator: check whether the input names are existed or not
        """

        @functools.wraps(func)  # keep original function name
        def wrapper(self, *name_list, **new_name_dict):

            name_list = list(name_list)
            if name_list == []:  # choose all stages if name_list == []
                name_list = list(self.stage.keys())

            exist_list = list(
                map(
                    self.check_name,
                    [self.stage.copy() for _ in range(len(name_list))],
                    name_list,
                )
            )

            if new_name_dict == {}:
                return func(self, name_list, exist_list)
            else:
                return func(self, name_list, list(new_name_dict.values()), exist_list)

        return wrapper

    def init_all_camera(
        self,
    ) -> None:
        """
        initialize all detected Basler cameras
        """
        for i in len(self.cam_devices):
            SN = self.cam_devices[i].GetSerialNumber()
            self.camera[SN] = py.InstantCamera(
                self.tlf.CreateDevice(self.cam_devices[i])
            )
            self.camera[SN].Open()
            self.camera[SN].UserSetSelector = "Default"
            self.camera[SN].UserSetLoad.Execute()
            self.camera[SN].ExposureMode.Value = "Timed"
            self.camera[SN].ExposureAuto.Value = "Off"
            self.camera[SN].ExposureTime = self.camera[SN].ExposureTime.Min
            self.camera[SN].AcquisitionFrameRateEnable.Value = True
            self.camera[SN].PixelFormat.Value = "Mono8"
            self.camera[SN].GainAuto.Value = "Off"
            self.camera[SN].Gain.Value = 0

    def init_all_stage(
        self,
    ) -> None:
        """
        initialize all detected translation stages
        """

        for SN in self.motor_SN:
            print(f"initializing {SN}:", end=" ")
            self.stage[SN] = Thorlabs.KinesisMotor(
                SN, self.scale
            )  # connect to stage and set scale. [1 mm / scale]

            ## config moving velocity
            self.stage[SN].setup_velocity(
                min_velocity=self.move_min_velocity,
                max_velocity=self.move_max_velocity,
                acceleration=self.acceleration,
            )

            ## config home mode
            self.stage[SN].setup_homing(
                velocity=self.move_max_velocity,
                home_direction=self.home_direction,
                limit_switch=self.home_direction,
            )

            ## config jog mode
            self.stage[SN].setup_jog(
                min_velocity=self.move_min_velocity,
                max_velocity=self.move_max_velocity,
                acceleration=self.acceleration,
            )

            self.stage[SN].home(force=True)  # home the stage
            self.stage[SN].wait_for_home()  # wait for "home"
            time.sleep(1)  # wait to be stable

            print("finished.", end=" ")
            print(f"current position: {self.stage[SN].get_position()} [mm]")

        time.sleep(1)  # wait to be stable
        print(f"stage(s) {self.motor_SN} initialization finished! \n")

    @_search_stage_name
    def change_stage_name(
        self, old_name_list: list = [], new_name_list: list = [], exit_list: list = []
    ) -> None:
        """
        change translation stage's name
        """
        operate_name_list = []
        for old_name, new_name, exit_flag in zip(
            old_name_list, new_name_list, exit_list
        ):
            if exit_flag:
                self.stage[new_name] = self.stage.pop(old_name)
                operate_name_list.append(old_name)
            else:
                print(f"cannot find stage {old_name}")

        print(f"stage(s) {operate_name_list} finished renaming!\n")
        self.get_all_stage_name()

    @_search_stage_name
    def close_stages(self, name_list: list = [], exit_list: list = []) -> None:
        """
        turn off the connection to translation stage(s)
        default: close all connected translation stage(s)
        """
        operate_name_list = []
        for name, exit_flag in zip(name_list, exit_list):
            if exit_flag:
                self.stage[name].close()
                self.stage.pop(name)
                operate_name_list.append(name)
                # print(f"closed translation stage {name}")
            else:
                print(f"cannot find stage {name}")

        self.motor_SN = [device[0] for device in Thorlabs.list_kinesis_devices()]
        print(f"stage(s) {operate_name_list} finished close!\n")
        self.get_all_stage_name()

    @_search_stage_name
    def get_stage_position(self, name_list: list = [], exit_list: list = []) -> None:
        """
        acquire translation stage's position in [mm]
        """
        for name, exit_flag in zip(name_list, exit_list):
            if exit_flag:
                print(
                    f"stage {name}'s current position: {self.stage[name].get_position()} [mm]"
                )
            else:
                print(f"cannot find stage {name}")

        print()

    @_search_stage_name
    def get_stage_full_info(self, name_list: list = [], exit_list: list = []) -> None:
        """
        acquire the full info of translation stage
        """
        for name, exit_flag in zip(name_list, exit_list):
            if exit_flag:

                print(f"stage {name}'s info:")

                for key, value in self.stage[name].get_full_info().items():
                    print(f"{key}: {value}")

                print()
                print()
            else:
                print(f"cannot find stage {name}")

        print()

    @_search_stage_name
    def home_stage(self, name_list: list = [], exit_list: list = []) -> None:
        """
        home translation stage(s)
        """
        operate_name_list = []
        for name, exit_flag in zip(name_list, exit_list):
            if exit_flag:
                print(f"homing stage {name}:", end=" ")
                self.stage[name].home(force=True)  # home the stage
                self.stage[name].wait_for_home()  # wait for "home"
                operate_name_list.append(name)
                time.sleep(1)  # wait to be stable
                print(f"finished!")
                self.get_stage_position(name)
            else:
                print(f"cannot find stage {name}")
        time.sleep(1)
        print(f"stage(s) {operate_name_list} finished homing!\n")

    @_search_stage_name
    def move_stage(
        self, name_list: list = [], pos_list: list = [], exit_list: list = []
    ) -> None:
        """
        move translation stage(s) to a position
        """
        operate_name_list = []
        for name, pos, exit_flag in zip(name_list, pos_list, exit_list):
            if exit_flag:
                print(f"moving stage {name} to position {pos} [mm]:", end=" ")
                self.stage[name].move_to(pos)
                self.stage[name].wait_move()  # wait for moving
                operate_name_list.append(name)
                time.sleep(1)  # wait to be stable
                print("finished!")
            else:
                print(f"cannot find stage {name}")

        time.sleep(1)  # wait to be stable
        print(f"stage(s) {operate_name_list} finished moving!\n")
        self.get_stage_position()

    def get_all_stage_name(self) -> None:
        """
        get all connected stage(s) name
        """
        print("currently connected translation stage(s):")
        for name, sn_num in zip(
            list(self.stage.keys()),
            [device[0] for device in Thorlabs.list_kinesis_devices()],
        ):
            print(f"S/N {sn_num}: {name}")

        print()

    def move_cam_xy(self, pos=[], max_range=[50, 50]) -> None:
        """
        move the camera(s) to a (x,y) position

        define the coordinate system based on the back view of camera(s) as follows
        y(+)
          ^
          |
          |
          o------->x(+)
        """
        horizontal_move = -pos[0] + max_range[0] / 2
        vertical_move = -pos[1] + max_range[1] / 2
        self.move_stage(
            "vertical", "horizontal", first=vertical_move, second=horizontal_move
        )
        print(f"camera(s) is(are) at {pos} [mm]!")

    def move_cam_xyz(self, pos=[], max_range=[50.0, 50.0, 50.0]) -> None:
        """
        move the camera(s) to a (x,y,z) position

        define the coordinate system based on the back view of camera(s) as follows
        y(+)  z(+)
          ^  /
          | /
          |/
          o------->x(+)

        todo
        """

        pass

    def rotate_obj(self, deg: float = 0) -> None:
        """
        rotate the object by degrees

        todo
        """
        pass

    def cam_capture(
        self, cam_name: str, frame_num: int = 100, exp_time: float = 1000.0
    ) -> None:
        """
        use camera to capture frames for each exposure times
        return a averaged image
        """
        # fetch some images with foreground loop
        cam = self.camera[cam_name]  # default is SN
        cam.ExposureTime.Value = exp_time  # [μs]
        img_sum = np.zeros((cam.Height.Value, cam.Width.Value), dtype=np.float32)
        cam.StartGrabbingMax(frame_num)
        while cam.IsGrabbing():
            with cam.RetrieveResult(1000) as res:
                if res.GrabSucceeded():
                    img = res.Array
                    img_sum += img
                else:
                    raise RuntimeError("Grab failed")
        cam.StopGrabbing()
        self.img_avrg = img_sum / frame_num
        return self.img_avrg

    def close_all_cams(
        self,
    ) -> None:
        """
        close all cameras
        """
        for name, cam_obj in self.camera.items():
            self.camera[name].Close()

    @staticmethod
    def save_img(img, name: str, path: str) -> None:
        """
        save an image to the designated path
        """
        np.save(path + "/" + name + ".npy", img)
        cv2.imwrite(path + "/" + name + ".bmp", img)
        print(f"{name} is saved!")
