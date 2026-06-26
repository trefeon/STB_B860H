import paramiko
import sys

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

def run_cmd(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    err = stderr.read().decode('utf-8', errors='ignore').strip()
    return out, err

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)
        
    print("--- dmesg ---")
    out, err = run_cmd(client, "dmesg | grep -i -E 'blue|firmware|hci'")
    print(out)
    
    print("--- rfkill ---")
    out, err = run_cmd(client, "rfkill list")
    print(out)
    
    print("--- hciconfig ---")
    out, err = run_cmd(client, "hciconfig -a")
    print(out)
    
    print("--- lsusb ---")
    out, err = run_cmd(client, "lsusb")
    print(out)
    
    print("--- lshw / dev ---")
    out, err = run_cmd(client, "ls -l /dev/tty*")
    # print only lines containing ttyAML or ttyS
    for line in out.splitlines():
        if "ttyAML" in line or "ttyS" in line:
            print(line)
            
    client.close()

if __name__ == "__main__":
    main()
