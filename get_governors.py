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
        
    stdin, stdout, stderr = client.exec_command("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors")
    print("Governors:", stdout.read().decode('utf-8').strip())
    
    stdin, stdout, stderr = client.exec_command("cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_min_freq")
    print("Min Freqs:", stdout.read().decode('utf-8').strip().split())
    
    stdin, stdout, stderr = client.exec_command("cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq")
    print("Max Freqs:", stdout.read().decode('utf-8').strip().split())
    
    client.close()

if __name__ == "__main__":
    main()
