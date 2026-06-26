import paramiko
import sys
import time

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("Connected to STB. Initiating reboot...")
    except Exception as e:
        print(f"ERROR: Cannot connect to STB to trigger reboot: {e}")
        sys.exit(1)
        
    # Trigger reboot
    # The SSH connection will drop, which is expected
    try:
        stdin, stdout, stderr = client.exec_command(f"echo '{PASSWORD}' | sudo -S reboot")
        # Give it a second to send
        time.sleep(1)
    except Exception as e:
        print("Reboot command sent (connection drop expected).")
        
    client.close()
    
    # Wait and check for online status
    print("Waiting for STB to shut down and boot back up...")
    time.sleep(15)  # Wait 15 seconds before first check
    
    max_attempts = 15
    attempt = 1
    online = False
    
    while attempt <= max_attempts:
        print(f"Connection attempt {attempt}/{max_attempts}...")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=5)
            print("STB is back online!")
            online = True
            break
        except Exception as e:
            attempt += 1
            time.sleep(5)
            
    if not online:
        print("ERROR: STB did not come back online within the timeout period.")
        sys.exit(1)
        
    # Verify post-reboot health
    print("\nVerifying post-reboot configuration...")
    commands = {
        "Uptime": "uptime",
        "Scaling Governor": "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
        "Congestion Control": "sysctl net.ipv4.tcp_congestion_control",
        "Dirty Ratio": "sysctl vm.dirty_ratio",
        "FSTAB Options": "mount | grep ' / '",
        "Kernel Log Errors": "dmesg | grep -i -E 'error|fail|warn' | tail -n 10"
    }
    
    for desc, cmd in commands.items():
        print(f"\n--- {desc} ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore').strip()
        err = stderr.read().decode('utf-8', errors='ignore').strip()
        if out:
            print(out)
        if err:
            print(f"Err/Warn: {err}")
            
    client.close()
    print("\nReboot and verification complete!")

if __name__ == "__main__":
    main()
