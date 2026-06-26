import paramiko
import sys

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

COMMANDS = {
    "dmesg (bluetooth/firmware)": "dmesg | grep -i -E 'blue|firmware|hci'",
    "rfkill status": "rfkill list",
    "bluetoothctl show": "bluetoothctl show",
    "hciconfig status": "hciconfig -a",
    "lsusb": "lsusb",
    "firmware files in brcm": "ls -l /lib/firmware/brcm/ /lib/firmware/rtl_bt/ 2>/dev/null",
    "hci_uart status": "systemctl status hciuart 2>/dev/null || systemctl status bluetooth"
}

def check_bluetooth():
    print(f"Connecting to STB at {HOSTNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("Connected! Running Bluetooth Diagnostics...\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    for name, cmd in COMMANDS.items():
        print("=" * 60)
        print(f"  {name}")
        print("=" * 60)
        print(f"Command: {cmd}")
        print("-" * 60)
        try:
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode('utf-8', errors='ignore').strip()
            err = stderr.read().decode('utf-8', errors='ignore').strip()
            if out:
                print(out)
            if err:
                print(f"Error output:\n{err}")
            if not out and not err:
                print("(No output)")
        except Exception as e:
            print(f"Execution error: {e}")
        print()
        
    client.close()

if __name__ == "__main__":
    check_bluetooth()
