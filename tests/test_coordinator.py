from custom_components.airos_xs2_ssh.coordinator import AiRXS2Coordinator, _number, _to_text


def test_to_text_handles_bytes_and_none():
    assert _to_text(b"signal=-65") == "signal=-65"
    assert _to_text(None) == ""
    assert _to_text("already text") == "already text"


def test_number_returns_default_for_invalid_values():
    assert _number("12.5") == 12.5
    assert _number("not a number", default=-1) == -1
    assert _number(None) is None


def test_parse_results_maps_requested_fields():
    coordinator = object.__new__(AiRXS2Coordinator)
    results = {
        "mca_status": "\n".join([
            "deviceName=NanoStation5",
            "deviceId=001122334455",
            "firmwareVersion=XS5.ar2313.v4.0.4",
            "signal=-63",
            "noise=-95",
            "ccq=991",
            "freq=5765",
            "channel=153",
            "chanbw=20",
            "txpower=27",
            "wlanTxRate=54",
            "wlanRxRate=48",
            "wlanRxBytes=1000",
            "wlanTxBytes=2000",
            "wlanRxErrors=1",
            "wlanTxErrors=2",
            "lanSpeed=100Mbps-Full",
        ]),
        "system_cfg": "resolv.host.1.name=NS5\n",
        "version": "XS5.ar2313.v4.0.4.5074.150724.1344\n",
        "uname": "Linux NS5 2.6.32 #1 Wed Jul 24 13:44:10 EEST 2015 mips GNU/Linux\n",
        "uptime": " 10:00:00 up 1 day, load average: 0.10, 0.20, 0.30\n",
        "top": "CPU:  5% usr  5% sys  0% nic 90% idle\n",
        "free": "Mem: 65536 32768 32768 0 0\n",
        "ps": "PID USER COMMAND\n1 root init\n2 root dropbear\n",
        "date": "Tue Nov 22 12:00:00 UTC 2026\n",
        "logread": "line1\nline2\n",
        "df": "Filesystem Size Used Available Use% Mounted on\n/dev/root 8.0M 4.0M 4.0M 50% /\n",
        "mount": "/dev/root on / type squashfs\nproc on /proc type proc\n",
        "ifconfig_eth0": "eth0 Link encap:Ethernet HWaddr 00:11:22:33:44:55\nRX packets:10 errors:1 dropped:2\nTX packets:20 errors:3 dropped:4\nRX bytes:100 TX bytes:200\n",
        "ifconfig_br0": "br0 Link encap:Ethernet HWaddr 00:11:22:33:44:55\ninet addr:192.168.1.20 Bcast:192.168.1.255 Mask:255.255.255.0\n",
        "proc_net_dev": "eth0: 100 10 1 2 0 0 0 0 200 20 3 4 0 0 0 0\n",
        "route": "Kernel IP routing table\nDestination Gateway Genmask Flags Metric Ref Use Iface\n0.0.0.0 192.168.1.1 0.0.0.0 UG 0 0 0 br0\n",
        "arp": "IP address HW type Flags HW address Mask Device\n192.168.1.1 0x1 0x2 aa:bb:cc:dd:ee:ff * br0\n",
        "brctl": "bridge name bridge id STP enabled interfaces\nbr0 8000.001122334455 no eth0\n",
        "iwconfig_ath0": 'ath0 IEEE 802.11na ESSID:"MySSID" Mode:Master Frequency:5.765 GHz Access Point: 00:11:22:33:44:66 Bit Rate:54 Mb/s Tx-Power=27 dBm\n',
        "athstats": "tx failed due to too many retries: 7\nother stat\n",
        "wstalist": "00:AA:BB:CC:DD:EE\n",
        "iwlist_scan": 'Cell 01 - Address: 00:01:02:03:04:05\nESSID:"Net1"\nCell 02 - Address: 00:01:02:03:04:06\nESSID:"Net2"\n',
    }

    data = coordinator._parse_results(results)

    assert data["device_status"] == "ok"
    assert data["device_name"] == "NS5"
    assert data["device_model"] == "NanoStation5"
    assert data["firmware_version"].startswith("XS5")
    assert data["lan_ip"] == "192.168.1.20"
    assert data["lan_subnet"] == "255.255.255.0"
    assert data["eth_mac"] == "00:11:22:33:44:55"
    assert data["signal_strength"] == -63
    assert data["noise_floor"] == -95
    assert data["snr"] == 32
    assert data["ccq"] == 99.1
    assert data["wireless_retries"] == 7
    assert data["connected_stations"] == 1
    assert data["available_networks"] == 2
