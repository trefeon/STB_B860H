import paramiko
import sys

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    stdin, stdout, stderr = client.exec_command("cat /etc/default/cpufrequtils 2>/dev/null || echo 'No cpufrequtils'")
    print("cpufrequtils:", stdout.read().decode('utf-8').strip())
    
    stdin, stdout, stderr = client.exec_command("cat /sys/block/mmcblk0/queue/scheduler")
    print("I/O Scheduler:", stdout.read().decode('utf-8').strip())
    
    client.close()

if __name__ == "__main__":
    main()
