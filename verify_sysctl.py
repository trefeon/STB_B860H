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
        
    stdin, stdout, stderr = client.exec_command("/sbin/sysctl net.ipv4.tcp_congestion_control vm.swappiness vm.dirty_ratio fs.file-max")
    print(stdout.read().decode('utf-8').strip())
    client.close()

if __name__ == "__main__":
    main()
