#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from adxl345 import ADXL345
import time
import pigpio
import datetime
import requests

class DHT11(object):

    def __init__(self, pi, gpio):
        self.pi = pi
        self.gpio = gpio
        self.high_tick = 0
        self.bit = 40
        self.temperature = 0
        self.humidity = 0
        self.either_edge_cb = None
        self.setup()

    def setup(self):
        self.pi.set_pull_up_down(self.gpio, pigpio.PUD_OFF)
        self.pi.set_watchdog(self.gpio, 0)
        self.register_callbacks()

    def register_callbacks(self):
        self.either_edge_cb = self.pi.callback(
            self.gpio,
            pigpio.EITHER_EDGE,
            self.either_edge_callback
        )

    def either_edge_callback(self, gpio, level, tick):
        level_handlers = {
            pigpio.FALLING_EDGE: self._edge_FALL,
            pigpio.RISING_EDGE: self._edge_RISE,
            pigpio.EITHER_EDGE: self._edge_EITHER
        }
        handler = level_handlers[level]
        diff = pigpio.tickDiff(self.high_tick, tick)
        handler(tick, diff)

    def _edge_RISE(self, tick, diff):
        val = 0
        if diff >= 50:
            val = 1
        if diff >= 200:
            self.checksum = 256

        if self.bit >= 40:
            self.bit = 40
        elif self.bit >= 32:
            self.checksum = (self.checksum << 1) + val
            if self.bit == 39:

                self.pi.set_watchdog(self.gpio, 0)
                total = self.humidity + self.temperature

                if not (total & 255) == self.checksum:
                    raise
        elif 16 <= self.bit < 24:
            self.temperature = (self.temperature << 1) + val
        elif 0 <= self.bit < 8:
            self.humidity = (self.humidity << 1) + val
        else:
            pass
        self.bit += 1

    def _edge_FALL(self, tick, diff):
        self.high_tick = tick
        if diff <= 250000:
            return
        self.bit = -2
        self.checksum = 0
        self.temperature = 0
        self.humidity = 0

    def _edge_EITHER(self, tick, diff):
        self.pi.set_watchdog(self.gpio, 0)

    def read(self):
        self.pi.write(self.gpio, pigpio.LOW)
        time.sleep(0.017)
        self.pi.set_mode(self.gpio, pigpio.INPUT)
        self.pi.set_watchdog(self.gpio, 200)
        time.sleep(0.2)

    def close(self):
        self.pi.set_watchdog(self.gpio, 0)
        if self.either_edge_cb:
            self.either_edge_cb.cancel()
            self.either_edge_cb = None

    def __iter__(self):
        return self

    def next(self):
        self.read()
        response =  {
            'humidity': self.humidity,
            'temperature': self.temperature
        }
        return response


if __name__ == '__main__':
    pi = pigpio.pi()
    pi2 = pigpio.pi()
    sensor = DHT11(pi, 23)
    sensor2 = DHT11(pi2, 24)
    adxl345 = ADXL345()
    axes = adxl345.getAxes(True)
    for a in sensor:
        for b in sensor2:
            for adxl345 in axes:
                print("External temperature: {}".format(a['temperature']))
                print("External humidity: {}".format(a['humidity']))
                time.sleep(1)
                print("Internal temperature: {}".format(b['temperature']))
                print("Internal humidity: {}".format(b['humidity']))
                time.sleep(1)
                print(" x = {:.3f}G".format(axes['x']))
                print(" y = {:.3f}G".format(axes['y']))
                print(" z = {:.3f}G".format(axes['z']))
                payload = {'id_prontuario': '1', 'key': '202cb962ac59075b964b07152d234b70', 'temperatura': '{}'.format(b['temperature']), 'umidade': '{}'.format(b['humidity']), 'temperatura_externa': '{}'.format(a['temperature']), 'umidade_externa': '{}'.format(a['humidity']), 'acelerometro_x': '{}'.format(axes['x']), 'acelerometro_y': '{}'.format(axes['y']), 'acelerometro_z': '{}'.format(axes['z'])}
                r = requests.post('http://192.168.1.4/medical/app/api/sensor/set', data=payload)
                print(r.text)
                break
            break
        break
