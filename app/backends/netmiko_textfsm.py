import os

from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from netmiko.utilities import get_structured_data_textfsm

CONNECT_TIMEOUT = 10

# Netmiko raises its own exception classes, so each one is grouped with the
# built-in the public tests use for the same backend error code.
AUTH_ERRORS = (PermissionError, NetmikoAuthenticationException)

CONNECTION_ERRORS = (ConnectionError, NetmikoTimeoutException)


def _connect(router):
    return ConnectHandler(
        device_type="cisco_ios",
        host=router,
        username=os.getenv("ROUTER_USER", ""),
        password=os.getenv("ROUTER_PASS", ""),
        conn_timeout=CONNECT_TIMEOUT,
    )


def _parsed(output):
    """TextFSM returns the raw string when no template matched."""
    if not isinstance(output, list):
        raise RuntimeError("TextFSM did not parse the CLI output")
    return output


def _is_cli_error(raw_output):
    """IOS answers an unknown interface with an invalid-input marker."""
    lowered = raw_output.lower()
    return "invalid input" in lowered or "% incomplete" in lowered


def _default_netmiko_get(router, interface_name):
    """Real read path, matching netmiko_get(router, interface_name)."""
    show_ip = f"show ip interface {interface_name}"

    with _connect(router) as connection:
        # Read this one raw first: an absent interface produces an IOS error
        # banner that TextFSM refuses to parse, and that is "not found" here,
        # not a backend failure.
        raw_ip = connection.send_command(show_ip)

        descriptions = connection.send_command(
            "show interfaces description",
            use_textfsm=True,
        )

    if _is_cli_error(raw_ip):
        ip_info = []
    else:
        ip_info = _parsed(
            get_structured_data_textfsm(
                raw_ip,
                platform="cisco_ios",
                command=show_ip,
            )
        )

    return ip_info, _parsed(descriptions)


def _default_netmiko_delete(router, interface_name):
    """Real delete path, returning "deleted" or "not_found"."""
    before = get_interface_state(router, interface_name, _default_netmiko_get)

    if before.get("status") == "error":
        raise RuntimeError(before.get("result"))

    if before.get("result") == "not_found":
        return "not_found"

    with _connect(router) as connection:
        connection.send_config_set([f"no interface {interface_name}"])

    after = get_interface_state(router, interface_name, _default_netmiko_get)

    if after.get("result") != "not_found":
        raise RuntimeError("interface still present after delete")

    return "deleted"


def get_interface_state(
    router,
    interface_name,
    netmiko_get=None,
):
    """Return normalized interface status using Netmiko + TextFSM."""
    if netmiko_get is None:
        netmiko_get = _default_netmiko_get

    try:
        ip_info, descriptions = netmiko_get(router, interface_name)
    except AUTH_ERRORS:
        return {"status" : "error", "result" : "authentication_failed"}
    except CONNECTION_ERRORS:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception:
        return {"status" : "error", "result" : "backend_failed"}

    if ip_info is None or not ip_info:
        return {"status" : "ok", "result" : "not_found", "interface" : None}

    info = ip_info[0]

    short_name = info["interface"].replace("Loopback", "Lo")

    description = None
    for entry in descriptions:
        if entry["port"] == short_name:
            description = entry["description"]
            break

    resp = {
        "name": info["interface"],
        "description": description,
        "admin_state": "down" if info["link_status"] == "administratively down" else "up",
        "ipv4": f'{info["ip_address"][0]}/{info["prefix_length"][0]}'
    }

    return {"status" : "ok", "result" : "found", "interface" : resp}


def delete_interface(
    router,
    interface_name,
    netmiko_delete=None,
):
    """Delete an interface using Netmiko."""
    if netmiko_delete is None:
        netmiko_delete = _default_netmiko_delete

    try:
        result = netmiko_delete(router, interface_name)
    except AUTH_ERRORS:
        return {"status" : "error", "result" : "authentication_failed"}
    except CONNECTION_ERRORS:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception:
        return {"status" : "error", "result" : "backend_failed"}

    if result == "not_found":
        return {"status" : "ok", "result" : "not_found", "interface" : None}

    return {"status" : "ok", "result" : "deleted"}