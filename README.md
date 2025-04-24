# Key Remapper

A utility for remapping key events using systemd's hardware database (hwdb).

# Example Usage

Remapping Lenovo Quick Clean keys on a ThinkPad P16s Gen2:

```bash
./remap_keys.py --mapping 4b=prog1 --mapping 4c=prog2 --mapping 4d=prog3 event13
```

# Output

```
HWDB entry:
evdev:name:ThinkPad Extra Buttons:phys:thinkpad_acpi/input0:ev:33:dmi:bvn*:bvr*:bd*:svnLENOVO:pn*
 KEYBOARD_KEY_4b=prog1
 KEYBOARD_KEY_4c=prog2
 KEYBOARD_KEY_4d=prog3

Written hwdb entry to 99-keyboard.hwdb
Run the following commands to update the hwdb:
sudo cp 99-keyboard.hwdb /etc/udev/hwdb.d/
sudo systemd-hwdb update
sudo udevadm trigger --sysname-match=event13
udevadm info /dev/input/event13
```

# List All Available Input Devices

To list all available input devices, use the following command:

```bash
./remap_keys.py --list-devices
```

# Helpful Commands

- Get scan codes: `sudo evtest /dev/input/event13`
- Get key code identifiers: `less /usr/include/linux/input-event-codes.h`
