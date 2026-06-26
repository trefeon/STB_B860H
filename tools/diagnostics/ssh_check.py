import paramiko
import sys

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

DIAGNOSTIC_COMMANDS = {
    "System & Kernel": "uname -a",
    "Uptime": "uptime",
    "CPU Temperature": "echo \"$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0) / 1000\" | bc -l",
    "Memory Usage": "free -h",
    "Disk Usage": "df -h /",
    "Network Interfaces": "ip -br addr show",
    "Wi-Fi Connection Status": "nmcli device status",
    "Wi-Fi Modules loaded": "lsmod | grep -E 'brcm|rtl|mt76|cfg80211|mac80211' | head -n 10",
    "Failed Services": "systemctl --failed --no-legend",
    "Recent Kernel Errors/Warnings": "dmesg | grep -i -E 'error|fail|warn' | tail -n 15"
}

def run_ssh_diagnostics():
    print(f"Connecting to STB at {HOSTNAME} as {USERNAME}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("Connected successfully! Starting health check...\n")
    except Exception as e:
        print(f"ERROR: Failed to connect to STB: {e}")
        sys.exit(1)
        
    for section, cmd in DIAGNOSTIC_COMMANDS.items():
        print("=" * 60)
        print(f"  {section}")
        print("=" * 60)
        print(f"Running: {cmd}")
        print("-" * 60)
        try:
            stdin, stdout, stderr = client.exec_command(cmd)
            out = stdout.read().decode('utf-8', errors='ignore').strip()
            err = stderr.read().decode('utf-8', errors='ignore').strip()
            
            if out:
                print(out)
            if err:
                print(f"Stderr: {err}")
            if not out and not err:
                print("(No output)")
        except Exception as e:
            print(f"Failed to execute command: {e}")
        print()
        
    client.close()
    print("Health check completed.")

if __name__ == "__main__":
    run_ssh_diagnostics()
