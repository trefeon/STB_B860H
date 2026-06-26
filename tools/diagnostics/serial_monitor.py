import sys
import time
import serial
from serial.serialutil import SerialException

PORT = 'COM9'
BAUDRATE = 115200
LOG_FILE = 'live_boot.log'

def monitor_serial():
    ser = None
    print(f"=== Starting Auto-Reconnecting Serial Monitor on {PORT} at {BAUDRATE} baud ===")
    print(f"Writing live log to {LOG_FILE}")
    print("Press Ctrl+C to stop.")
    
    # Open log file in append mode, flushing after each write
    log_f = open(LOG_FILE, 'a', encoding='utf-8', errors='replace')
    
    while True:
        try:
            if ser is None or not ser.is_open:
                msg = f"\n[Connecting] Opening {PORT}..."
                print(msg, end="", flush=True)
                log_f.write(msg)
                log_f.flush()
                
                ser = serial.Serial(
                    port=PORT,
                    baudrate=BAUDRATE,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.1
                )
                print(" Connected!")
                log_f.write(" Connected!\n")
                log_f.flush()
                
            # Read incoming data
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                try:
                    text = data.decode('utf-8', errors='replace')
                except Exception:
                    text = data.decode('ascii', errors='ignore')
                
                # Write to stdout
                sys.stdout.write(text)
                sys.stdout.flush()
                
                # Write to log file
                log_f.write(text)
                log_f.flush()
                    
            time.sleep(0.01)
            
        except SerialException as se:
            err_msg = ""
            if "PermissionError" in str(se) or "Access is denied" in str(se):
                err_msg = f"\n[Error] Port {PORT} is busy or access is denied. Retrying in 2s...\n"
            else:
                err_msg = f"\n[Disconnected] Connection lost: {se}. Reconnecting in 2s...\n"
                
            print(err_msg, end="", flush=True)
            log_f.write(err_msg)
            log_f.flush()
            
            if ser:
                try:
                    ser.close()
                except Exception:
                    pass
                ser = None
            time.sleep(2)
            
        except KeyboardInterrupt:
            stop_msg = "\n=== Monitoring stopped by user ===\n"
            print(stop_msg, end="")
            log_f.write(stop_msg)
            log_f.flush()
            if ser:
                ser.close()
            log_f.close()
            break

if __name__ == "__main__":
    monitor_serial()
