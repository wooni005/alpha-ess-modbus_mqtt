# Alpha-ESS-T10 MQTT

Communication service between the Alpha ESS Storion T10 modbus and publish it via MQTT

## Protocol

The Alpha-ESS Storion T10 allows retrieving internal data via Modbus RTU. Also Modbus TCP, but that is currently in beta stadium.

This is the protocol description of the modbus: [Alpha-Modbus-Protocol_V1.17.pdf](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/Alpha-Modbus-Protocol_V1.17.pdf)

## Hardware

I´m using a Raspberry Pi 3B+ to retrieve the data out of the Alpha-ESS Storion T10.

In the Raspberry Pi you need a USB-Modbus adapter, which works perfectly, which I bought here via eBay in Germany: [Rs485 Converter Bus Adapter Serial USB rs-485 Interface Modbus Raspberry Pi | eBay](https://www.ebay.com/itm/RS485-Konverter-Bus-Adapter-Seriell-USB-RS-485-Schnittstelle-Modbus-Raspberry-Pi/252784174363)

### UTP cable

To connect to the Storion T10, you need an UTP cable T-568:

![](https://github.com/wooni005/alpha-ess-modbus_mqtt/blob/main/UTP-T-586B.png)



Connect to the RS485 USB adapter:

* BPin3 (Green-white) is connected to the B
  Pin6 The PIN3 of LAN cable ( Green-white colour)
  -->RS485B; PIN6 of LAN cable ( Green colour) -->RS485A

https://www.loxone.com/cscz/question/integrace-baterioveho-systemu-storion-pro-ukladani-energie-z-fotovoltaiky/
With this software there is no need to invest into a LOXONE device, which is a sort of supported and advised by Alpha-ESS dealer ProSolar: https://www.loxone.com/cscz/question/integrace-baterioveho-systemu-storion-pro-ukladani-energie-z-fotovoltaiky/