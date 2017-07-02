# 433SS - 433 MHz Sensor Service

Receives 433 MHz sensor broadcasts using a rtlsdr receiver and the [rtl_433](https://github.com/merbanan/rtl_433) application. The service parses received broadcasts and outputs the sensor information to desired output (like: file, MQTT). I.e. a (simple) wrapper for rtl_433.

It supports multiple outputs at once, but is primarily made to publish sensor updates via MQTT.

