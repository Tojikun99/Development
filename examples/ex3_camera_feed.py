#!/usr/bin/env python3
"""
Example 3: Camera Feed Viewer with Flight
Connects via cflib to execute a hover maneuver while simultaneously
streaming and displaying the live AI-Deck UDP camera feed via OpenCV.

Requirements:
  - Run demo with: ./run_demo.sh --camera   (MuJoCo only, NOT Gazebo)
  - launch_ros2_sitl.sh is NOT required (uses cflib directly)
"""

import socket
import struct
import sys
import threading
import time

import cv2
import numpy as np
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.high_level_commander import HighLevelCommander

UDP_IP   = "127.0.0.1"
UDP_PORT = 5200
URI      = 'udp://127.0.0.1:19850'

# Shared flag so the flight thread knows when to land
stop_event = threading.Event()


def flight_thread():
    """Background thread to handle cflib flight operations."""
    cflib.crtp.init_drivers()
    print(f"[flight] Connecting to {URI}...")
    try:
        with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
            commander = HighLevelCommander(scf.cf)

            print("[flight] Taking off to 0.5m...")
            commander.takeoff(0.5, duration_s=3.0)
            time.sleep(4.0)

            print("[flight] Hovering — press 'q' or Esc in the camera window to land.")
            stop_event.wait()

            print("[flight] Landing...")
            commander.land(0.05, duration_s=3.0)
            time.sleep(4.0)
            print("[flight] Done.")
    except Exception as e:
        print(f"[flight] Error: {e}")
        stop_event.set()


def main():
    # Start the flight thread in the background
    t = threading.Thread(target=flight_thread, daemon=True)
    t.start()

    # ── Camera viewer (main thread) ───────────────────────────────────────
    print(f"[camera] Listening on udp://{UDP_IP}:{UDP_PORT}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"[camera] Failed to bind to port {UDP_PORT}: {e}")
        stop_event.set()
        sys.exit(1)

    sock.settimeout(1.0)

    chunks = {}
    expected_total = 0
    current_width  = 324
    current_height = 244

    cv2.namedWindow('CrazySim AI-deck Camera', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('CrazySim AI-deck Camera', 648, 488)
    print("[camera] Waiting for frames... (Press 'q' or Esc to land and quit)")

    while not stop_event.is_set():
        try:
            pkt, _ = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            break

        if len(pkt) < 8:
            continue

        seq, total, width, height = struct.unpack('<HHHH', pkt[:8])
        chunk_data = pkt[8:]

        if seq == 0:
            chunks = {}
            expected_total = total
            current_width  = width
            current_height = height

        chunks[seq] = chunk_data

        if len(chunks) == expected_total and expected_total > 0:
            pixels = b''.join(chunks[i] for i in range(expected_total))
            chunks = {}

            if len(pixels) == current_width * current_height:
                img = np.frombuffer(pixels, dtype=np.uint8).reshape(
                    (current_height, current_width))
                cv2.imshow('CrazySim AI-deck Camera', img)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):  # q or Esc
            break

    print("[camera] Closing — signalling drone to land...")
    stop_event.set()
    sock.close()
    cv2.destroyAllWindows()

    t.join(timeout=15.0)
    print("Flight complete.")


if __name__ == "__main__":
    main()

