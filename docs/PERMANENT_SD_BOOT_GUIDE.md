# Permanent SD Card Auto-Boot Guide for ZTE B860H V1/V2

This guide outlines the permanent hardware modification required to make the ZTE B860H V1/V2 bootloader prioritize and boot from the MicroSD card automatically upon power connection, without needing to hold the physical recovery/power button.

---

## 1. Why Hardware Modification is Required
On Amlogic S905X devices with a failing internal eMMC:
1. **Low-Speed Read Success**: The internal eMMC boot sectors are still readable at very low speeds (100–400 kHz) by the SoC's BootROM. Thus, the BootROM always boots the vendor U-Boot from the internal flash first.
2. **High-Speed Bus Failure**: Once the vendor U-Boot starts, it attempts to initialize the full eMMC interface (higher speed and width). The dead/corrupted eMMC controller fails this stage (`MMC init failed`), causing U-Boot to default to its hardcoded boot command (`run storeboot`), which tries to load Android, fails, and reboots.
3. **Environment is Read-Only**: Because the eMMC is physically unresponsive to write commands, running U-Boot's `saveenv` to change the boot commands permanently fails.
4. **Conclusion**: To force the SoC's BootROM to skip the eMMC entirely and boot directly from your SD card's raw sectors (which contains our patched U-Boot), you must physically disable the eMMC clock (CLK) signal.

---

## 2. Hardware Mod Options

### Option A: Desolder the CLK Resistor (Recommended & Cleanest)
Amlogic boards route the clock signal from the CPU to the eMMC through a small series resistor (typically 33 ohms, labeled as `CLK` or located right next to the eMMC). Desoldering or removing this resistor physically disconnects the clock line, disabling the eMMC.

#### Step 1: Open the Casing
- Remove the rubber feet from the bottom of the TV box.
- Unscrew the screws underneath the feet.
- Use a plastic pry tool to open the plastic latches of the casing.
- Remove the heatsink if necessary.

#### Step 2: Locate the eMMC and CLK Resistor
- Locate the large square chip labeled **Samsung**, **SK Hynix**, **Toshiba**, or **Sandisk** (this is the eMMC).
- Look closely at the small resistors arrayed right next to the eMMC chip.
- On the **B860H V1/V2** boards (blue or green PCBs), there is a resistor labeled **R87** (often used as the short-pin recovery resistor) and a series of resistors directly adjacent to the eMMC chip pins.
- The CLK line trace runs through a resistor. In many B860H V1/V2 revisions, the CLK resistor is located near the eMMC and can be identified by the tiny `CLK` label printed on the silk screen, or by tracking the trace from the eMMC clock pad (pin `W6` under BGA153 package).
- *Common Revision Locations*:
  - **B860H V1 (Red/Blue board)**: The CLK resistor is usually a tiny black resistor situated in a group of 4-5 resistors directly adjacent to the eMMC chip edge.
  - **B860H V2 (Blue/Green board)**: It is situated close to the CPU heatsink corner.

#### Step 3: Remove the Resistor
- Using a fine-tip soldering iron or hot air rework station, desolder and remove the CLK resistor from the board.
- Alternatively, you can use a fine hobby knife (scalpel) to gently scratch and sever the thin CLK copper trace on the PCB leading to the resistor. (This is irreversible unless you solder a jumper wire later, so desoldering the resistor is preferred).

---

### Option B: Solder CLK to GND (Jumper Wire Method)
If you do not want to remove the resistor, you can solder a thin jumper wire to ground the CLK signal. This clamps the clock signal to 0V, making the eMMC invisible to the BootROM.

1. Locate the CLK test point or the side of the CLK resistor closest to the eMMC chip.
2. Solder a thin insulated copper wire (enameled jumper wire) from the CLK point.
3. Solder the other end of the wire to a Ground (GND) point on the board. (The metal outer casings of the USB ports, HDMI port, or the microSD slot are excellent ground points).
4. Secure the wire using a small drop of hot glue or kapton tape to prevent it from shorting other components.

---

## 3. Post-Mod Boot Behavior
Once the CLK line is disabled:
1. **Power Connected**: The SoC BootROM powers on and attempts to read the eMMC.
2. **Immediate Timeout**: Due to the missing clock signal, the eMMC does not respond. The BootROM immediately times out (~10ms).
3. **SD Card Failover**: The BootROM moves to `mmc0` (MicroSD slot).
4. **Bootloader Loaded**: The BootROM reads Sector 0/1 of the SD card, detects the injected `uboot_HG680P-sdboot.bin` signature, loads it into DRAM, and boots.
5. **Auto-Boot Armbian**: The SD card U-Boot starts, reads the custom `aml_autoscript` from the SD card BOOT partition, and boots Armbian Linux directly.

No buttons, serial consoles, or keyboards are required. The TV box behaves exactly like a standard single-board computer (like a Raspberry Pi), booting directly from the SD card.
