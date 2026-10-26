#!/bin/sh
# Hotspot failover: bring B860H-AP up when no working uplink, down when uplink returns.
# Runs every minute via hotspot-failover.timer. AP on wlan1, STA stays on wlan0.
LOG=/var/log/hotspot-failover.log
STATE=/run/hotspot-failover.count
AP_IFACE=wlan1
CONN=B860H-AP

GW=$(ip route show default 2>/dev/null | awk '/^default/ {print $3; exit}')
UP=0
if [ -n "$GW" ] && ping -c1 -W3 "$GW" >/dev/null 2>&1; then
  UP=1
fi

CNT=$(cat "$STATE" 2>/dev/null || echo 0)
case "$CNT" in ''|*[!0-9]*) CNT=0 ;; esac
if [ "$UP" = 1 ]; then
  CNT=0
else
  CNT=$((CNT + 1))
fi
echo "$CNT" > "$STATE"

AP_UP=0
if nmcli -t -f DEVICE,STATE dev status 2>/dev/null | grep -q "^${AP_IFACE}:connected"; then
  AP_UP=1
fi

if [ "$CNT" -ge 2 ] && [ "$AP_UP" = 0 ]; then
  echo "$(date '+%F %T') no uplink ${CNT}x in a row, bringing AP up" >>"$LOG"
  /bin/nmcli con up "$CONN" >/dev/null 2>&1
elif [ "$UP" = 1 ] && [ "$AP_UP" = 1 ]; then
  echo "$(date '+%F %T') uplink back, bringing AP down" >>"$LOG"
  /bin/nmcli con down "$CONN" >/dev/null 2>&1
fi
exit 0
