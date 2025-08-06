#! /usr/bin/python3

import time
import subprocess
import socket

MAC_ADDRESS_TV = '48:8d:36:bc:e8:ec'
IP_ADDRESS_TV = '192.168.1.43'
RETRY_INTERVAL = 3
HDMI_INPUT = 'HDMI_2'

def main():
    print('PC woke up - assuming controller triggered wake. Running commands...')
    
    # Add a small delay to ensure system is fully awake
    time.sleep(2)
    
    print('Running wake-up commands...')
    print('Waking TV....')
    send_wol_packet(MAC_ADDRESS_TV)
    print('Setting TV input')
    set_tv_input()        
    print('Commands completed.') 
    
    print('Script completed successfully.')
    

def send_wol_packet(mac_address):
    mac_bytes = bytes.fromhex(mac_address.replace(':', ''))
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    # TV will sometimes not respond, so we spam WoL a bit.
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('<broadcast>', 9))

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