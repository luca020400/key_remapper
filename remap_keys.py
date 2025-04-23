#!/usr/bin/env python3

import os


def read_file(file_path: str) -> str:
    """Get the value of a file."""
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except PermissionError:
        print(f"Permission denied to read {file_path}")
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def get_device(event: str, path: str) -> str:
    return read_file(os.path.join("/sys/class/input", event, "device", path))


def get_device_name(event: str) -> str:
    """Get the device name for the event."""
    return get_device(event, "name")


def get_device_phys(event: str) -> str:
    """Get the device physical path for the event."""
    return get_device(event, "phys")


def get_device_ev(event: str) -> str:
    """Get the device event capabilities for the event."""
    return get_device(event, "capabilities/ev")


def get_system_vendor() -> str:
    """Get the firmware-provided vendor string of the device."""
    return read_file("/sys/class/dmi/id/sys_vendor")


def get_hwdb_evdev_entry(
    name: str, phys: str, ev: str, vendor: str, key_code_mapping: dict
) -> str:
    """Get the hwdb evdev entry for device

    #  - Extended input driver device name, properties and DMI data match:
    #      evdev:name:<input device name>:phys:<phys>:ev:<ev>:dmi:bvn*:bvr*:bd*:svn<vendor>:pn*
    #    <input device name> is the name device specified by the
    #    driver, <phys> is the physical-device-path, "cat
    #    /sys/class/input/input?/phys", <ev> is the event bitmask, "cat
    #    /sys/class/input/input?/capabilities/ev" and <vendor> is the
    #    firmware-provided string exported by the kernel DMI modalias,
    #    see /sys/class/dmi/id/modalias.

    """
    if not name or not phys or not ev or not vendor:
        return None

    # Create the hwdb entry
    hwdb_entry = (
        f"evdev:name:{name}:phys:{phys}:ev:{ev}:dmi:bvn*:bvr*:bd*:svn{vendor}:pn*\n"
    )

    # Add the mapping as KEYBOARD_KEY_
    for key, value in key_code_mapping.items():
        # Add the mapping to the hwdb entry
        hwdb_entry += f" KEYBOARD_KEY_{key}={value}\n"

    return hwdb_entry


def write_hwdb_entry(hwdb_entry: str) -> None:
    """Write the hwdb entry to the hwdb file."""
    if not hwdb_entry:
        return

    # Get the hwdb file path
    hwdb_file = "99-keyboard.hwdb"

    # Create the hwdb entry to the hwdb file
    try:
        with open(hwdb_file, "w") as f:
            f.write(hwdb_entry)
    except FileNotFoundError:
        print(f"File not found: {hwdb_file}")
    except PermissionError:
        print(f"Permission denied to write {hwdb_file}")
    except Exception as e:
        print(f"Error writing {hwdb_file}: {e}")
        return None

    print(f"Written hwdb entry to {hwdb_file}")


if __name__ == "__main__":
    import argparse

    def parse_mapping(value: str) -> tuple:
        """Parse the mapping from the command line."""
        try:
            key, value = value.split("=")
            return (key, value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid mapping: {value}")

    # Create the argument parser
    parser = argparse.ArgumentParser(description="Remap keys for a device.")
    parser.add_argument(
        "device",
        type=str,
        help="The device to remap keys for (e.g. eventX).",
    )
    parser.add_argument(
        "--mapping",
        type=parse_mapping,
        action="append",
        required=True,
        metavar="KEY=VALUE",
        help="The key code mapping to use (e.g. <hex scan code>=<key code identifier>).",
    )

    args = parser.parse_args()

    # Get required device information
    event = args.device

    name = get_device_name(event)
    if not name:
        print(f"Failed to get device name for event {event}")
        exit(1)

    phys = get_device_phys(event)
    if not phys:
        print(f"Failed to get device physical path for event {event}")
        exit(1)

    ev = get_device_ev(event)
    if not ev:
        print(f"Failed to get device event capabilities for event {event}")
        exit(1)

    vendor = get_system_vendor()
    if not vendor:
        print(f"Failed to get system vendor")
        exit(1)

    # Create the key code mapping
    key_code_mapping = {}
    if args.mapping:
        for mapping in args.mapping:
            key, value = mapping
            key_code_mapping[key] = value

    # Get the hwdb evdev entry for the product
    hwdb_entry = get_hwdb_evdev_entry(name, phys, ev, vendor, key_code_mapping)
    if not hwdb_entry:
        print(f"Failed to create hwdb entry for event {event}")
        exit(1)

    print(f"HWDB entry:\n{hwdb_entry}")

    # Write the hwdb entry to the hwdb file
    write_hwdb_entry(hwdb_entry)

    # Print next commands to run
    print("Run the following commands to update the hwdb:")
    print("sudo cp 99-keyboard.hwdb /etc/udev/hwdb.d/")
    print("sudo systemd-hwdb update")
    print(f"sudo udevadm trigger --sysname-match={args.device}")
    print(f"udevadm info /dev/input/{args.device}")
