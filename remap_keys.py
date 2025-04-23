#!/usr/bin/env python3

import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


def read_file(file_path: Union[str, Path]) -> Optional[str]:
    """Get the value of a file."""
    file_path = Path(file_path)
    try:
        return file_path.read_text().strip()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except PermissionError:
        print(f"Permission denied to read {file_path}")
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def get_device(event: str, path: str) -> Optional[str]:
    device_path = Path("/sys/class/input") / event / "device" / path
    return read_file(device_path)


def get_device_name(event: str) -> Optional[str]:
    """Get the device name for the event."""
    return get_device(event, "name")


def get_device_phys(event: str) -> Optional[str]:
    """Get the device physical path for the event."""
    return get_device(event, "phys")


def get_device_ev(event: str) -> Optional[str]:
    """Get the device event capabilities for the event."""
    return get_device(event, "capabilities/ev")


def get_system_vendor() -> Optional[str]:
    """Get the firmware-provided vendor string of the device."""
    return read_file("/sys/class/dmi/id/sys_vendor")


def validate_event_device(event: str) -> bool:
    """Validate if the provided event device exists and is properly formatted."""
    # Check if the event name is valid
    if not re.match(r"^event\d+$", event):
        print(
            f"Invalid event device format: {event}. Expected format: eventX where X is a number."
        )
        return False

    # Check if the device exists
    if not Path(f"/sys/class/input/{event}").exists():
        print(f"Event device not found: {event}")
        return False

    return True


def list_available_devices() -> List[Dict[str, str]]:
    """List all available input devices."""
    devices = []
    input_dir = Path("/sys/class/input")

    if not input_dir.exists():
        print("Input device directory not found.")
        return devices

    for device_path in input_dir.glob("event*"):
        event = device_path.name
        name = get_device_name(event)
        phys = get_device_phys(event)

        if name:
            devices.append({"event": event, "name": name, "phys": phys or "N/A"})

    return devices


def get_hwdb_evdev_entry(
    name: str,
    phys: str,
    ev: str,
    vendor: str,
    key_code_mapping: Dict[str, str],
) -> str:
    """Get the hwdb evdev entry for device."""
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


def write_hwdb_entry(
    hwdb_entry: Optional[str],
    output_file: str,
) -> bool:
    """Write the hwdb entry to the hwdb file."""
    if not hwdb_entry:
        return False

    # Create the hwdb entry to the hwdb file
    try:
        with open(output_file, "w") as f:
            f.write(hwdb_entry)
    except FileNotFoundError:
        print(f"File not found: {output_file}")
        return False
    except PermissionError:
        print(f"Permission denied to write {output_file}")
        return False
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False

    print(f"Written hwdb entry to {output_file}")
    return True


def main() -> int:
    import argparse

    def parse_mapping(value: str) -> tuple:
        """Parse the mapping from the command line."""
        try:
            key, value = value.split("=")
            return (key, value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid mapping: {value}")

    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="Remap keys for a device using systemd's hardware database (hwdb)."
    )

    # Add an argument group for the main mode of operation
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--list-devices", action="store_true", help="List all available input devices."
    )
    mode_group.add_argument(
        "device",
        type=str,
        nargs="?",
        help="The device to remap keys for (e.g. eventX).",
    )

    # Add arguments for key mapping
    parser.add_argument(
        "--mapping",
        type=parse_mapping,
        action="append",
        metavar="KEY=VALUE",
        help="The key code mapping to use (e.g. <hex scan code>=<key code identifier>).",
    )

    # Add file and operation arguments
    parser.add_argument(
        "--output",
        type=str,
        default="99-keyboard.hwdb",
        help="The output hwdb file (default: 99-keyboard.hwdb).",
    )

    args = parser.parse_args()

    # Handle listing devices mode
    if args.list_devices:
        devices = list_available_devices()
        if not devices:
            print("No input devices found.")
            return 1

        # Sort devices by event number
        devices.sort(key=lambda x: int(x["event"][5:]))

        print("Available input devices:")
        for device in devices:
            print(f"  {device['event']}: {device['name']} ({device['phys']})")
        return 0

    # Check if a device was specified
    if not args.device:
        parser.print_help()
        return 1

    # Validate the event device
    event = args.device
    if not validate_event_device(event):
        return 1

    # Check if mapping was provided
    if not args.mapping and not args.list_devices:
        print("Error: At least one --mapping is required when specifying a device.")
        return 1

    # Get required device information
    name = get_device_name(event)
    if not name:
        print(f"Failed to get device name for event {event}")
        return 1

    phys = get_device_phys(event)
    if not phys:
        print(f"Failed to get device physical path for event {event}")
        return 1

    ev = get_device_ev(event)
    if not ev:
        print(f"Failed to get device event capabilities for event {event}")
        return 1

    vendor = get_system_vendor()
    if not vendor:
        print(f"Failed to get system vendor")
        return 1

    # Create the key code mapping
    key_code_mapping = {}
    if args.mapping:
        for mapping in args.mapping:
            key, value = mapping
            key_code_mapping[key] = value

    # Get the hwdb evdev entry for the device
    hwdb_entry = get_hwdb_evdev_entry(name, phys, ev, vendor, key_code_mapping)
    if not hwdb_entry:
        print(f"Failed to create hwdb entry for event {event}")
        return 1

    print(f"HWDB entry:\n{hwdb_entry}")

    # Write the hwdb entry to the hwdb file
    if not write_hwdb_entry(hwdb_entry, args.output):
        return 1

    # Print next commands to run
    print("\nRun the following commands to update the hwdb:")
    print(f"sudo cp {args.output} /etc/udev/hwdb.d/")
    print("sudo systemd-hwdb update")
    print(f"sudo udevadm trigger --sysname-match={args.device}")
    print(f"udevadm info /dev/input/{args.device}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
