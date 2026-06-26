import paramiko
import sys

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

COMMANDS = {
    "fstab": "cat /etc/fstab",
    "cpu governor": "cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null",
    "cpu speed": "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null",
    "zram status": "/sbin/zramctl 2>/dev/null || /usr/sbin/zramctl 2>/dev/null || echo 'No zramctl'",
    "swappiness": "/sbin/sysctl vm.swappiness 2>/dev/null || /usr/sbin/sysctl vm.swappiness 2>/dev/null || echo 'No sysctl'",
    "journald limit": "grep -E '^SystemMaxUse|^RuntimeMaxUse|^Storage' /etc/systemd/journald.conf || echo 'No systemd limits custom set'",
    "running services": "systemctl list-units --type=service --state=running --no-legend | awk '{print $1, $2, $3}'",
    "hciuart status": "systemctl status hciuart 2>/dev/null || systemctl status bluetooth 2>/dev/null || echo 'No hciuart/bluetooth'"
}

def safe_print(text):
    try:
        encoding = sys.stdout.encoding or 'utf-8'
        sys.stdout.write(text.encode(encoding, errors='replace').decode(encoding))
        sys.stdout.flush()
    except:
        sys.stdout.write(text.encode('ascii', errors='replace').decode('ascii'))
        sys.stdout.flush()

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    for name, cmd in COMMANDS.items():
        print(f"=== {name} ===")
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore').strip()
        err = stderr.read().decode('utf-8', errors='ignore').strip()
        if out:
            safe_print(out + "\n")
        if err:
            safe_print(f"Err: {err}\n")
        print()
        
    client.close()

if __name__ == "__main__":
    main()
