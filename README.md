# 433SS - 433 MHz Sensor Service

Receives 433 MHz sensor broadcasts using a rtlsdr receiver and the [rtl_433](https://github.com/merbanan/rtl_433) application. The service parses received broadcasts and outputs the sensor information to desired output (like: log file, MQTT). In short: a (simple) wrapper for rtl_433.

It supports multiple outputs at once, but is primarily made to publish sensor updates via MQTT.

## Installation
Install requirements, adjust settings (if needed) and then run the application.
```
pip install -r requirements.txt
vim sensorservice.cfg
python sensorservice.py
```

## Settings
Settings are stored in `sensorservice.cfg` and are read at start. If no settings are specified, specified incorrectly or no .cfg file exits, default values are used.

### Default settings

**main**
| Argument  | Value      | Default          | Description                        |
|-----------|------------|------------------|------------------------------------|
| binary    | file path  | /usr/bin/rtl_433 | The path for the `rtl_433` binary. |
| debug     | True/False | False            | Turns on or off debug messages.    |
| frequency | integer    | 433748300        | The frequency in Hz to tune to.    |

**file**
| Argument | Value     | Default         | Description                                   |
|----------|-----------|-----------------|-----------------------------------------------|
| path     | file path | /tmp/433sensors | The path to the directory to output files to. |

**mqtt**
| Argument  | Value       | Default | Description                           |
|-----------|-------------|---------|---------------------------------------|
| broker    | IP/hostname |         | The MQTT broker server address.       |
| port      | integer     | 1883    | The port number for the MQTT server.  |
| username  | string      |         | The username for login on the broker. |
| password  | string      |         | The password for login on the broker. |

**alias** (accepts one line per sensor)
| Argument    | Value  | Default | Description                                            |
|-------------|--------|---------|--------------------------------------------------------|
| <sensor id> | string |         | An alias to use in logs and messages for given sensor. |
