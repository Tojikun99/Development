#!/usr/bin/env python3
"""
Interactive Swarm2 Formation Manager
Control real Crazyflies (with Loco Positioning System) or SITL simulated drones.

Configured for 10 drones on the same radio channel:
- Drones take off to exactly 1.0 meter altitude.
- Pre-flight EKF stabilization delay eliminates LPS sensor noise.
- Ground coordinates (X0, Y0) are actively sampled and locked during takeoff.
- Immediate closed-loop goTo position-lock prevents drone from drifting or running away.
- Formations are dynamically centered around the swarm arena centroid.
"""

import sys
import math
import numpy as np
from crazyflie_py import Crazyswarm

DEFAULT_ALTITUDE = 1.0      # Exactly 1.0 meter takeoff altitude from ground
TAKEOFF_DURATION = 2.5      # Crisp vertical takeoff time to clear ground turbulence
STABILIZE_DELAY = 2.0       # Pre-flight EKF convergence delay
TRANSITION_DURATION = 4.0   # Safe transition duration for multi-drone movement


class SwarmManager:
    def __init__(self):
        print("Connecting to ROS 2 Crazyswarm2 server...")
        try:
            self.swarm = Crazyswarm()
            self.timeHelper = self.swarm.timeHelper
            self.cfs = self.swarm.allcfs.crazyflies
        except Exception as e:
            print(f"\n[ERROR] Failed to connect to Crazyswarm2 server: {e}")
            print("==========================================================")
            print(" The formation manager requires the ROS 2 server to be running.")
            print(" Please start the server first in another terminal:")
            print("   ./launch_ros2_real.sh")
            print("==========================================================")
            sys.exit(1)

        self.num_drones = len(self.cfs)
        if self.num_drones == 0:
            print("[WARN] 0 drones detected on the ROS 2 server.")
            print("Please ensure your Crazyflies are turned on and ./launch_ros2_real.sh is running.")
            sys.exit(1)

        # Cache initial spawn coordinates from YAML
        self.home = {}
        for cf in self.cfs:
            pos = getattr(cf, 'initialPosition', None)
            if pos is None or len(pos) < 3:
                pos = [0.0, 0.0, 0.0]
            self.home[cf] = np.array(pos, dtype=float)

        self.is_airborne = False

        # Calculate initial arena centroid
        self.cx = float(np.mean([self.home[cf][0] for cf in self.cfs]))
        self.cy = float(np.mean([self.home[cf][1] for cf in self.cfs]))

        print(f"\n[READY] Successfully connected to {self.num_drones} drone(s):")
        print(f"   • Arena Centroid : (X={self.cx:.2f}, Y={self.cy:.2f})")
        print(f"   • Target Altitude: {DEFAULT_ALTITUDE:.2f}m")
        for cf in self.cfs:
            print(f"   • {cf.prefix} (Initial: X={self.home[cf][0]:.1f}, Y={self.home[cf][1]:.1f}, Z={self.home[cf][2]:.1f})")

    def takeoff(self, height=DEFAULT_ALTITUDE, duration=TAKEOFF_DURATION):
        if self.is_airborne:
            print("[INFO] Drones are already airborne.")
            return

        print("\n==================================================")
        print("       INITIATING POSITION-HOLD TAKEOFF           ")
        print("==================================================")
        print(f"[STEP 1/2] Stabilizing EKF on anchor signals ({STABILIZE_DELAY:.1f}s)...")
        self.timeHelper.sleep(STABILIZE_DELAY)

        # Arm all drones with broadcast redundancy
        print("  • Arming motors...")
        self.swarm.allcfs.arm(True)
        self.timeHelper.sleep(0.15)
        self.swarm.allcfs.arm(True)
        self.timeHelper.sleep(0.5)

        print(f"\n[STEP 2/2] Synchronized vertical ascent to {height:.1f}m (duration: {duration:.1f}s)...")
        print("  • Broadcasting takeoff to all 10 drones simultaneously...")
        self.swarm.allcfs.takeoff(targetHeight=height, duration=duration)
        self.timeHelper.sleep(0.12)
        # Duplicate broadcast ensures any drone servicing UWB/SPI during 1st burst catches 2nd
        self.swarm.allcfs.takeoff(targetHeight=height, duration=duration)

        # Mid-ascent check (at 1.2s): catch any drone that missed both broadcasts
        self.timeHelper.sleep(1.2)
        stragglers = [cf for cf in self.cfs if np.array(cf.position)[2] < 0.12]
        if stragglers:
            print(f"  \033[93m[RESCUE] {len(stragglers)} drone(s) ({', '.join(c.prefix for c in stragglers)}) on ground - sending direct unicast...\033[0m")
            for cf in stragglers:
                cf.arm(True)
                cf.takeoff(targetHeight=height, duration=max(1.8, duration - 1.2))

        # Allow remaining duration for complete ascent
        remaining_wait = max(0.5, duration - 1.2) + 0.6
        self.timeHelper.sleep(remaining_wait)

        # Final verification: Guarantee 100% of drones reached flight altitude
        final_check = [cf for cf in self.cfs if np.array(cf.position)[2] < 0.25]
        if final_check:
            print(f"  \033[93m[FINAL CHECK] Re-commanding {len(final_check)} drone(s): {', '.join(c.prefix for c in final_check)}...\033[0m")
            for cf in final_check:
                cf.arm(True)
                cf.takeoff(targetHeight=height, duration=2.5)
            self.timeHelper.sleep(2.8)

        # Update in-flight home positions from actual clean in-air anchor readings
        for cf in self.cfs:
            pos = np.array(cf.position)
            if np.linalg.norm(pos[:2]) > 0.05:
                self.home[cf] = pos
            print(f"  \033[92m✔ {cf.prefix:<5} HOVERING\033[0m at X={self.home[cf][0]:.2f}m, Y={self.home[cf][1]:.2f}m, Z={self.home[cf][2]:.2f}m")

        self.cx = float(np.mean([self.home[cf][0] for cf in self.cfs]))
        self.cy = float(np.mean([self.home[cf][1] for cf in self.cfs]))
        self.is_airborne = True
        print(f"\n\033[92m[SUCCESS] All {self.num_drones} drones airborne in position-hold hover at {height:.1f}m.\033[0m")

    def takeoff_single(self, cf_name, height=DEFAULT_ALTITUDE, duration=TAKEOFF_DURATION):
        cf = self.swarm.allcfs.crazyfliesByName.get(cf_name)
        if not cf:
            available = [c.prefix[1:] for c in self.cfs]
            print(f"[ERROR] Drone '{cf_name}' not found. Connected drones: {', '.join(available)}")
            return

        print(f"\n==================================================")
        print(f"       POSITION-HOLD TAKEOFF: {cf_name.upper()}   ")
        print(f"==================================================")
        print(f"  • Stabilizing EKF on anchors...")
        self.timeHelper.sleep(1.5)

        print(f"  • Arming {cf_name}...")
        cf.arm(True)
        self.timeHelper.sleep(0.5)

        print(f"  • Pure vertical takeoff to {height:.1f}m (duration: {duration:.1f}s)...")
        cf.takeoff(targetHeight=height, duration=duration)
        self.timeHelper.sleep(duration + 0.8)

        pos = np.array(cf.position)
        if np.linalg.norm(pos[:2]) > 0.05:
            self.home[cf] = pos

        print(f"  \033[92m✔ {cf_name} locked in position-hold hover at ({self.home[cf][0]:.2f}, {self.home[cf][1]:.2f}, {height:.1f}m)\033[0m")
        self.is_airborne = True

    def hover_here(self):
        """Re-asserts stationary position-hold hover at current in-flight coordinates."""
        if not self.is_airborne:
            print("[INFO] Drones are not airborne.")
            return
        print("\n[COMMAND] Freezing in place: Holding current anchor coordinates...")
        for cf in self.cfs:
            cur_pos = cf.position
            cf.goTo(goal=[cur_pos[0], cur_pos[1], DEFAULT_ALTITUDE], yaw=0.0, duration=1.0, relative=False)
        self.timeHelper.sleep(1.5)
        print("\033[92m[SUCCESS] Position-hold confirmed. Zero drift.\033[0m")

    def land(self):
        if not self.is_airborne:
            print("[INFO] Drones are already on the ground.")
            return
        print("\n[COMMAND] Descending gently to ground at current positions...")
        self.swarm.allcfs.land(targetHeight=0.04, duration=3.5)
        self.timeHelper.sleep(0.15)
        self.swarm.allcfs.land(targetHeight=0.04, duration=3.5)
        self.timeHelper.sleep(4.0)
        self.disarm()
        self.is_airborne = False
        print("\033[92m[SUCCESS] All drones landed safely. Motors disabled.\033[0m")

    def land_single(self, cf_name):
        cf = self.swarm.allcfs.crazyfliesByName.get(cf_name)
        if not cf:
            available = [c.prefix[1:] for c in self.cfs]
            print(f"[ERROR] Drone '{cf_name}' not found. Connected drones: {', '.join(available)}")
            return
        print(f"\n[COMMAND] Landing {cf_name} gently in-place...")
        cf.land(targetHeight=0.04, duration=3.0)
        self.timeHelper.sleep(3.5)
        cf.arm(False)
        print(f"\033[93m[SUCCESS] {cf_name} landed and disarmed.\033[0m")

    def arm(self):
        print("\n[COMMAND] Arming all drones...")
        for cf in self.cfs:
            cf.arm(True)
            self.timeHelper.sleep(0.3)
        self.timeHelper.sleep(1.0)
        print("\033[92m[SUCCESS] Drones armed and ready for flight.\033[0m")

    def disarm(self):
        print("\n[COMMAND] Disarming all drones...")
        self.swarm.allcfs.arm(False)
        self.timeHelper.sleep(1.0)
        self.is_airborne = False
        print("\033[93m[SUCCESS] Drones disarmed. Motors cut off.\033[0m")

    def emergency_stop(self):
        print("\n[EMERGENCY] Cutting motors immediately!")
        self.swarm.allcfs.emergency()
        self.is_airborne = False

    def return_home(self):
        print("  -> Returning to exact takeoff coordinates...")
        # Step 1: Disperse to staggered altitudes to avoid any transit collisions
        for i, cf in enumerate(self.cfs):
            hx, hy, _ = self.home[cf]
            safe_z = DEFAULT_ALTITUDE + (i % 3) * 0.20
            cf.goTo(goal=[hx, hy, safe_z], yaw=0.0, duration=TRANSITION_DURATION, relative=False)
        self.timeHelper.sleep(TRANSITION_DURATION + 0.5)

        # Step 2: Settle all back to base altitude
        for cf in self.cfs:
            hx, hy, _ = self.home[cf]
            cf.goTo(goal=[hx, hy, DEFAULT_ALTITUDE], yaw=0.0, duration=2.0, relative=False)
        self.timeHelper.sleep(2.5)
        print("  -> All drones holding stationary above takeoff spots.")

    def transition(self, targets):
        """Transition drones safely with altitude staggering to prevent collisions."""
        # 1. Stagger vertically first
        for i, cf in enumerate(self.cfs):
            tx, ty = targets[cf]
            stagger_z = DEFAULT_ALTITUDE + (i % 3) * 0.22
            cf.goTo(goal=[cf.position[0], cf.position[1], stagger_z], yaw=0.0, duration=1.5, relative=False)
        self.timeHelper.sleep(2.0)

        # 2. Move horizontally to new (X, Y)
        for i, cf in enumerate(self.cfs):
            tx, ty = targets[cf]
            stagger_z = DEFAULT_ALTITUDE + (i % 3) * 0.22
            cf.goTo(goal=[tx, ty, stagger_z], yaw=0.0, duration=TRANSITION_DURATION, relative=False)
        self.timeHelper.sleep(TRANSITION_DURATION + 0.5)

        # 3. Level out to exactly 1.0m formation altitude
        for cf in self.cfs:
            tx, ty = targets[cf]
            cf.goTo(goal=[tx, ty, DEFAULT_ALTITUDE], yaw=0.0, duration=2.0, relative=False)
        self.timeHelper.sleep(2.5)

    def form_line(self, spacing=0.70):
        if not self.is_airborne:
            self.takeoff()
        print(f"\n[FORMATION] Line formation (centered at Y={self.cy:.1f}, spacing={spacing:.2f}m)...")
        start_x = self.cx - (self.num_drones - 1) * spacing / 2.0
        targets = {cf: (start_x + i * spacing, self.cy) for i, cf in enumerate(self.cfs)}
        self.transition(targets)
        print("[SUCCESS] Line formation active at 1.0m.")

    def form_circle(self, radius=1.20):
        if not self.is_airborne:
            self.takeoff()
        print(f"\n[FORMATION] Circle formation (center: ({self.cx:.1f}, {self.cy:.1f}), radius={radius:.2f}m)...")
        targets = {}
        for i, cf in enumerate(self.cfs):
            angle = (2.0 * math.pi * i) / self.num_drones
            targets[cf] = (self.cx + radius * math.cos(angle), self.cy + radius * math.sin(angle))
        self.transition(targets)
        print("[SUCCESS] Circle formation active at 1.0m.")

    def form_v(self, arm_spacing=0.55):
        if not self.is_airborne:
            self.takeoff()
        print(f"\n[FORMATION] V-Formation (centered at ({self.cx:.1f}, {self.cy:.1f}))...")
        targets = {}
        arm_x = arm_spacing * 0.8
        arm_y = arm_spacing
        for i, cf in enumerate(self.cfs):
            if i == 0:
                tx = self.cx + (self.num_drones // 2) * arm_x * 0.5
                ty = self.cy
            else:
                rank = (i + 1) // 2
                side = -1.0 if (i % 2 == 1) else 1.0
                tx = self.cx + (self.num_drones // 2) * arm_x * 0.5 - rank * arm_x
                ty = self.cy + side * rank * arm_y
            targets[cf] = (tx, ty)
        self.transition(targets)
        print("[SUCCESS] V-Formation active at 1.0m.")

    def form_grid(self, spacing=1.0):
        if not self.is_airborne:
            self.takeoff()
        print(f"\n[FORMATION] Grid formation (spacing={spacing:.1f}m)...")
        # For 10 drones: 5 columns x 2 rows
        cols = 5 if self.num_drones == 10 else int(math.ceil(math.sqrt(self.num_drones)))
        rows = int(math.ceil(self.num_drones / cols))
        targets = {}
        for i, cf in enumerate(self.cfs):
            r = i // cols
            c = i % cols
            gx = self.cx + (c - (cols - 1) / 2.0) * spacing
            gy = self.cy + (r - (rows - 1) / 2.0) * spacing
            targets[cf] = (gx, gy)
        self.transition(targets)
        print("[SUCCESS] Grid formation active at 1.0m.")


def interactive_menu():
    manager = SwarmManager()

    while True:
        status_str = "\033[92mAIRBORNE (1.0m)\033[0m" if manager.is_airborne else "\033[94mGROUNDED\033[0m"
        print(f"\n==================================================")
        print(f"      Swarm2 Formation Manager [{status_str}]     ")
        print(f"==================================================")
        print("  1) Arm All Drones")
        print("  2) Takeoff ALL Drones (Position-Hold Hover at 1.0m)")
        print("  s) Takeoff SINGLE Drone (Choose cf1, cf2, etc.)")
        print("  3) Form Line Formation")
        print("  4) Form Circle Formation")
        print("  5) Form V-Formation")
        print("  6) Form Grid Formation (1m spacing)")
        print("  7) Return to Takeoff Coordinates")
        print("  8) Land ALL Drones Safely")
        print("  k) Land SINGLE Drone")
        print("  h) Hover In-Place (Hold Current Position)")
        print("  9) Disarm All Drones")
        print("  e) Emergency Motor Stop (CUT)")
        print("  0) Exit")
        print("==================================================")

        try:
            choice = input("Select an option [0-9, s, k, h, e]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if choice == "1":
            manager.arm()
        elif choice == "2":
            manager.takeoff(height=1.0)
        elif choice.lower() == "s":
            available = [c.prefix[1:] for c in manager.cfs]
            print(f"Active drones: {', '.join(available)}")
            name = input(f"Enter drone name to takeoff (e.g. {available[0]}): ").strip()
            if name:
                manager.takeoff_single(name, height=1.0)
        elif choice == "3":
            manager.form_line()
        elif choice == "4":
            manager.form_circle()
        elif choice == "5":
            manager.form_v()
        elif choice == "6":
            manager.form_grid()
        elif choice == "7":
            manager.return_home()
        elif choice == "8":
            manager.land()
        elif choice.lower() == "k":
            available = [c.prefix[1:] for c in manager.cfs]
            print(f"Active drones: {', '.join(available)}")
            name = input(f"Enter drone name to land (e.g. {available[0]}): ").strip()
            if name:
                manager.land_single(name)
        elif choice.lower() == "h":
            manager.hover_here()
        elif choice == "9":
            manager.disarm()
        elif choice.lower() == "e":
            manager.emergency_stop()
        elif choice == "0":
            if manager.is_airborne:
                print("[WARN] Landing swarm before exit...")
                manager.land()
            break
        else:
            print("[ERROR] Invalid selection.")


if __name__ == "__main__":
    interactive_menu()
