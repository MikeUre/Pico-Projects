# python code for raspberry pi pico for the control of ws2812 led's via pir sensors.
# February 2022
# Authour Mike Ure
# Example using PIO to drive a set of WS2812 LEDs.
# also using pico onboard rtc to control led colour as per thai colours of the day
# no battery back up so system switch on to be midday sunday to load correct time of the day
# ws2812 leds connected to pin 29 HC-SR-501 PIR's connected to pins 27, and 28, although the system will work with only one pir
# PIR's and WS2812 power 5v connected to usb 5v power supply, as both need raised 5v to operate correctly
# power consumption worked out at 0.5amp per meter (30 led strip), so a 2amp usb power supply should power up 3 metres of
# ws2812 strips comfortable.  as long as the brightness levels kept to 0.5.

import array, time
import machine
import utime
from machine import Pin
import rp2

# Configure the number of WS2812 LEDs.
NUM_LEDS = 18
PIN_NUM = 29
FALSE = 0
TRUE = 1
#date commands to use pico on board real time clock.
#although we are not interested in the time, we are interested in the day.
#switching the pico on at midday sunday will set the correct day for thia day colors.
rtc = machine.RTC()
#date in the form year, month, day, dayoftheweek, hours, minutes, seconds, milliseconds
rtc.datetime((2022, 02, 20, 6, 12, 00, 00, 0))

# set up pir sensors as input and pull down.  PIR goes to logic 1 on trigger
sensor_pir1 = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_DOWN)
sensor_pir2 = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_DOWN)
#define and clear PIR trigger
pir_triggered = FALSE
#set up timing for ws2812 loops
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()
# Create the StateMachine with the ws2812 program, outputting on pin
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(PIN_NUM))
# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)
# Display a pattern on the LEDs via an array of LED RGB values.
ar = array.array("I", [0 for _ in range(NUM_LEDS)])


#show led array on ws2812 passing the brightness to control the brightness level.
def pixels_show(brightness):
    dimmer_ar = array.array("I", [0 for _ in range(NUM_LEDS)])
    for i,c in enumerate(ar):
        r = int(((c >> 8) & 0xFF) * brightness)
        g = int(((c >> 16) & 0xFF) * brightness)
        b = int((c & 0xFF) * brightness)
        dimmer_ar[i] = (g<<16) + (r<<8) + b
    sm.put(dimmer_ar, 8)
    time.sleep_ms(10)

#set individual pixels in buffer ready to show
def pixels_set(i, color):
    ar[i] = (color[1]<<16) + (color[0]<<8) + color[2]
    
#pixel fill required to switch off all led's  make black (0,0,0)
def pixels_fill(color):
    for i in range(len(ar)):
        pixels_set(i, color)
        
#fill buffer array with todays color every second led        
def pixels_up_light(color):
        for i in range(0, len(ar), 2):
            pixels_set(i,color)
            pixels_set(i+1,BLACK)
            
#interrupt handler for the connected pir.  the pir calls interupt subroutine and flags pir_triggered to true        
def pir_handler(pin):
    utime.sleep_ms(100) # debounce for led switching
    if pin.value():
        if pin is sensor_pir2:
            print("PIR Alarm 2!")
            global pir_triggered # pir trigger flag. global due to it being inside the interupt routine
            pir_triggered = TRUE
        elif pin is sensor_pir1:
            print("PIR Alarm 1!")
            global pir_triggered
            pir_triggered = TRUE

#set pir to interupt on rising event, and call pir_handler
sensor_pir1.irq(trigger=machine.Pin.IRQ_RISING, handler=pir_handler)
sensor_pir2.irq(trigger=machine.Pin.IRQ_RISING, handler=pir_handler)

#define colors
BLACK = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
PURPLE = (128, 0, 255)
WHITE = (255, 255, 255)
PINK = (255, 0, 255)
ORANGE = (255, 50, 0)


#main loop.  
while True:

    print(rtc.datetime())  #example of two ways we can print the time, straight from rtc time,or
    dtime=(rtc.datetime()) #pull individual time sections of the tuple
    time.sleep(1)          #update the time every second for display purposes
    print ("time is {:02d}-{:02d}-{:04d} {:02d}-{:02d}".format(dtime[2],dtime[1],dtime[0],dtime[4],dtime[5]))
    #example of testing the time tuple for seconds.  possible to arranged timed functions
    if dtime[6] == 0:
        print(" it is zero")
    #determine day by testing dtime tuple 3 daysoftheweek. remembering tuple starts at 0
    if dtime[3] == 0:
        print("Monday") #print day of the week in the shell for user purposes.
        color = YELLOW #load daily color to uptime buffer
    if dtime[3] == 1:
        print ("Tuesday")
        color = PINK
    if dtime[3] == 2:
        print("Wednesday")
        color = GREEN
    if dtime[3] == 3:
        print("Thursday")
        color = ORANGE
    if dtime[3] == 4:
        print("Friday")
        color = CYAN
    if dtime[3] == 5:
        print("Saturday")
        color = PURPLE
    if dtime[3] == 6:
        print("Sunday")
        color = RED
    #check if pir is triggered, and if so call up lights and show    
    if pir_triggered == TRUE:
        pixels_up_light(color)
        #loop 50 times until at 0.5 brightness.
        for i in range (50):
            pixels_show(i/100)
            time.sleep(0.01)  #uptime speed 10ms
        #once uptime lights complete illuminate whites    
        for i in range(0, len(ar), 2):
            pixels_set(i,color)
            pixels_set(i+1,WHITE)
            pixels_show(0.5) #also at 0.5 brightness.  this also reduces current consumed.
        #reset pir trigger to clear trigger flag    
        pir_triggered = FALSE
        time.sleep(10) #illuminate time (10 seconds)
        #while loop to test trigger status so if pir still active leds are still on
        while pir_triggered == TRUE: #if true (triggered)
            pir_triggered = FALSE    #reset flag
            time.sleep(10)           #and illuminate for a further 10 seconds
        #once trigger flag has elapsed the ontime without being re-triggered carry a down light function.    
        pixels_up_light(color) #load daily colour and switch off whites
        for i in range (50, 0, -1): #de-illuminate at same speed but in reverse loop (-1)
            pixels_show(i/100)
            time.sleep(0.01)
        #reset pir triggered flag ready for next fresh trigger
        pir_triggered = FALSE
        #switch off all LED's by filling buffer black and showing.
        pixels_fill(BLACK)
        pixels_show(0.1)
