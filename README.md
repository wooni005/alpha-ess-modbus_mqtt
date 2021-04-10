# Alpha-ESS-T10 MQTT

Communication service between the Alpha ESS Storion T10 modbus and publish it via MQTT

## Protocol

The Alpha-ESS Storion T10 allows retrieving internal data via Modbus RTU. Also Modbus TCP, but that is currently in beta stadium.

This is the protocol description of the modbus: [Alpha-Modbus-Protocol_V1.17.pdf](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/img/Alpha-Modbus-Protocol_V1.17.pdf)

## Hardware

I´m using a Raspberry Pi 3B+ to retrieve the data out of the Alpha-ESS Storion T10.

In the Raspberry Pi you need a USB-Modbus adapter, which works perfectly, which I bought here via eBay in Germany: [Rs485 Converter Bus Adapter Serial USB rs-485 Interface Modbus Raspberry Pi | eBay](https://www.ebay.com/itm/RS485-Konverter-Bus-Adapter-Seriell-USB-RS-485-Schnittstelle-Modbus-Raspberry-Pi/252784174363)

### UTP cable

To connect to the Storion T10, you need an UTP cable T-568:

![](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/img/UTP-T-586B.png)

Connect to the UTP cable to the connector of the RS485 USB adapter:

* Into B goes the green-white wire (pin 3)

* Into A goes the green wire (pin 6)

![](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/img/USB-RS485-adapter.png)

Connect other side ()the RJ45 connector) to DISPATCH on the Control box of the Storion T10.

## Testing

You can use the [storion_terminal_rs485.py](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/storion_terminal_rs485.py) program to test if it's working.

## Problems

### Checks if it doesn't work

These checks were done in cooperation with Alpha-ESS support (Mr.Ming)

**1 - Modbus wires**

First I had to check that the modbus wires were connected to pin 3 (B) and 6 (A) of the modbus. (see above)

**2 - Modbus Poll tool**

Alpha-ESS support uses the [Modbus Poll tool](https://www.modbustools.com/modbus_poll.html) to check the modbus is working.
Download it [here](https://www.modbustools.com/download.html) (Windows only)

These are the settings:

![](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/img/Modbus-Poll-Tool-settings.png)

And this was my result (not working):

![](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/img/Modbus-Poll-Tool-results.png)

**3 - Check cable inside**

**Warning!** Only do this in cooperation with Alpha-ESS support (for waranty reasons) and be careful with the high voltages in the Control box!

The internal UTP cable from the DISPATCH connector needs to be connected to USART4.

![](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/img/Alpha-ESS-ControlBox-motherboard-layout.png)

**Result**

Still didn't work and the dealer (ProSolar) in Czech Republic replied that I need to buy a [Loxone system](https://www.loxone.com/cscz/question/integrace-baterioveho-systemu-storion-pro-ukladani-energie-z-fotovoltaiky/) to get it working. End of discussion... But I don´t need the Loxone system, I´m running Home Assistant and my own software for home automation. The modbus is an universal bus and should also work with other systems. Also the Loxone system is pretty expensive to test if this will work or not. I understand that as a company you don't want to support all hobbyists, but I'm doing this kind of work for more than 25 years :-). Also said that to ProSolar, but no answer to that. 

I also bought a Moxa RS422/RS485 converter, which I was used to work with from my previous work. This device is working via the LAN to communicate to RS485/modbus. Same result of course, it didn't work also. You can use the [storion_terminal_moxa.py](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/storion_terminal_moxa.py) program to use the Moxa converter.

Finally the Control box is replaced and it all worked immediately. Yippie!
Don't get me wrong, I'm a happy user of the Storion T10 and the system has a good price-performance ratio. The support could be better.

**Work-around**

There are more ways to get the Storion T10 data out of the system:

* Make use of [Alpha-ess.com web scraping](https://github.com/wooni005/alpha-ess-web_mqtt). The web information is refreshed every 5 min. But I don't know if Alpha-ESS is happy with this load on their website if you're running this 24/7, but if you've a refresh rate of 30-60 minutes I think that's not a problem.

* The beta version of Modbus TCP, which is using the LAN interface to access the internal Storion T10 data, but I didn't see it working yet.