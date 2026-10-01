#!/usr/bin/env python3
"""
Dynamic Active Drone Discovery for Swarm2
Scans configured Crazyflie URIs (up to 10 drones on the same radio channel)
and generates an active YAML configuration enabling only the drones currently powered on.

This prevents Crazyswarm2 from timing out and disconnecting when flying with
any subset of your swarm (1 to 10 drones).
"""

import sys
import os
import yaml

def main():
    config_in = sys.argv[1] if len(sys.argv) > 1 else "/swarm2/config/crazyflies_real.yaml"
    config_out = sys.argv[2] if len(sys.argv) > 2 else "/swarm2/config/crazyflies_active.yaml"

    if not os.path.exists(config_in):
        print(f"[ERROR] Source config not found: {config_in}")
        sys.exit(1)

    with open(config_in, 'r') as f:
        config = yaml.safe_load(f)

    try:
        import cflib.crtp
        cflib.crtp.init_drivers()
    except Exception as e:
        print(f"[WARN] Failed to initialize Crazyradio driver: {e}")
        # Copy input to output as fallback
        with open(config_out, 'w') as f:
            yaml.dump(config, f, sort_keys=False)
        sys.exit(0)

    print("==========================================================================")
    print("           Swarm2: Auto-Discovering Active Drones on Radio                ")
    print("==========================================================================")

    robots = config.get('robots', {})
    active_count = 0
    detected_robots = {}

    cr = None
    try:
        from cflib.drivers.crazyradio import Crazyradio
        from cflib.crtp.radiodriver import RadioDriver
        import time
        cr = Crazyradio(devid=0)
        cr.set_arc(3)
    except Exception as e:
        print(f"[WARN] Could not directly access Crazyradio: {e}")
        # Copy input to output as fallback
        with open(config_out, 'w') as f:
            yaml.dump(config, f, sort_keys=False)
        sys.exit(0)

    try:
        for cf_name, cf_data in robots.items():
            uri = cf_data.get('uri', '')
            is_online = False

            if uri:
                try:
                    devid, channel, datarate, address, _ = RadioDriver.parse_uri(uri)
                    cr.set_channel(channel)
                    cr.set_data_rate(datarate)
                    cr.set_address(address)

                    # Send targeted ping packets (CRTP null packet 0xFF)
                    for _ in range(3):
                        ack = cr.send_packet((0xff,))
                        if ack and ack.ack:
                            is_online = True
                            break
                        time.sleep(0.003)
                except Exception:
                    is_online = False

            pos = cf_data.get('initial_position', [0, 0, 0])
            if is_online:
                cf_data['enabled'] = True
                active_count += 1
                print(f"  \033[92m✔ {cf_name:<5} ONLINE\033[0m  URI: {uri:<28} Spawn: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")
                detected_robots[cf_name] = cf_data
            else:
                cf_data['enabled'] = False
                print(f"  \033[90m✖ {cf_name:<5} OFFLINE\033[0m URI: {uri}")

        # Fallback check on broadcast address 0xE7E7E7E7E7 if 0 found
        if active_count == 0:
            print("\n[INFO] No drones found matching individual radio addresses.")
            print("Checking default factory address 0xE7E7E7E7E7 on channel 80 and 2...")
            for ch in [80, 2]:
                try:
                    cr.set_channel(ch)
                    cr.set_data_rate(Crazyradio.DR_2MPS)
                    cr.set_address((0xE7, 0xE7, 0xE7, 0xE7, 0xE7))
                    ack = cr.send_packet((0xff,))
                    if ack and ack.ack:
                        found_uri = f"radio://0/{ch}/2M/E7E7E7E7E7"
                        print(f"  \033[92m✔ Found Crazyflie on factory address: {found_uri}\033[0m")
                        if 'cf1' in robots:
                            robots['cf1']['enabled'] = True
                            robots['cf1']['uri'] = found_uri
                            active_count = 1
                        break
                except Exception:
                    pass

    finally:
        if cr:
            try:
                cr.close()
            except Exception:
                pass
            import time
            time.sleep(0.2)

    if active_count > 0:
        print(f"\n[READY] {active_count} active drone(s) detected and ready for continuous flight.")
    else:
        print("\n[WARN] 0 drones responded. Leaving cf1 enabled as default fallback.")
        if 'cf1' in robots:
            robots['cf1']['enabled'] = True

    # Write the active configuration
    os.makedirs(os.path.dirname(config_out), exist_ok=True)
    with open(config_out, 'w') as f:
        yaml.dump(config, f, sort_keys=False)
    try:
        os.chmod(config_out, 0o666)
    except Exception:
        pass

    print(f"[CONFIG] Active swarm topology saved to: {config_out}")
    print("==========================================================================")

if __name__ == '__main__':
    main()
