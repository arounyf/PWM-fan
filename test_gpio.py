#!/usr/bin/env python3
import gpiod, time
chip = gpiod.Chip('/dev/gpiochip0')
line = chip.get_line(24)
line.request(consumer='fan-test', type=gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
print('GPIO 24 HIGH — fan should be at max speed')
time.sleep(5)
line.set_value(0)
line.release()
print('GPIO 24 LOW — released')
