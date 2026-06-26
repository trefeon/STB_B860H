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
    escaped_cmd = cmd.replace("'", "'\\''")
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{escaped_cmd}'"
    stdin, stdout, stderr = client.exec_command(full_cmd)
    
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
        print("Connected to STB. Commencing further server performance optimizations...")
    except Exception as e:
        print(f"ERROR: Connection failed: {e}")
        sys.exit(1)

    # 1. Enable TCP BBR Congestion Control & increase network buffer sizes
    network_opt_cmd = (
        "echo 'net.core.default_qdisc = fq' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'net.ipv4.tcp_congestion_control = bbr' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'net.ipv4.tcp_rmem = 4096 87380 16777216' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'net.ipv4.tcp_wmem = 4096 65536 16777216' >> /etc/sysctl.d/99-server-opt.conf && "
        "sysctl -p /etc/sysctl.d/99-server-opt.conf"
    )
    run_sudo_cmd(client, network_opt_cmd, "Enabling TCP BBR and optimizing TCP buffers")

    # 2. Prevent SD Card Write Blocker Hangs (Dirty page ratios & file descriptors)
    sd_write_opt_cmd = (
        "echo 'vm.dirty_background_ratio = 5' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'vm.dirty_ratio = 10' >> /etc/sysctl.d/99-server-opt.conf && "
        "echo 'fs.file-max = 2097152' >> /etc/sysctl.d/99-server-opt.conf && "
        "sysctl -p /etc/sysctl.d/99-server-opt.conf"
    )
    run_sudo_cmd(client, sd_write_opt_cmd, "Optimizing kernel dirty memory writeback ratios and file limits")

    # 3. Disable redundant logging daemon (rsyslog) to save CPU/Memory
    # Armbian already logs to systemd journald in memory/zram
    rsyslog_opt_cmd = "systemctl stop rsyslog && systemctl disable rsyslog"
    run_sudo_cmd(client, rsyslog_opt_cmd, "Disabling rsyslog service (redundant logging)")

    # 4. Unload failing Bluetooth kernel modules immediately to stop timeout loops
    unload_bt_modules_cmd = "modprobe -r hci_uart btbcm 2>/dev/null || echo 'Modules busy, will unload on reboot'"
    run_sudo_cmd(client, unload_bt_modules_cmd, "Unloading failing Broadcom Bluetooth modules")

    # 5. Verify the sysctl configuration
    run_sudo_cmd(client, "sysctl net.ipv4.tcp_congestion_control vm.dirty_ratio fs.file-max", "Verifying applied parameters")

    client.close()
    print("\nFurther server optimizations successfully completed!")

if __name__ == "__main__":
    main()
