#!/usr/bin/env python

import ConfigParser
import json
import os
import paho.mqtt.client as paho
import subprocess
import sys

parse_lines = False


def execute(command):
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        if nextline == "" and process.poll() is not None:
            break

        # Parse line for data (from 'nextline')
        parseLine(nextline)

    output = process.communicate()[0]
    exitCode = process.returncode

    if (exitCode == 0):
        return output
    else:
        raise Exception(command, exitCode, output)


def findNth(haystack, needle, n):
    parts = haystack.split(needle, n + 1)

    if len(parts) <= n + 1:
        return -1

    return len(haystack) - len(parts[-1]) - len(needle)


def parseLine(line):
    global parse_lines

    if "Tuned to " in line:
        print("Tuner started. Waiting for sensor data...")
        parse_lines = True
        return None

    # JSON output
    if parse_lines:
        try:
            json_line = json.loads(line)

            if json_line is not None:
                if json_line["model"] == "Prologue sensor":
                    sensorid = "{}.{}.{}".format(
                        json_line["id"], json_line["rid"], json_line["channel"])
                    processOutput(sensorid, "battery", json_line["battery"])
                    processOutput(sensorid, "button", json_line["button"])
                    processOutput(
                        sensorid, "temperature",
                        round(float(json_line["temperature_C"]), 1))
                    hum_str = str(json_line["humidity"])[::-1]
                    if len(hum_str) > 2:
                        hum_str = "{}.{}".format(hum_str[0:2], hum_str[2:3])
                        processOutput(sensorid, "humidity", float(hum_str))
                    else:
                        processOutput(sensorid, "humidity", int(json_line["humidity"]))
                elif json_line["model"] == "WT450 sensor":
                    sensorid = "{}.{}".format(
                        json_line["id"], json_line["channel"])
                    processOutput(
                        sensorid, "temperature",
                        round(float(json_line["temperature_C"]), 1))
                    processOutput(sensorid, "humidity", int(json_line["humidity"]))
                    processOutput(sensorid, "battery", json_line["battery"])
                elif json_line["model"] == "Nexus Temperature":
                    sensorid = "{}.{}".format(
                        json_line["id"], json_line["channel"])
                    processOutput(sensorid, "battery", json_line["battery"])
                    processOutput(
                        sensorid, "temperature",
                        round(float(json_line["temperature_C"]), 1))
        except KeyError as ex:
            pass
            # print("Parse error, invalid key: {}".format(ex))
        except TypeError as ex:
            pass
            # print("Parse error, type error: {}".format(ex))
        except:
            print("Parse error!\n{}".format(sys.exc_info()[0]))


def processOutput(sensorid, sensortype, value):
    for sensor, alias in alias_list:
        if sensorid == sensor:
            sensorid = alias
            break

    if output_file:
        updateFile(sensorid, sensortype, value)

    if output_mqtt:
        topic = "home/{}/{}".format(sensorid, sensortype)
        message = value  # usually no modifications needed
        publishMqtt(topic, message)


def publishMqtt(topic, message):
    try:
        mqttc = paho.Client("433ss")
        # mqttc.will_set("/event/dropped", "Sorry, I seem to have died.")
        mqttc.on_publish = onPublish
        mqttc.username_pw_set(mqtt_username, mqtt_password)
        mqttc.connect(mqtt_broker, mqtt_port, 60)

        mqttc.publish(topic, message)
    except Exception as ex:
        print("MQTT error!\n{}".format(ex))


def onPublish(client, packet, mid):
    client.disconnect()


def updateFile(sensorid, sensortype, value):
    if os.path.isdir(file_path) is False:
        os.makedirs(file_path)

    datafile = "%s/%s-%s" % (file_path, sensorid, sensortype)

    f = open(datafile, 'w')
    f.write("{}".format(value))
    f.close()


def removeOldSensors(path):
    if os.path.isdir(file_path) is True:
        for fileitem in os.listdir(path):
            filepath = "{}/{}".format(path, fileitem)
            os.remove(filepath)


if __name__ == "__main__":
    # Defaul settings
    output_file = False
    output_mqtt = False
    frequency = 433748300
    binary = "/usr/bin/rtl_433"
    file_path = "/tmp/433sensors"
    mqtt_broker = ""
    mqtt_port = 1883
    mqtt_username = ""
    mqtt_password = ""

    # Settings from file
    if os.path.exists("sensorservice.cfg"):
        try:
            config = ConfigParser.ConfigParser()
            config.read("sensorservice.cfg")

            if config.has_section("main"):
                frequency = config.getint("main", "frequency")
                binary = config.get("main", "binary")

            if config.has_section("file"):
                file_path = config.get("file", "path")
                output_file = True

            if config.has_section("mqtt"):
                mqtt_broker = config.get("mqtt", "broker")
                mqtt_port = config.get("mqtt", "port")
                mqtt_username = config.get("mqtt", "username")
                mqtt_password = config.get("mqtt", "password")
                output_mqtt = True

            if config.has_section("alias"):
                alias_list = config.items("alias")
        except ConfigParser.NoSectionError:
            print("Missing section, ignoring settings from file.")
        except ConfigParser.NoOptionError:
            print("Missing value, ignoring settings from file.")

    # Run main loop
    try:
        rtl_433 = "{} -F json -f {}".format(binary, frequency)
        returncode = execute(rtl_433)
        print("Execution stopped ({}). Exiting...".format(returncode))
        removeOldSensors(file_path)
    except Exception as ex:
        print("Error!\n{}".format(ex.args))
        removeOldSensors(file_path)
    except KeyboardInterrupt:
        print("\nUser stopped execution. Exiting...")
        removeOldSensors(file_path)
        sys.exit()
