#!/usr/bin/env python
"""433SS - 433 MHz Sensor Service using rtl_433."""

import json
import os
import subprocess
import sys
import ConfigParser
import paho.mqtt.client as paho


def execute(command):
    """Execute given command in a subprocess."""
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        if nextline == "" and process.poll() is not None:
            break

        # Parse line for data (from 'nextline')
        parse_line(nextline)

    output = process.communicate()[0]
    exit_code = process.returncode

    if exit_code != 0:
        raise Exception(command, exit_code, output)

    return output


def parse_line(line):
    """Parse given line for sensor data."""
    if "Tuned to " in line:
        print("Tuner started. Waiting for sensor data...")

        # Turn on line parsing after tuner has initiolized
        SETTINGS['parse_lines'] = True

    # JSON output
    if SETTINGS['parse_lines']:
        try:
            json_line = json.loads(line)

            if json_line is not None:
                process_json_data(json_line)
        except KeyError as ex:
            if SETTINGS['debug']:
                print("Parse error, invalid key: {}".format(ex))
        except TypeError as ex:
            if SETTINGS['debug']:
                print("Parse error, type error: {}".format(ex))
        except Exception:  # pylint: disable=W0703
            print("Parse error!\n{}".format(sys.exc_info()[0]))


def process_json_data(json_line):
    """Handle the JSON data."""
    if json_line["model"] == "Prologue sensor":
        sensorid = "{}.{}.{}".format(
            json_line["id"],
            json_line["rid"],
            json_line["channel"])
        process_output(sensorid, "battery", json_line["battery"])
        process_output(sensorid, "button", json_line["button"])
        process_output(
            sensorid, "temperature",
            round(float(json_line["temperature_C"]), 1))
        hum_str = str(json_line["humidity"])[::-1]
        if len(hum_str) > 2:
            hum_str = "{}.{}".format(hum_str[0:2], hum_str[2:3])
            process_output(sensorid, "humidity", float(hum_str))
        else:
            process_output(
                sensorid, "humidity", int(json_line["humidity"]))
    elif json_line["model"] == "WT450 sensor":
        sensorid = "{}.{}".format(
            json_line["id"], json_line["channel"])
        process_output(
            sensorid, "temperature",
            round(float(json_line["temperature_C"]), 1))
        process_output(
            sensorid, "humidity", int(json_line["humidity"]))
        process_output(sensorid, "battery", json_line["battery"])
    elif json_line["model"] == "Nexus Temperature":
        sensorid = "{}.{}".format(
            json_line["id"], json_line["channel"])
        process_output(sensorid, "battery", json_line["battery"])
        process_output(
            sensorid, "temperature",
            round(float(json_line["temperature_C"]), 1))


def process_output(sensorid, sensortype, value):
    """Handle the parsed sensor data."""
    for sensor, alias in SETTINGS['alias_list']:
        if sensorid == sensor:
            sensorid = alias
            break

    if SETTINGS['output_file']:
        update_file(sensorid, sensortype, value)

    if SETTINGS['output_mqtt']:
        topic = "home/{}/{}".format(sensorid, sensortype)
        message = value  # usually no modifications needed
        publish_mqtt(topic, message)


def publish_mqtt(topic, message):
    """Publish given message under specified topic."""
    try:
        mqttc = paho.Client("433ss")
        # mqttc.will_set("/event/dropped", "Sorry, I seem to have died.")
        mqttc.on_publish = on_publish
        mqttc.username_pw_set(
            SETTINGS['mqtt_username'], SETTINGS['mqtt_password'])
        mqttc.connect(SETTINGS['mqtt_broker'], SETTINGS['mqtt_port'], 60)
        mqttc.publish(topic, message)
    except Exception as ex:  # pylint: disable=W0703
        print("MQTT error!\n{}".format(ex))


def on_publish(client, packet, mid):  # pylint: disable=W0613
    """Run once MQTT message is published."""
    client.disconnect()


def update_file(sensorid, sensortype, value):
    """Update sensor data file."""
    if os.path.isdir(SETTINGS['file_path']) is False:
        os.makedirs(SETTINGS['file_path'])

    datafile = "%s/%s-%s" % (SETTINGS['file_path'], sensorid, sensortype)

    file_handle = open(datafile, 'w')
    file_handle.write("{}".format(value))
    file_handle.close()


def remove_old_sensors():
    """Remove old sensor data files."""
    if os.path.isdir(SETTINGS['file_path']) is True:
        for fileitem in os.listdir(SETTINGS['file_path']):
            filepath = "{}/{}".format(SETTINGS['file_path'], fileitem)
            os.remove(filepath)


def get_default_settings():
    """Return a dict of default values."""
    default_settings = {
        'debug': False,
        'parse_lines': False,
        'output_file': False,
        'output_mqtt': False,
        'frequency': 433748300,
        'binary': "/usr/bin/rtl_433",
        'file_path': "/tmp/433sensors",
        'mqtt_broker': "",
        'mqtt_port': 1883,
        'mqtt_username': "",
        'mqtt_password': ""
    }

    return default_settings


def read_settings():
    """Read settings from .cfg file."""
    file_settings = get_default_settings()

    if os.path.exists("sensorservice.cfg"):
        try:
            config = ConfigParser.ConfigParser()
            config.read("sensorservice.cfg")

            if config.has_section("main"):
                debug_string = config.get("main", "debug")
                if debug_string.lower() == 'true':
                    file_settings['debug'] = True
                file_settings['frequency'] = config.getint("main", "frequency")
                file_settings['binary'] = config.get("main", "binary")

            if config.has_section("file"):
                file_settings['file_path'] = config.get("file", "path")
                file_settings['output_file'] = True

            if config.has_section("mqtt"):
                file_settings['mqtt_broker'] = config.get("mqtt", "broker")
                file_settings['mqtt_port'] = config.get("mqtt", "port")
                file_settings['mqtt_username'] = config.get("mqtt", "username")
                file_settings['mqtt_password'] = config.get("mqtt", "password")
                file_settings['output_mqtt'] = True

            if config.has_section("alias"):
                file_settings['alias_list'] = config.items("alias")
        except ConfigParser.NoSectionError:
            print("Missing section, ignoring settings from file.")
            file_settings = get_default_settings()
        except ConfigParser.NoOptionError:
            print("Missing value, ignoring settings from file.")
            file_settings = get_default_settings()

    return file_settings


if __name__ == "__main__":
    SETTINGS = read_settings()

    try:
        # Run main loop
        RTL_433 = "{} -F json -f {}".format(
            SETTINGS['binary'], SETTINGS['frequency'])
        RETURNCODE = execute(RTL_433)
        print("Execution stopped ({}). Exiting...".format(RETURNCODE))
        remove_old_sensors()
    except KeyboardInterrupt:
        print("\nUser stopped execution. Exiting...")
        remove_old_sensors()
        sys.exit()
    except Exception as ex:  # pylint: disable=W0703
        print("Error!\n{}".format(ex.args))
        remove_old_sensors()
