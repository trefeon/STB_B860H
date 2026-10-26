#!/bin/sh
# HDMI console power policy: no HOTPLUG display -> blank output + stop getty (light load).
# HDMI present -> unblank + ensure getty on tty1.
# NOTE: the meson driver reports status=connected even with no cable
# (video=...e forces the connector on), so presence is detected via EDID:
# an empty /sys/.../edid means no display is attached.
# Triggered by udev rule 99-hdmi-console.rules and hdmi-console-boot.service.
exec >>/var/log/hdmi-console.log 2>&1
if [ -s /sys/class/drm/card0-HDMI-A-1/edid ]; then
  ST=connected
else
  ST=disconnected
fi
echo "$(date '+%F %T') event status=$ST"
if [ "$ST" = connected ]; then
  echo 0 > /sys/class/graphics/fb0/blank 2>/dev/null
  /bin/systemctl start getty@tty1 &
else
  echo 1 > /sys/class/graphics/fb0/blank 2>/dev/null
  /bin/systemctl stop getty@tty1 &
fi
exit 0
