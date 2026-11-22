# Ubiquiti AirOS (SSH)

[![Downloads](https://img.shields.io/github/downloads/jonny5509/ha-airos-ssh/total?label=downloads)](https://github.com/jonny5509/ha-airos-ssh/releases)

**Version:** 2.3.2  
**Transport:** SSH  
**Repository:** https://github.com/jonny5509/ha-airos-ssh

A Home Assistant custom integration for monitoring legacy Ubiquiti airOS radios. This edition connects over SSH and runs read-only status commands, with a button to reboot the radio.

## Features

- Home Assistant UI setup
- SSH-based polling for legacy Ubiquiti NanoStation5 airOS devices
- Sensors for system, Ethernet, and wireless information (as exposed by device commands)
- Reboot button

## Sensors

### System
- Device status (`mca-status`)
- Device name (`cat /tmp/system.cfg`)
- Device model (`mca-status`)
- Device ID (`mca-status`)
- Firmware version (`cat /etc/version`)
- Kernel version (`uname -a`)
- Uptime (`uptime`)
- CPU usage (`top`)
- System load (`uptime`)
- Total memory (`free`)
- Free memory (`free`)
- Running processes (`ps`)
- System date/time (`date`)
- System logs (`logread`)
- Storage usage (`df -h`)
- Filesystem mounts (`mount`)

### Ethernet
- Ethernet interface (`ifconfig eth0`)
- Ethernet MAC address (`ifconfig eth0`)
- LAN IP address (`ifconfig br0`)
- Subnet mask (`ifconfig br0`)
- Ethernet link status (`mca-status`)
- Ethernet speed (`mca-status`)
- Ethernet duplex (`mca-status`)
- RX bytes (`cat /proc/net/dev`)
- TX bytes (`cat /proc/net/dev`)
- RX packets (`ifconfig eth0`)
- TX packets (`ifconfig eth0`)
- RX errors (`ifconfig eth0`)
- TX errors (`ifconfig eth0`)
- RX dropped packets (`ifconfig eth0`)
- TX dropped packets (`ifconfig eth0`)
- Routing table (`route -n`)
- ARP table (`arp -n`)
- Bridge information (`brctl show`)

### Wireless
- Wireless interface (`iwconfig ath0`)
- Wireless MAC address (`iwconfig ath0`)
- Wireless mode (`iwconfig ath0`)
- SSID (`iwconfig ath0`)
- Frequency (`iwconfig ath0`)
- Channel (`iwconfig ath0`)
- Channel width (`iwconfig ath0`)
- TX power (`iwconfig ath0`)
- Signal strength (dBm) (`mca-status`)
- Noise floor (dBm) (`mca-status`)
- SNR (dB) (calculated from signal and noise)
- CCQ (%) (`mca-status`)
- TX data rate (`iwconfig ath0`)
- RX data rate (`iwconfig ath0`)
- Wireless RX bytes (`mca-status`)
- Wireless TX bytes (`mca-status`)
- Wireless RX errors (`mca-status`)
- Wireless TX errors (`mca-status`)
- Wireless retries (`athstats`)
- Connected stations (`wstalist`)
- Radio statistics (`athstats`)
- Available networks (`iwlist ath0 scan`)

## Compatibility

Officially supported hardware is limited to the original Ubiquiti NanoStation 2 (NS2/XS2) and NanoStation 5 (NS5/XS5), running legacy airOS 3.x–4.x.

NanoStation Loco, Bullet, PicoStation, PowerStation, and other product families are **not officially supported**. Device identification or parsing of similar status fields does not establish compatibility.

This edition uses `mca-status` and additional legacy BusyBox/procfs commands where available. Automated tests cover NS2/NS5 identity and representative airOS 3.x/4.x version strings; optional command availability varies by firmware. Physical-radio testing across every firmware build has not been completed.

May require legacy SSH key-exchange, cipher, or host-key algorithms for older firmware.

## Domain and upgrade note

This SSH edition uses the unique Home Assistant domain `airos_xs2_ssh`, so it can coexist with the HTTP edition (`airos_xs2_http`) and the combined AirOS integration (`airos_xs2`). If upgrading from the former shared `airos_xs2` domain, remove the old integration entry and old `custom_components/airos_xs2` folder before installing this edition. Home Assistant does not automatically migrate config entries across domains; add this SSH integration again after installation.

## Installation

### HACS

1. Open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add `https://github.com/jonny5509/ha-airos-ssh` and select **Integration**.
3. Install **Ubiquiti AirOS (SSH)** and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and select **Ubiquiti AirOS (SSH)**.

### Manual

1. Download or clone this repository.
2. Copy `custom_components/airos_xs2_ssh` into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.
4. Add **Ubiquiti AirOS (SSH)** from **Settings → Devices & services → Add integration**.
5. Enter the radio's IP address and SSH credentials.

The integration requires the `asyncssh` dependency declared in its manifest.

## Troubleshooting

- Confirm SSH access to the radio from the Home Assistant host.
- Check the configured IP address and credentials.
- Some older firmware does not support every diagnostic command or counter.
- Remove passwords, private keys, and other secrets before sharing logs.

## Security

The current SSH connection configuration disables known-host verification (`known_hosts=None`), so the radio's host key is not authenticated. Legacy SSH algorithms may also provide weaker security. Use only on a trusted LAN or VPN, and do not expose the radio's management interface to the public internet.

## Related project

Prefer polling through the radio's web interface instead? See the [Ubiquiti AirOS (HTTP) integration](https://github.com/jonny5509/ha-airos-http).
