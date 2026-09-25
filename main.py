# example code for ansemjo/luftctl
# 1. flash micropython from https://micropython.org/download/esp32c3-usb/
# 2. upload with `ampy -p /dev/ttyACM0 put main.py`

from machine import Pin as pin, PWM as pwm
from time import sleep, ticks_ms as ticks, ticks_diff as diff

# 12V now comes straight from USB-C PD (always on) - no boost enable anymore.
# GPIO3 is free and broken out on the J6 header (with GPIO2 and GPIO8).

# fan pwms
pwmfreq = 25000
f1 = pwm(pin(4, pin.OUT, pin.PULL_DOWN), pwmfreq)
f2 = pwm(pin(6, pin.OUT, pin.PULL_DOWN), pwmfreq)
f1.duty(0)
f2.duty(0)

# button
btn = pin(9, pin.IN, pin.PULL_UP)

# usr led
led = pwm(pin(10, pin.OUT, pin.PULL_DOWN), 10000)
led.duty(0)
def blink():
  led.duty(1023)
  sleep(0.06)
  led.duty(0)
  sleep(0.04)


# states to cycle through (fans stop at 0% pwm; 12V is always present)
states = [
  #  label  fan1   fan2  led
  (  "off",  0.00,  0.00,    0 ),
  (  "20%",  0.20,  0.20,  100 ),
  (  "45%",  0.45,  0.45,  300 ),
  (  "65%",  0.65,  0.65,  400 ),
  ( "100%",  1.00,  1.00,  800 ),
]

# button callback for state change
i = 0
now = ticks()
def nextstate(_):
  global i, now
  if diff(ticks(), now) < 300:
    print("debounce")
    return
  now = ticks()
  i = (i+1) % len(states)
  txt, d1, d2, l = states[i]
  print(f"[{i+1}/{len(states)}] {txt} {l}")
  f1.duty(int(d1*1023))
  f2.duty(int(d2*1023))
  blink()
  led.duty(l)

# register callback on falling edge / button press
btn.irq(trigger=pin.IRQ_FALLING, handler=nextstate)
