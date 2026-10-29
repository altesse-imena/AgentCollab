import ipaddress
import re
import subprocess

HOSTNAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?")


def _valid(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return len(host) <= 253 and bool(HOSTNAME.fullmatch(host))


def ping(host: str) -> bool:
    if not _valid(host):
        raise ValueError(f"invalid host: {host!r}")
    result = subprocess.run(["ping", "-c", "1", host], capture_output=True)
    return result.returncode == 0
