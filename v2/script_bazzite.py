#! /usr/bin/python3

import time
import subprocess
import random
import socket

MAC_ADDRESS_TV = '48:8d:36:bc:e8:ec'
IP_ADDRESS_TV = '192.168.1.43'
RETRY_INTERVAL = 3
HDMI_INPUT = 'HDMI_2'

def main():
    print('PC woke up - assuming controller triggered wake. Running commands...')
    
    # Add a small delay to ensure system is fully awake
    time.sleep(2)
    
    # Execute the commands immediately
    execute_commands_on_wake()
    
    print('Script completed successfully.')


def execute_commands_on_wake():
    print('Running wake-up commands...')
    start_steam()
    print('Waking TV....')
    send_wol_packet(MAC_ADDRESS_TV)
    wake_screen()
    print('Setting TV input')
    set_tv_input()        
    print('Commands completed.') 

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

def is_wake_from_suspend():
    """Check if system is waking from suspend vs fresh boot"""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.read().split()[0])
        
        # If uptime is more than 5 minutes, assume it's a wake from suspend
        # Adjust this threshold based on your needs
        return uptime_seconds > 300
    except Exception as e:
        print(f'Error checking uptime: {e}')
        # Default to running Steam if we can't determine
        return True


def start_steam():
    if not is_wake_from_suspend():
        return
    
    try:
        # Check if Steam is already running (native process)
        result = subprocess.run(
            ['pgrep', '-f', 'steam'], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            print('Steam is already running, skipping launch.')
        else:
            print('Starting Steam...')
            log_path = '/tmp/steamstart.log'
            
            with open(log_path, 'a') as log_file:
                subprocess.Popen(
                    ['steam'],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
    except Exception as e:
        print(f'Error checking for Steam process: {e}')

def set_tv_input():
    try:
        subprocess.run(['/home/sverrejb/.local/bin/alga', 'input', 'set', HDMI_INPUT], check=True)
    except:
        print('Initial HDMI-switch failed. Trying harder.')
        while True:
            response = subprocess.run(['ping', '-c', '1', '-W', '1', IP_ADDRESS_TV], stdout=subprocess.PIPE)
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
    try:
        main()
    except KeyboardInterrupt:
        print('Exiting...')