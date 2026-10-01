#!/usr/bin/env python3
"""
Crazyradio Scanner: Scans the airwaves to discover active real Crazyflies.
Scans standard addresses (0xE7E7E7E7E7 and swarm addresses 0xE7E7E7E701-0xE7E7E7E70A).
"""

import sys

def main():
    print("==================================================")
    print("      Bitcraze Crazyradio Frequency Scanner       ")
    print("==================================================")

    try:
        import cflib.crtp
    except ImportError:
        print("[ERROR] cflib is not installed or not in PYTHONPATH.")
        sys.exit(1)

    print("Initializing CRTP communication driver...")
    try:
        cflib.crtp.init_drivers()
    except Exception as e:
        print(f"[ERROR] Failed to initialize drivers: {e}")
        print("Ensure the Crazyradio PA USB dongle is plugged into your PC.")
        sys.exit(1)

    from cflib.drivers.crazyradio import Crazyradio
    import struct
    import binascii
    import time

    cr = None
    try:
        cr = Crazyradio(devid=0)
        cr.set_arc(2)
    except Exception as e:
        print(f"[ERROR] Failed to open Crazyradio: {e}")
        print("Ensure Crazyradio PA is plugged in.")
        sys.exit(1)

    # Standard channels: Channel 80 (configured swarm channel), Channel 2 (factory default)
    channels_to_scan = [80, 2]
    # Datarates to scan: 2M (swarm default), 1M, 250K
    datarates = [
        (Crazyradio.DR_2MPS, '2M'),
        (Crazyradio.DR_1MPS, '1M'),
        (Crazyradio.DR_250KPS, '250K')
    ]

    # List of addresses to scan: default + swarm IDs 1 to 10
    addresses_to_scan = [0xE7E7E7E7E7] + [0xE7E7E7E700 + i for i in range(1, 11)]
    found_interfaces = []
    seen_uris = set()

    print("Scanning swarm addresses on channel 80 and channel 2...")
    try:
        for addr_int in addresses_to_scan:
            addr_hex = f"{addr_int:010X}"
            addr_bytes = struct.unpack('<BBBBB', binascii.unhexlify(addr_hex))
            cr.set_address(addr_bytes)

            for channel in channels_to_scan:
                cr.set_channel(channel)
                for dr_val, dr_str in datarates:
                    cr.set_data_rate(dr_val)
                    ack = cr.send_packet((0xff,))
                    if ack and ack.ack:
                        uri = f"radio://0/{channel}/{dr_str}/{addr_hex}"
                        if uri not in seen_uris:
                            seen_uris.add(uri)
                            found_interfaces.append((uri, f"Crazyflie_{addr_hex[-2:]}"))
                        break # Found on this channel
    finally:
        if cr:
            cr.close()

    if not found_interfaces:
        print("\n[RESULT] No Crazyflies found.")
        print("Troubleshooting tips:")
        print("  1. Ensure Crazyradio PA is securely plugged into USB.")
        print("  2. Verify that your Crazyflie is powered ON and LEDs are flashing.")
        print("  3. Check udev permissions: did you run `./setup_usb_udev.sh`?")
        print("  4. Check battery on the Crazyflie.")
    else:
        print(f"\n[SUCCESS] Found {len(found_interfaces)} active Crazyflie(s) online:")
        for uri, name in found_interfaces:
            print(f"  • URI: \033[92m{uri}\033[0m")
        print("\nConfigure these URIs in `swarm2/config/crazyflies_real.yaml` under `robots:`.")

if __name__ == "__main__":
    main()
