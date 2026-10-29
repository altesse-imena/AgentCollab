import subprocess


def ping(host: str) -> bool:
    result = subprocess.run(f"ping -c 1 {host}", shell=True, capture_output=True)
    return result.returncode == 0
