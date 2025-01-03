#! /usr/bin/python3

import evdev
from evdev import InputDevice, ecodes, list_devices, ff
import time
import subprocess
import random
import socket

MAC_ADDRESS_DESKTOP = 'd8:80:83:9c:5b:2f'
MAC_ADDRESS_TV = '48:8d:36:bc:e8:ec'
DEVICE_PATH = '/dev/input/event14'
RETRY_INTERVAL = 3
BTN_A = ecodes.BTN_SOUTH 
BTN_B = ecodes.BTN_EAST
COMBO_HOLD_TIME = 1.5 # Seconds
HDMI_INPUT = 'HDMI_2'

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

def send_wol_packet(mac_address):
    mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('<broadcast>', 9))

def wake_screen():
    x, y = random.randint(0, 10), random.randint(0, 10)
    subprocess.run(["ydotool", "mousemove", str(x), str(y)])


def start_steamlink():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "com.valvesoftware.SteamLink"], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # If pgrep finds an existing process, it returns a non-empty result
        if result.stdout:
            print("Bringing SteamLink to the foreground...")
            subprocess.run(["swaymsg", "[app_id=\"com.valvesoftware.SteamLink\"] focus"])
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

def rumble_controller(device):
    rumble = ff.Rumble(strong_magnitude=0xc000, weak_magnitude=0xc000)
    duration_ms = 500

    effect = ff.Effect(
        ecodes.FF_RUMBLE, # type
        -1, # id (set by ioctl)
        0,
        ff.Trigger(0, 0), # no triggers
        ff.Replay(duration_ms, 0), # length and delay
        ff.EffectType(ff_rumble_effect=rumble)
    )
    
    effect_id = device.upload_effect(effect)
    repeat_count = 1
    device.write(ecodes.EV_FF, effect_id, repeat_count)
    time.sleep(0.5)
    device.erase_effect(effect_id) 

def execute_command():
    print("Button combo detected! Running script...")
    rumble_controller(device)
    send_wol_packet(MAC_ADDRESS_TV)
    send_wol_packet(MAC_ADDRESS_DESKTOP) 
    wake_screen()
    start_steamlink()
    
    try:
        subprocess.run(["/home/sverrejb/.local/bin/alga", "input", "set", HDMI_INPUT], check=True)
    except:
        print('Initial HDMI-switch failed. Trying harder.')
        while True:
            response = subprocess.run(["ping", "-c", "1", "-W", "1", "192.168.1.43"], stdout=subprocess.PIPE)
            if response.returncode == 0:
                print("TV is responding to ping.")
                break
            else:
                print("Waiting for TV to respond to ping...")
                time.sleep(1)
        time.sleep(10)
        
        for i in range(5):
            print(f'Setting HDMI-input {i+1}/5')
            subprocess.run(["/home/sverrejb/.local/bin/alga", "input", "set", HDMI_INPUT])
            time.sleep(0.2)
        
    print('Steps completed.')

device = find_controller_device()
pressed_buttons = set()
combo_pressed_time = None

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
                device = find_controller_device()  # Wait and retry if device disconnects
            else:
                print(f"Unexpected error: {e}")
                time.sleep(RETRY_INTERVAL)  # Sleep before retrying

except KeyboardInterrupt:
    print("Exiting...")