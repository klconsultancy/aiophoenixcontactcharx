# B 3 Modbus communication and register overview

#### Preparation of the configuration

- The Modbus server must be running, see “System Control/Status” (WBM: System Control, Status)
- Port 502 must be open, “Network/Port Sharing”
- If you want to control the full scope of functions, you must set charging to be enabled via Modbus, see “Charging Stations/Charge Point/Configuration” (under “Release Mode”)
- If the phase rotation of one of the configured charging points is not known, then the register for total current will indicate the value “-1” (placeholder to indicate that the value is invalid).
ℹ️ If you modify a configuration, you will need to restart the Modbus server or the charging controller, see “System Control/Status” (WBM: System Control, Status)
#### General communication data

Table B-6 General communication data
| Attribute | Data |
| --- | --- |
| Modbus server address | 1 |
| Port | 502 |
| Object type | Holding, 16-bit |

Holding register (0x03) and Input register (0x04) return the same value
#### Modbus register

Address range 0-999 relates to data that is assigned to the overall installation. This includes charging controllers that are attached via the backplane bus of the server as well as clients connected via Ethernet and the extension modules that are attached to them.
Address range x000-x999 relates to data that is assigned to an individual charging point. The x stands for the assigned number of the charging point.
Table B-7 Modbus register in address range 0-999
| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| Charging station data (100 - 199) | Charging station data (100 - 199) | Charging station data (100 - 199) | Charging station data (100 - 199) | Charging station data (100 - 199) |
| 100 | 10 | R | Device designation | 20 characters, ASCII coded |
| 110 | 4 | R | Linux software version | 8 characters, ASCII coded |
| 114 | 1 | R | Number of charging controllers in the system (backplane bus and in the Ethernet network) | Integer |
| 115 | 3 | R | MAC address ETH0 | HEX characters |
| 118 | 3 | R | MAC address ETH1 | HEX characters |
| 121 | 4 | R | IPv4 IP address ETH0 | 4x integer |
| 125 | 4 | R | IPv4 IP address ETH1 | 4x integer |
| 129 | 4 | R | Subnet mask ETH0 | 4x integer |

Table B-7 Modbus register in address range 0-999 [...]
| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| 133 | 4 | R | Subnet mask ETH1 | 4x integer |
| 137 | 4 | R | Gateway ETH0 (placeholder, re-turns 0) | 4x integer |
| 141 | 4 | R | Gateway ETH1 (placeholder, re-turns 0) | 4x integer |
| 145 | 1 | R | Modem registration status | Integer 0: Not registered / Not searching 1: Registered 2: Searching 3: Registration denied 4: Unknown |
| 146 | 1 | R | Modem signal quality | Integer 0: Unknown 1: Inadequate to none 2: Inadequate 3: OK 4: Good 5: Excellent |
| 147 | 1 | R | Number of charging controllers in the system (backplane bus and in the Ethernet network) in the non-critical error state | Integer |
| 148 | 1 | R | Number of charging controllers in the system (backplane bus and in the Ethernet network) which re-sults in status E or F | Integer |
| 149 | 1 | R | Number of charging controllers in status A in the system (backplane bus and in the Ethernet network)/number of unoccupied charging points in the system | Integer |
| 150 | 1 | R | Number of charging controllers in status B, C, or D in the system (backplane bus and in the Ethernet network) / number of occupied charging points | Integer |
| 151 | 1 | R | Number of charging controllers with an active charging process (C2) | Integer |

Table B-7 Modbus register in address range 0-999 [...]
| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| 152 | 2 | R | Total power measured at the ter-minal point for the group of charging controllers. Aggregated power of the configured charging points | Integer [mW] |
| 154 | 2 | R | Total reactive power measured at the terminal point for the group of charging controllers. Aggregated power of the configured charging points | Integer [mVAR] |
| 156 | 2 | R | Total apparent power measured at the terminal point for the group of charging controllers. Aggregated power of the configured charging points | Integer [mVA] |
| 158 | 2 | R | Total current on phase L1 mea-sured at the terminal point for the group of charging controllers. Ag-gregated current of the configured charging points, no phase delay | Integer [mA] -1, if phase rotation = unknown |
| 160 | 2 | R | Total current on phase L2 mea-sured at the terminal point for the group of charging controllers. Ag-gregated current of the configured charging points, no phase delay | Integer [mA] -1, if phase rotation = unknown |
| 162 | 2 | R | Total current on phase L3 mea-sured at the terminal point for the group of charging controllers. Ag-gregated current of the configured charging points, no phase delay | Integer [mA] -1, wenn Phasendrehung = un-bekannt |
| 164 | 1 | R/(W, if configured) | Controlling the availability of the charging controller | 0: All assigned charging controllers are set to status F |
| 164 | 1 | R/(W, if configured) | Controlling the availability of the charging controller | 1: All assigned charging controllers are in normal operating mode |
| 165 | 1 | W | Reset | 1: Charging controller restart (only performed on the server) |
| 166 | 1 | W | System reset | 1: Restart of all charging controllers connected in the group |
| 167 | 1 | R/W | Dynamic maximum target charging current for load management. With reference to the first load circuit | Integer [A] |

