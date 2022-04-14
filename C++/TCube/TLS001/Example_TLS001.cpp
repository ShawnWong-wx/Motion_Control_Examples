// Example_TLS001.cpp : Defines the entry point for the console application.
//

#include <stdio.h>
#include <stdlib.h>
#include <conio.h>

// Include device-specific header file
#include "Thorlabs.MotionControl.TCube.LaserSource.h"

int __cdecl wmain(int argc, wchar_t* argv[])
{
	// Uncomment this line (and TLI_UnitializeSimulations at the bottom of the page)
	// If you are using a simulated device
	//TLI_InitializeSimulations();

	// Change this line to reflect your device's serial number
	int serialNo = 86000001;

	// Optionally set the power to the device (between 0-32767 representing 0-100% max power)
	WORD power = 0;
	
	// identify and access device
	char testSerialNo[16];
	sprintf_s(testSerialNo, "%d", serialNo);

	// Build list of connected device
    if (TLI_BuildDeviceList() == 0)
    {
		// get device list size 
        short n = TLI_GetDeviceListSize();
		// get BBD serial numbers
        char serialNos[100];
		TLI_GetDeviceListByTypeExt(serialNos, 100, 86);

		// output list of matching devices
		{
			char *searchContext = nullptr;
			char *p = strtok_s(serialNos, ",", &searchContext);

			while (p != nullptr)
			{
				TLI_DeviceInfo deviceInfo;
				// get device info from device
				TLI_GetDeviceInfo(p, &deviceInfo);
				// get strings from device info structure
				char desc[65];
				strncpy_s(desc, deviceInfo.description, 64);
				desc[64] = '\0';
				char serialNo[9];
				strncpy_s(serialNo, deviceInfo.serialNo, 8);
				serialNo[8] = '\0';
				// output
				printf("Found Device %s=%s : %s\r\n", p, serialNo, desc);
				p = strtok_s(nullptr, ",", &searchContext);
			}
		}

		// open device
		if(LS_Open(testSerialNo) == 0)
		{
			// start the device polling at 200ms intervals
			LS_StartPolling(testSerialNo, 200);

			// NOTE The following uses Sleep functions to simulate timing
			// In reality, the program should read the status to check that commands have been completed
			Sleep(1000);

			LS_SetPower(testSerialNo, power);
			printf("Device %s setting power %d\r\n", testSerialNo, power);
			Sleep(1000);

			WORD readPower = LS_GetPowerReading(testSerialNo);
			WORD readCurrent = LS_GetCurrentReading(testSerialNo);
			printf("Device %s read power %d\r\n", testSerialNo, readPower);
			printf("Device %s read current %d\r\n", testSerialNo, readCurrent);

			Sleep(1000);

			// stop polling
			LS_StopPolling(testSerialNo);
			// close device
			LS_Close(testSerialNo);
	    }
    }

	// Uncomment this line if you are using simulations
	//TLI_UnitializeSimulations;
	char c = _getch();
	return 0;
}
