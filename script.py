#! /usr/bin/python3

import evdev
from evdev import InputDevice, ecodes, list_devices
import time
import subprocess
import random
import socket


DEVICE_PATH = '/dev/input/event14'
RETRY_INTERVAL = 3

def find_controller_device():
    while True:
        try:
            devices = [InputDevice(path) for path in list_devices()]
            for dev in devices:
                if dev.path == DEVICE_PATH:  # Replace with custom matching logic if needed
                    print(f"Device found: {dev.path}")
                    return InputDevice(DEVICE_PATH)
            print(f"Device not found. Retrying in {RETRY_INTERVAL} seconds...")
            time.sleep(RETRY_INTERVAL)
        except Exception as e:
            print(f"Error checking devices: {e}")
            time.sleep(RETRY_INTERVAL)

device = find_controller_device()

BTN_A = ecodes.BTN_SOUTH 
BTN_B = ecodes.BTN_EAST

pressed_buttons = set()
combo_pressed_time = None
COMBO_HOLD_TIME = 3  # Seconds

def send_wol_packet(mac_address):
       mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
       magic_packet = b'\xff' * 6 + mac_bytes * 16
       with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
           sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
           sock.sendto(magic_packet, ('<broadcast>', 9))

def start_steamlink():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "com.valvesoftware.SteamLink"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # If pgrep finds an existing process, it returns a non-empty result
        if result.stdout:
            print("SteamLink is already running, skipping launch.")
        else:
            # If SteamLink is not running, start it
            print("Starting SteamLink...")
            with open("/home/sverrejb/workspace/gamestart/steamlink.log", "a") as log_file:
                subprocess.Popen(
                    "QT_QPA_PLATFORM=wayland WAYLAND_DISPLAY=wayland-0 flatpak run com.valvesoftware.SteamLink",
                    shell=True,
                    stdout=log_file,  # Redirect stdout to the log file
                    stderr=subprocess.STDOUT,  # Redirect stderr to the same log file
                    start_new_session=True,
                    env={
                            "QT_QPA_PLATFORM": "wayland",
                            "WAYLAND_DISPLAY": "wayland-0",
                            "XDG_RUNTIME_DIR": "/run/user/1000"
                        }
                )
    except Exception as e:
        print(f"Error checking for SteamLink process: {e}")

def execute_command():
    print("Button combo detected! Running script...")
    send_wol_packet("d8:80:83:9c:5b:2f")  # Replace with the actual MAC address of DESKTOP-L87EPJN

    x, y = random.randint(0, 10), random.randint(0, 10)
    subprocess.run(["ydotool", "mousemove", str(x), str(y)])

    start_steamlink()

    for _ in range(3):
        subprocess.run(["/home/sverrejb/.local/bin/alga", "power", "on"])
        time.sleep(0.5)
    
    time.sleep(5)
    subprocess.run(["/home/sverrejb/.local/bin/alga", "input", "set", "HDMI_2"])

try:
    while True:
        try:
     # Read input events
            for event in device.read_loop():
                if event.type == ecodes.EV_KEY:  # Key press/release events
                    key_event = evdev.categorize(event)

                    # Track pressed buttons
                    if key_event.keystate == key_event.key_down:
                        pressed_buttons.add(key_event.scancode)
                        if BTN_A in pressed_buttons and BTN_B in pressed_buttons:
                            if combo_pressed_time is None:
                                combo_pressed_time = time.time()
                    elif key_event.keystate == key_event.key_up:
                        pressed_buttons.discard(key_event.scancode)
                        combo_pressed_time = None

                # Check if combo is held long enough
                if combo_pressed_time and (time.time() - combo_pressed_time >= COMBO_HOLD_TIME):
                    execute_command()
                    combo_pressed_time = None  # Reset timer after execution

        except OSError as e:
            if e.errno == 19:  # No such device (disconnected)
                print(f"Device disconnected. Reconnecting...")
                device = find_device()  # Wait and retry if device disconnects
            else:
                print(f"Unexpected error: {e}")
                time.sleep(RETRY_INTERVAL)  # Sleep before retrying

except KeyboardInterrupt:
    print("Exiting...")