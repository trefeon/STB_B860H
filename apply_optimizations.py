import paramiko
import sys
import time

HOSTNAME = "<STB-LAN-IP>"
USERNAME = "trefeon"
PASSWORD = "<stb-password>"

def safe_print(text):
    try:
        encoding = sys.stdout.encoding or 'utf-8'
        sys.stdout.write(text.encode(encoding, errors='replace').decode(encoding))
        sys.stdout.flush()
    except:
        sys.stdout.write(text.encode('ascii', errors='replace').decode('ascii'))
        sys.stdout.flush()

def run_sudo_cmd(client, cmd, desc):
    print("\n" + "=" * 60)
    print(f"  [ACTION] {desc}")
    print("=" * 60)
    # Escape single quotes in cmd for safe wrapping in bash -c '...'
    escaped_cmd = cmd.replace("'", "'\\''")
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{escaped_cmd}'"
    stdin, stdout, stderr = client.exec_command(full_cmd)
    
    # Wait for completion
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            out = stdout.channel.recv(1024).decode('utf-8', errors='ignore')
            out = out.replace(f"[sudo] password for {USERNAME}:", "")
            safe_print(out)
        time.sleep(0.1)
        
    out = stdout.read().decode('utf-8', errors='ignore').replace(f"[sudo] password for {USERNAME}:", "")
    safe_print(out)
    err = stderr.read().decode('utf-8', errors='ignore').replace(f"[sudo] password for {USERNAME}:", "")
    if err.strip():
        print("\nStderr/Warnings:")
        safe_print(err.strip() + "\n")

def main():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("Connected to STB. Commencing system optimizations...")
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        sys.exit(1)

    # 1. Optimize /etc/fstab for SD Card (add noatime, nodiratime)
    fstab_patch_cmd = (
        "grep -q 'noatime' /etc/fstab || "
        "sed -i 's/defaults,commit=120/defaults,noatime,nodiratime,commit=120/g' /etc/fstab"
    )
    run_sudo_cmd(client, fstab_patch_cmd, "Adding noatime,nodiratime to fstab root mount")

    # 2. Blacklist unused Bluetooth modules to prevent kernel timeout boot loops
    bt_blacklist_cmd = (
        "echo -e 'blacklist hci_uart\\nblacklist btbcm' > /etc/modprobe.d/blacklist-bluetooth.conf && "
        "depmod -a"
    )
    run_sudo_cmd(client, bt_blacklist_cmd, "Blacklisting hci_uart and btbcm modules")

    # 3. ZRAM swappiness optimization (vm.swappiness = 100 for memory compressed swap)
    zram_swap_cmd = (
        "echo 'vm.swappiness = 100' > /etc/sysctl.d/99-zram-swappiness.conf && "
        "sysctl -p /etc/sysctl.d/99-zram-swappiness.conf"
    )
    run_sudo_cmd(client, zram_swap_cmd, "Setting vm.swappiness = 100 for optimal ZRAM utilization")

    # 4. CPU Governor optimizations (enable cpufrequtils and change governor to schedutil)
    cpufreq_edit_cmd = (
        "sed -i 's/ENABLE=false/ENABLE=true/g' /etc/default/cpufrequtils && "
        "sed -i 's/GOVERNOR=ondemand/GOVERNOR=schedutil/g' /etc/default/cpufrequtils"
    )
    run_sudo_cmd(client, cpufreq_edit_cmd, "Configuring cpufrequtils to use schedutil governor")

    # Enable and restart cpufrequtils service if active
    cpufreq_service_cmd = (
        "systemctl daemon-reload && "
        "systemctl enable cpufrequtils 2>/dev/null || true && "
        "systemctl restart cpufrequtils 2>/dev/null || true"
    )
    run_sudo_cmd(client, cpufreq_service_cmd, "Enabling and restarting cpufrequtils service")

    # Force write immediate scaling governor to schedutil for all cores
    force_gov_cmd = "echo schedutil | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
    run_sudo_cmd(client, force_gov_cmd, "Force setting current CPU scaling governor to schedutil")

    # 5. Verify the current governor and fstab contents
    run_sudo_cmd(client, "cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor", "Verifying CPU scaling governor")
    run_sudo_cmd(client, "cat /etc/fstab", "Verifying /etc/fstab")
    run_sudo_cmd(client, "/sbin/sysctl vm.swappiness", "Verifying swappiness value")

    client.close()
    print("\nOptimizations successfully completed!")

if __name__ == "__main__":
    main()
