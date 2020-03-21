# Work Pi
One-button time-management with the Raspberry Pi.

Ever get frustrated by JIRA's time logging? Replace all that time spent navigating crummy UI and doing mental math with a Work Pi on your desk!

![workpi](https://github.com/PaulMcInnis/WorkPi/blob/master/workpi.jpg)

It's very easy to use, with only one button

* rotate to scroll through currently-assigned tasks
* click to start time logging
* click to stop time logging

----

### Pre-requisites

The WorkPi runs a simple  `pygame`script which interfaces with a rotary encoder + button. Wiring up and installing the button requires drilling a single hole and soldering a few wires.

#### Hardware

This device can be built with only a few Adafruit components. To replicate this you'll need the below:

##### Materials

* [Raspi TFT Plus (2.8") kit](https://www.adafruit.com/product/2298)
* [Raspi TFT enclosure](https://www.adafruit.com/product/2253)
* [Raspi TFT Faceplate](https://www.adafruit.com/product/2807)
* [Raspberry Pi (2/3/4)](https://www.adafruit.com/product/3055)
* [Rotary encoder](https://www.adafruit.com/product/377) (with integrated button)
* [Big metal knob](https://www.adafruit.com/product/2056)

*NOTE: if you are Canadian, like me, I recommend Elmwood Electronics when purchasing Adafruit products*

##### Wiring it up

The following connections will be made between the rotary encoder and the RasPi-TFT's GPIO header (**not** the raspberry pi's own physical GPIO pins!).

I recommend soldering these to the PCB so as not to ruin the expansion GPIO header on the RasPiTFT.

![wiring](https://github.com/PaulMcInnis/WorkPi/blob/master/wiring.png)

##### Assembly

** TODO measurements + pictures**

1. Just drill a single hole in the RaspiTFT enclosure on the side which has the microSD slot. Once inserted the encoder will fit nicely above the microUSB connector and below the RaspiTFT PCB.

2. insert the Raspberry pi into the enclosure

3. screw in the rotary encoder

4. insert the raspiTFT and faceplate

   Done!

#### Software

There isn't a whole lot going on beyond just a simple startup script:

1. Install the RaspiTFT drivers from the link [here](https://learn.adafruit.com/adafruit-pitft-28-inch-resistive-touchscreen-display-raspberry-pi/easy-install-2).
2. Clone *this* repo into your `/home/pi ` directory (as `/home/pi/WorkPi`)
3. Make it run on startup by adding `sudo python3 /home/pi/WorkPi/run.py` to  new file`/etc/init.d/workpiscript`
4.  `cd` to `/home/pi/WorkPi` and run `sudo python3 install -r requirements`



