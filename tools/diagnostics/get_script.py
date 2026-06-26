import paramiko
import sys
import time

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

ESSENTIAL_PACKAGES = [
    "htop", "tmux", "curl", "wget", "git", "rsync", 
    "unzip", "zip", "dnsutils", "net-tools", "ncdu",
    "build-essential", "lm-sensors", "usbutils", "pciutils"
]

def run_server_setup():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("Connected to STB. Starting server cleanup and package installation...")
    except Exception as e:
        print(f"ERROR: Failed to connect: {e}")
        sys.exit(1)
        
    def safe_print(text):
        # Safely print Unicode text to Windows console
        try:
            encoding = sys.stdout.encoding or 'utf-8'
            sys.stdout.write(text.encode(encoding, errors='replace').decode(encoding))
            sys.stdout.flush()
        except:
            # Fallback
            sys.stdout.write(text.encode('ascii', errors='replace').decode('ascii'))
            sys.stdout.flush()

    # Helper to execute command with sudo
    def execute_sudo_cmd(cmd_text, description):
        print("\n" + "=" * 60)
        print(f"  {description}")
        print("=" * 60)
        full_cmd = f'echo "{PASSWORD}" | sudo -S {cmd_text}'
        stdin, stdout, stderr = client.exec_command(full_cmd)
        
        # Stream the output in real-time
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                out = stdout.channel.recv(1024).decode('utf-8', errors='ignore')
                out = out.replace(f"[sudo] password for {USERNAME}:", "")
                safe_print(out)
            time.sleep(0.1)
            
        # Get remaining output
        out = stdout.read().decode('utf-8', errors='ignore').replace(f"[sudo] password for {USERNAME}:", "")
        safe_print(out)
        err = stderr.read().decode('utf-8', errors='ignore').replace(f"[sudo] password for {USERNAME}:", "")
        if err.strip():
            print("\nStderr/Warnings:")
            safe_print(err.strip() + "\n")
            
    # 1. Update Package Database
    execute_sudo_cmd("apt-get update", "Updating Package Lists (apt-get update)")
    
    # 2. Upgrade existing packages to latest stable versions
    execute_sudo_cmd("apt-get upgrade -y", "Upgrading Existing System Packages (apt-get upgrade)")
    
    # 3. Install essential server packages
    pkgs_str = " ".join(ESSENTIAL_PACKAGES)
    execute_sudo_cmd(f"apt-get install -y {pkgs_str}", "Installing Essential Linux Server Packages")
    
    # 4. Cleanup package cache
    execute_sudo_cmd("apt-get autoremove -y --purge", "Removing Unused Dependencies (apt-get autoremove)")
    execute_sudo_cmd("apt-get autoclean", "Cleaning Up Downloaded Archives (apt-get autoclean)")
    execute_sudo_cmd("apt-get clean", "Clearing Package Cache (apt-get clean)")
    
    client.close()
    print("\nServer cleanup and essential installation complete!")

if __name__ == "__main__":
    run_server_setup()
