# SPDX-FileCopyrightText: 2018 Tony DiCola for Adafruit Industries
# SPDX-License-Identifier: MIT

# Simple example to send a message and then wait indefinitely for messages
# to be received.  This uses the default RadioHead compatible GFSK_Rb250_Fd250
# modulation and packet format for the radio.
import board
import busio
import digitalio
import time
import adafruit_rfm69
from os import getenv

MY_NAME = getenv("NODE_NAME")
MY_ID = int(getenv("NODE_ID"))
MY_STATE = "OFF"
# Define radio parameters.
RADIO_FREQ_MHZ = 433.0  # Frequency of the radio in Mhz. Must match your
# module! Can be a value like 915.0, 433.0, etc.

# Define pins connected to the chip, use these if wiring up the breakout according to the guide:
CS = digitalio.DigitalInOut(board.GP17)
RESET = digitalio.DigitalInOut(board.GP21)
RELAY = digitalio.DigitalInOut(board.GP22)
RELAY.direction = digitalio.Direction.OUTPUT
RELAY.value = True
GW_UP = True
PING_TIME = time.monotonic()
PRES_TIME = time.monotonic()


# Define the onboard LED
LED = digitalio.DigitalInOut(board.LED)
LED.direction = digitalio.Direction.OUTPUT


# Initialize SPI bus.
spi = busio.SPI(board.GP18, MOSI=board.GP19, MISO=board.GP16)

# Initialze RFM radio
rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, RADIO_FREQ_MHZ)
rfm69.node = MY_ID
rfm69.destination = 0  # gw is 0 

# Optionally set an encryption key (16 byte AES key). MUST match both
# on the transmitter and receiver (or be set to None to disable/the default).
rfm69.encryption_key = (
    b"\x01\x02\x03\x04\x05\x06\x07\x08\x01\x02\x03\x04\x05\x06\x07\x08"
)

# Print out some chip state:
print("Temperature: {0}C".format(rfm69.temperature))
print("Frequency: {0}mhz".format(rfm69.frequency_mhz))
print("Bit rate: {0}kbit/s".format(rfm69.bitrate / 1000))
print("Frequency deviation: {0}hz".format(rfm69.frequency_deviation))


# send an initial presentation
presentation = str(MY_ID)+";"+MY_NAME+";0;switch;OFF"
state = str(MY_ID)+";"+MY_NAME+";1;switch;"+MY_STATE
ping = str(MY_ID)+";"+MY_NAME+";2;switch;"+MY_STATE

rfm69.send(bytes(presentation, "ascii"))
print("Sent presentation message!")

rfm69.send(bytes(state, "ascii"))
print("Waiting for packets...")
while True:
    now = time.monotonic()
    if now >= PING_TIME+120:
        print("lost gateway connection! turning off")
        RELAY.value = True
        MY_STATE = "OFF"
        GW_UP = False
    if now >= PRES_TIME+20:
        rfm69.send(bytes(presentation, "ascii"))
        rfm69.send(bytes(state, "ascii"))
        PRES_TIME = time.monotonic()
    packet = rfm69.receive()
    if packet is None:
        # Packet has not been received
        LED.value = False
        print("Received nothing! Listening again...")
    else:
        # Received a packet!
        LED.value = True
        if packet == "ON":
            RELAY.value = False
            print("Sending ON")
            MY_STATE = "ON"
            rfm69.send_with_ack(str(MY_ID)+";"+MY_NAME+";1;switch;"+MY_STATE)
        elif packet == "OFF":
            RELAY.value = True
            MY_STATE = "OFF"
            print("Sending OFF")
            rfm69.send_with_ack(str(MY_ID)+";"+MY_NAME+";1;switch;"+MY_STATE)
        elif packet == "ping":
            print("got a ping from GW")
            rfm69.send(str(MY_ID)+";"+MY_NAME+";2;pong;OFF")
            PING_TIME = now
            if not GW_UP:
                print("resending presentation message!")
                rfm69.send(bytes(presentation, "ascii"))
                rfm69.send(bytes(state, "ascii"))
                GW_UP = True
        # elif packet == "present":
        #     print("Got presentation request!")
        #     rfm69.send(bytes(presentation, "ascii"))
        #     rfm69.send(bytes(state, "ascii"))
        packet_text = str(packet, "ascii")
        print("Received (ASCII): {0}".format(packet_text))
