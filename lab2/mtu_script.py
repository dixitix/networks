import click
import subprocess
import socket
import platform
import sys

MIN_PACKET_SIZE = 1
INITIAL_MAX_PACKET_SIZE = 1024
HEADER_SIZE = 28

ERROR_MESSAGES = {
    "darwin": "Message too long",
    "linux": "Packet needs to be fragmented but DF set.",
    "windows": "Packet needs to be fragmented"
}

def get_system():
    return platform.system().lower()

def build_ping_command(system, host, packet_size):
    commands = {
        "darwin": f"ping {host} -D -s {packet_size} -c 1",
        "linux": f"ping {host} -c 1 -M do -s {packet_size}",
        "windows": f"ping {host} -n 1 -f -l {packet_size}",
    }
    if system not in commands:
        raise Exception(f"Unsupported system: {system}")
    return commands[system]

def execute_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    stdout, _ = process.communicate()
    return process.returncode, stdout

def check_host_availability(host):
    command = f"ping {host} -c 1"
    returncode, _ = execute_command(command)
    return returncode == 0

def execute_ping_command(system, host, packet_size):
    command = build_ping_command(system, host, packet_size)
    returncode, stdout = execute_command(command)

    error_message = ERROR_MESSAGES.get(system)
    if error_message and error_message.encode() in stdout:
        return False
    return returncode == 0

def find_max_packet_size(system, host, min_size, max_size):
    while min_size < max_size:
        mid_size = (min_size + max_size + 1) // 2
        if not execute_ping_command(system, host, mid_size):
            max_size = mid_size - 1
        else:
            min_size = mid_size
    return min_size

def calculate_mtu(system, host):
    if not check_host_availability(host):
        print(f"Host {host} is unreachable.", file=sys.stderr)
        exit(1)

    max_size = INITIAL_MAX_PACKET_SIZE
    mtu = max_size
    while mtu == max_size:
        max_size *= 2
        mtu = find_max_packet_size(system, host, MIN_PACKET_SIZE, max_size)
    mtu += HEADER_SIZE
    return mtu

@click.command()
@click.option("--host", required=True, help="Host address.")
def find_mtu(host):
    try:
        socket.gethostbyname(host)
    except socket.error:
        print(f"Invalid host argument: {host}", file=sys.stderr)
        exit(1)

    system = get_system()
    try:
        mtu = calculate_mtu(system, host)
        if mtu > 0:
            print(f"MTU: {mtu} bytes", flush=True)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        exit(1)

if __name__ == "__main__":
    find_mtu()