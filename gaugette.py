"""rotary_encoder.py from https://github.com/guyc/py-gaugette
This is a class for reading quadrature rotary encoders

like the PEC11 Series available from Adafruit:
  http://www.adafruit.com/products/377

This library expects the common pin C to be connected
to ground.  Pins A and B will have their pull-up resistor
pulled high.

Written by Guy Carpenter, Clearwater Software
CONTENTS OF THIS FILE ARE UNDER GNU LESSER GENERAL PUBLIC LICENSE
FIXME: need to move into seperate folder with license...
"""
import math
import threading
import time
import wiringpi


class Gpio:
    def __init__(self):
        self.gpio = wiringpi.GPIO(wiringpi.GPIO.WPI_MODE_PINS)
        self.setup = self.wiringpi_setup
        self.output = self.gpio.digitalWrite
        self.input = self.gpio.digitalRead
        self.trigger = self.gpio.wiringPiISR
        self.OUT = self.gpio.OUTPUT
        self.IN = self.gpio.INPUT
        self.HIGH = self.gpio.HIGH
        self.LOW = self.gpio.LOW
        self.PUD_UP = self.gpio.PUD_UP
        self.PUD_DOWN = self.gpio.PUD_DOWN
        self.PUD_OFF = self.gpio.PUD_OFF
        self.EDGE_FALLING = self.gpio.INT_EDGE_FALLING
        self.EDGE_RISING = self.gpio.INT_EDGE_RISING
        self.EDGE_BOTH = self.gpio.INT_EDGE_BOTH

    def wiringpi_setup(self, channel, direction, pull_up_down=None):
        self.gpio.pinMode(channel, direction)
        if pull_up_down is None:
            pull_up_down = self.gpio.PUD_OFF
        self.gpio.pullUpDnControl(channel, pull_up_down)


class Switch:

    def __init__(self, gpio, pin, pull_up=True):
        self.gpio = gpio
        self.pin = pin
        self.pull_up = pull_up
        pull_up_mode = gpio.PUD_UP if pull_up else gpio.PUD_DOWN
        self.gpio.setup(self.pin, self.gpio.IN, pull_up_mode)

    def enable_isr(self, edge, isr):
        self.gpio.trigger(self.pin, edge, isr)

    def get_state(self):
        state = self.gpio.input(self.pin)
        if self.pull_up:
            # If we are pulling up and switching
            # to ground, state will be 1 when the switch is open, and 0
            # when it is closed.  We invert the value here to a more
            # conventional representation of 0:open, 1:closed.
            return 1-state
        else:
            return state

class RotaryEncoder:

    def __init__(self, gpio, a_pin, b_pin, callback=None):
        self.gpio = gpio
        self.a_pin = a_pin
        self.b_pin = b_pin

        self.gpio.setup(self.a_pin, self.gpio.IN, self.gpio.PUD_UP)
        self.gpio.setup(self.b_pin, self.gpio.IN, self.gpio.PUD_UP)

        self.steps = 0
        self.last_delta = 0
        self.r_seq = self.rotation_sequence()

        # Callback function gets called when a rotation is detected
        # Function format should be:
        # FuncName(x) where x is 1 or -1 depending on the detected rotation
        self.callback = callback

        # steps_per_cycle and self.remainder are only used in get_cycles which
        # returns a coarse-granularity step count.  By default
        # steps_per_cycle is 4 as there are 4 steps per
        # detent on my encoder, and get_cycles() will return a signed
        # count of full detent steps.
        self.steps_per_cycle = 4
        self.remainder = 0

    def rotation_sequence(self):
        """ Returns the quadrature encoder state converted into
        a numerical sequence 0,1,2,3,0,1,2,3...
        """
        a_state = self.gpio.input(self.a_pin)
        b_state = self.gpio.input(self.b_pin)
        r_seq = (a_state ^ b_state) | b_state << 1
        return r_seq

    def update(self):
        delta = 0
        r_seq = self.rotation_sequence()
        if r_seq != self.r_seq:
            delta = (r_seq - self.r_seq) % 4
            if delta == 3:
                delta = -1
            elif delta == 2:
                delta = int(math.copysign(delta, self.last_delta))  # same direction as previous, 2 steps

            self.last_delta = delta
            self.r_seq = r_seq
        self.steps += delta
        if(self.callback is not None):
            cycles = self.get_cycles()
            if(cycles != 0):
                self.callback(cycles)

    def get_steps(self):
        steps = self.steps
        self.steps = 0
        return steps

    def get_cycles(self):
        """get_cycles returns a scaled down step count to match (for example)
        the detents on an encoder switch.  If you have 4 delta steps between
        each detent, and you want to count only full detent steps, use
        get_cycles() instead of get_delta().  It returns -1, 0 or 1.  If
        you have 2 steps per detent, set encoder.steps_per_cycle to 2
        before you call this method.
        """
        self.remainder += self.get_steps()
        cycles = self.remainder // self.steps_per_cycle
        self.remainder %= self.steps_per_cycle
        return cycles

    def start(self):
        def isr():
            self.update()
        self.gpio.trigger(self.a_pin, self.gpio.EDGE_BOTH, isr)
        self.gpio.trigger(self.b_pin, self.gpio.EDGE_BOTH, isr)

    class Worker(threading.Thread):
        def __init__(self, gpio, a_pin, b_pin):
            threading.Thread.__init__(self)
            self.lock = threading.Lock()
            self.stopping = False
            self.encoder = RotaryEncoder(gpio, a_pin, b_pin)
            self.daemon = True
            self.delta = 0
            self.delay = 0.001

        def run(self):
            while not self.stopping:
                self.encoder.update()
                time.sleep(self.delay)

        def stop(self):
            self.stopping = True

        def get_steps(self):
            return self.encoder.get_steps()