Table B-8 Modbus registers for the respective charging point
| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| Configuration data (x100 - x199) | Configuration data (x100 - x199) | Configuration data (x100 - x199) | Configuration data (x100 - x199) | Configuration data (x100 - x199) |
| X100 | 1 | R | Configuration of the charging inter-face in accordance with IEC 61851-1 | 0: Charging case B (charging socket) |
| X100 | 1 | R | Configuration of the charging inter-face in accordance with IEC 61851-1 | 1: Charging case C (charging connector) |
| X101 | 1 | R | Set maximum charging current for the respective charging point | Integer [A] |
| X102 | 1 | R | Set minimum charging current for the respective charging point | Integer [A] |
| X103 | 1 | R | Residual current monitoring via input RCM | 1: External residual current sensor configured |
| X103 | 1 | R | Residual current monitoring via input RCM | 0: No external residual current sensor configured |
| X104 | 1 | R | Lower temperature threshold for starting derating mode (Pt 1000 sensor active) | Integer [°C] |
| X105 | 1 | R | Upper temperature threshold for stopping derating mode (Pt 1000 sensor active) | Integer [°C] |
| X106 | 1 | R | Charging current setting when der-ating mode is started | Integer [A] |
| X107 | 1 | R | Charging current setting when der-ating mode is stopped | Integer [A] |
| X108 | 1 | R | Temperature monitoring | 0: Inactive |
| X108 | 1 | R | Temperature monitoring | 1: With Pt 1000 sensor |
| X108 | 1 | R | Temperature monitoring | 2: With PTC sensor |
| X109 | 1 | R | Accept vehicles in status D | 0: Blocked |
| X109 | 1 | R | Accept vehicles in status D | 1: Allow |
| X110 | 1 | R | Configuration of proximity evalua-tion | 0: In accordance with IEC 61851-1 |
| X111 | 1 | R | Configuration of overcurrent moni-toring | 0: Inactive |
| X111 | 1 | R | Configuration of overcurrent moni-toring | 1: Shutdown thresholds 120% (10 s) and 110% (100 s) |
| X111 | 1 | R | Configuration of overcurrent moni-toring | 2: As per EV/ZE Ready |

| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| X112 | 1 | R | Energy measuring device type | 0: No energy measuring device |
| X112 | 1 | R | Energy measuring device type | 1: Phoenix Contact EEM-350-D-MCB, 2905849 |
| X112 | 1 | R | Energy measuring device type | 2: Phoenix Contact EEM-EM357, 2908588 EEM-DM357, 1252817 EEM-DM357-70, 1219095 |
| X112 | 1 | R | Energy measuring device type | 3: Carlo Gavazzi EM24 |
| X112 | 1 | R | Energy measuring device type | 4: Phoenix Contact EEM-EM357-EE - 1311985 |
| X112 | 1 | R | Energy measuring device type | 5: Reserved |
| X112 | 1 | R | Energy measuring device type | 6: Carlo Gavazzi EM340 |
| X112 | 1 | R | Energy measuring device type | 7: Reserved |
| X112 | 1 | R | Energy measuring device type | 8: Reserved |
| X112 | 1 | R | Energy measuring device type | 9: Reserved |
| X112 | 1 | R | Energy measuring device type | 10: Reserved |
| X112 | 1 | R | Energy measuring device type | 11: Iskra WM3M4(C) |
| X112 | 1 | R | Energy measuring device type | 12: Inepro Metering PRO380 |
| X112 | 1 | R | Energy measuring device type | 65535: Unknown energy measuring device |
| X113 | 3 | R | UID of the charging controller | ASCII |
| X116 | 3 | R | UID of the associated client or server charging controller | ASCII |
| X119 | 1 | R | Position of the charging controller in the backplane bus | Integer |
| X120 | 1 | R | Charging controller charging release mode | 0: Dashboard |
| X120 | 1 | R | Charging controller charging release mode | 1: Local whitelist |
| X120 | 1 | R | Charging controller charging release mode | 2: External Control |
| X120 | 1 | R | Charging controller charging release mode | 3: Permanent Charging Release |
| X120 | 1 | R | Charging controller charging release mode | 4: OCPP |
| X120 | 1 | R | Charging controller charging release mode | 5: Modbus |
| X121 | 3 | R | RFID reader, UID of the charging controller (placeholder, returns 0) | 6 characters, ASCII |

| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| Status data (x200 - x299) | Status data (x200 - x299) | Status data (x200 - x299) | Status data (x200 - x299) | Status data (x200 - x299) |
| X232 | 2 | R | Voltage of phase L1 | Integer [mV] |
| X232 | 2 | R | Voltage of phase L1 | (X232=MSW, X233=LSW) |
| X234 | 2 | R | Voltage of phase L2 | Integer [mV] |
| X236 | 2 | R | Voltage of phase L3 | Integer [mV] |
| X238 | 2 | R | Current of phase L1 | Integer [mA] |
| X238 | 2 | R | Current of phase L1 | (X238=MSW, X239=LSW) |
| X240 | 2 | R | Current of phase L2 | Integer [mA] |
| X242 | 2 | R | Current of phase L3 | Integer [mA] |
| X244 | 2 | R | Active power | Integer [mW] |
| X246 | 2 | R | Reactive power | Signed Integer [mVAR] |
| X248 | 2 | R | Apparent power | Integer [mVA] |
| X250 | 4 | R | Counter value for active energy | Integer [Wh] |
| X254 | 4 | R | Counter value for reactive energy | Signed Integer [VARh] |
| X258 | 4 | R | Counter value for apparent energy | Integer [VAh] |
| x262 | 2 | R | SOC in kWh (placeholder, returns 0) | Integer [Wh], as of ISO 15118-20 |
| x264 | 1 | R | SOC in % (placeholder, returns 0) | Integer [%], as of ISO 15118-20 |
| X265 | 10 | R | Last EVCC ID at the charging point | ASCII |
| X275 | 10 | R | Last RFID UID at the charging point | ASCII |
| X285 | 2 | R | Connection time (time in status B/C/D) | Integer [s] |
| X287 | 2 | R | Total charging duration in status C/D, reset by status change from B  A | Integer [s] |
| x289 | 4 | R | Transmitted active energy for the current charging process | Integer [Wh] |
| X293 | 2 | R | Error code | Hexadecimal, an error bit is assigned to every single error, see “Error codes” on page 157 |
| X293 | 2 | R | Error code | MSB: X293, LSB: X294 |
| X293 | 2 | R | Error code | Example: X293=0x0000, X294=0040 = RFID reader error |
| X295 | 1 | R | Digital inputs | Binary, 1 bit per input |
| X296 | 1 | R | Current charging current setting (PWM duty cycle in accordance with IEC 61851-1) | Integer [%] |
| X297 | 1 | R | Current charging current setting (current strength) | Integer [A] |

| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| X298 | 1 | R | Current carrying capacity of the plugged-in charging connector in accordance with IEC 61851-1 | Integer [A] |
| X299 | 1 | R | Vehicle status in accordance with IEC 61851-1 | ASCII |
| X299 | 1 | R | Vehicle status in accordance with IEC 61851-1 | (A1, A2, B1, B2, C1, C2, E0, F0, IN) |
| Control registers (x300 - x399) | Control registers (x300 - x399) | Control registers (x300 - x399) | Control registers (x300 - x399) | Control registers (x300 - x399) |
| X300 | 1 | R/ (W, if configured) | Charging release (must be configured to release via Modbus) | 0: Charging process not enabled |
| X300 | 1 | R/ (W, if configured) | Charging release (must be configured to release via Modbus) | 1: Charging process enabled |
| X301 | 1 | R/W | Maximum charging current (can be changed by higher-level systems) Value range: 6 - 80 The charging release is withdrawn if the value is exceeded or fallen below | Integer [A] |
| X302 | 1 | R/W | State of the digital outputs 0: Undefined 1: Floating (“Floating”) 2: Permanent 0 V (“Low”) 3: Flashing 0 V (“Flashing Low”) 4: Pulsating 0 V (“Pulsatile Low”) 5: Permanent 12 V (“High”) 6: Flashing 12 V (“Flashing High”) | Binary-coded, 4 bits per output Example: 0001 0001 0010 0011 Out 4 Out 3 Out 2 Out 1 1 1 2 3 |
| X303 | 1 | R/ (W, if configured) | Locking (must be configured to external control) | 0: Unlocking |
| X303 | 1 | R/ (W, if configured) | Locking (must be configured to external control) | 1: Locking |
| X304 | 1 | R/ (W, if configured) | Status F (availability, must be configured to release via Modbus) | 0: Not available (status F) |
| X304 | 1 | R/ (W, if configured) | Status F (availability, must be configured to release via Modbus) | 1: Available |
| X305 | 1 | R/W | Enforce unlocking (if not configured to external control) | 1: Unlocking is performed |

| URL | Number of data words | Access | Meaning | Value/coding |
| --- | --- | --- | --- | --- |
| X306 | 1 | R/W | Maximum charging current when watchdog timer expires Value range: 6 - 80 The charging release is withdrawn if the value is exceeded or fallen below. | Integer [A] |
| X307 | 1 | R/W | Expiry timer, reset by writing a new value within the time interval; 65535 disables the watchdog | Integer [s] |
| X308 | 1 | R/W | When writing a value > 0 to the register, a reset of register x275 (last RFID tag) is triggered. At the same time, this register is reset to 0 again and is ready for the next delete request. | Integer [A] |
