import json
import os
import subprocess

from ipaddress import IPv4Interface
from pathlib import Path

ANSIBLE_DIR = Path(__file__).resolve().parents[2] / "ansible"

PLAYBOOK = ANSIBLE_DIR / "apply_interface.yml"

INVENTORY = ANSIBLE_DIR / "inventory.ini"

PLAYBOOK_TIMEOUT = 120

AUTH_MARKERS = (
    "authentication fail",
    "permission denied",
    "incorrect password",
    "authorization",
)

CONNECTION_MARKERS = (
    "unreachable",
    "timed out",
    "timeout",
    "connection refused",
    "no route to host",
)


def _default_run_playbook(variables):
    """Real Ansible runner, matching the run_playbook(variables) contract."""
    environment = os.environ.copy()
    environment.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")
    environment.setdefault("ANSIBLE_RETRY_FILES_ENABLED", "False")

    completed = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(PLAYBOOK),
            "-e",
            json.dumps(variables),
        ],
        capture_output=True,
        text=True,
        timeout=PLAYBOOK_TIMEOUT,
        env=environment,
    )

    if completed.returncode == 0:
        return

    output = f"{completed.stdout}\n{completed.stderr}".lower()

    if any(marker in output for marker in AUTH_MARKERS):
        raise PermissionError("ansible rejected the router credentials")

    if any(marker in output for marker in CONNECTION_MARKERS):
        raise ConnectionError("ansible could not reach the router")

    raise RuntimeError("ansible-playbook failed")


def apply_interface(
    router,
    desired_interface,
    run_playbook=None,
):
    """Apply complete desired interface state using Ansible."""
    if run_playbook is None:
        run_playbook = _default_run_playbook

    ipv4 = IPv4Interface(desired_interface["ipv4"])

    variables = {
        "router": router,
        "interface_name": desired_interface["name"],
        "description": desired_interface["description"],
        "ipv4_address": str(ipv4.ip),
        "netmask": str(ipv4.netmask),
        "shutdown": desired_interface["admin_state"] == "down",
    }

    try:
        run_playbook(variables)
    except PermissionError:
        return {"status": "error", "result": "authentication_failed"}
    except ConnectionError:
        return {"status": "error", "result": "connection_failed"}
    except Exception:
        return {"status": "error", "result": "backend_failed"}

    return {"status": "ok", "result": "applied"}
