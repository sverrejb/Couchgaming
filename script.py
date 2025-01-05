#! /usr/bin/python3

from evdev import InputDevice, ecodes, list_devices, ff, categorize
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

def main():
    device = find_controller_device()
    pressed_buttons = set()
    combo_pressed_time = None

    try:
        while True:
            try:
                for event in device.read_loop():
                    if event.type == ecodes.EV_KEY:
                        key_event = categorize(event)
                        if key_event.keystate == key_event.key_down:
                            pressed_buttons.add(key_event.scancode)
                            if BTN_A in pressed_buttons and BTN_B in pressed_buttons:
                                if combo_pressed_time is None:
                                    combo_pressed_time = time.time()
                        elif key_event.keystate == key_event.key_up:
                            pressed_buttons.discard(key_event.scancode)
                            combo_pressed_time = None

                    if combo_pressed_time and (time.time() - combo_pressed_time >= COMBO_HOLD_TIME):
                        
                        execute_commands(device)
                        combo_pressed_time = None

            except OSError as e:
                if e.errno == 19:  # 19 = No such device (disconnected)
                    print(f'Device disconnected. Reconnecting...')
                    device = find_controller_device()
                else:
                    print(f'Unexpected error: {e}')
                    time.sleep(RETRY_INTERVAL)

    except KeyboardInterrupt:
        print('Exiting...')


def find_controller_device():
    while True:
        try:
            devices = [InputDevice(path) for path in list_devices()]
            for dev in devices:
                if dev.path == DEVICE_PATH:
                    print(f'Device found: {dev.path}')
                    return InputDevice(DEVICE_PATH)
            print(f'Device not found. Retrying in {RETRY_INTERVAL} seconds...')
            time.sleep(RETRY_INTERVAL)
        except Exception as e:
            print(f'Error checking devices: {e}')
            time.sleep(RETRY_INTERVAL)

def execute_commands(device):
    print('Button combo detected! Running script...')
    rumble_controller(device)
    print('Waking TV....')
    send_wol_packet(MAC_ADDRESS_TV)
    print('Waking Desktop....')
    send_wol_packet(MAC_ADDRESS_DESKTOP) 
    wake_screen()
    start_steamlink()
    print('Setting TV input')
    set_tv_input()        
    print('Commands completed.')

def rumble_controller(device):
    rumble = ff.Rumble(strong_magnitude=0xc000, weak_magnitude=0xc000)
    duration_ms = 500

    effect = ff.Effect(
        ecodes.FF_RUMBLE,
        -1,
        0,
        ff.Trigger(0, 0),
        ff.Replay(duration_ms, 0),
        ff.EffectType(ff_rumble_effect=rumble)
    )
    
    effect_id = device.upload_effect(effect)
    repeat_count = 1
    device.write(ecodes.EV_FF, effect_id, repeat_count)
    time.sleep(0.5)
    device.erase_effect(effect_id) 

def send_wol_packet(mac_address):
    mac_bytes = bytes.fromhex(mac_address.replace(':', ''))
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    # TV will sometimes not respond, so we spam WoL a bit.
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('<broadcast>', 9))

def wake_screen():
    # If TV is ON, but media-PC has blanked the screen/screensaver, move the mouse a bit.
    x, y = random.randint(0, 10), random.randint(0, 10)
    subprocess.run(['ydotool', 'mousemove', str(x), str(y)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_steamlink():
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'com.valvesoftware.SteamLink'], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.stdout:
            print('SteamLink is already running, skipping launch.')
        else:
            print('Starting SteamLink...')
            with open('/home/sverrejb/workspace/gamestart/steamlink.log', 'a') as log_file:
                subprocess.Popen(
                    'QT_QPA_PLATFORM=wayland WAYLAND_DISPLAY=wayland-0 flatpak run com.valvesoftware.SteamLink',
                    shell=True,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={
                            'QT_QPA_PLATFORM': 'wayland',
                            'WAYLAND_DISPLAY': 'wayland-0',
                            'XDG_RUNTIME_DIR': '/run/user/1000'
                        }
                )
    except Exception as e:
        print(f'Error checking for SteamLink process: {e}')

def set_tv_input():
    try:
        subprocess.run(['/home/sverrejb/.local/bin/alga', 'input', 'set', HDMI_INPUT], check=True)
    except:
        print('Initial HDMI-switch failed. Trying harder.')
        while True:
            response = subprocess.run(['ping', '-c', '1', '-W', '1', '192.168.1.43'], stdout=subprocess.PIPE)
            if response.returncode == 0:
                print('TV is responding to ping.')
                break
            else:
                print('Waiting for TV to respond to ping...')
                time.sleep(1)
        time.sleep(10)
        
        for i in range(5):
            print(f'Setting HDMI-input {i+1}/5')
            subprocess.run(['/home/sverrejb/.local/bin/alga', 'input', 'set', HDMI_INPUT])
            time.sleep(0.2)

if __name__ == '__main__':
    main()