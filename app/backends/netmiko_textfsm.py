def get_interface_state(
    router,
    interface_name,
    netmiko_get=None,
):
    """Return normalized interface status using Netmiko + TextFSM."""
    if netmiko_get is None:
        pass

    try:
        ip_info, descriptions = netmiko_get(router, interface_name)
    except PermissionError as e:
        return {"status" : "error", "result" : "authentication_failed"}
    except ConnectionError as e:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception as e:
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
        pass

    try:
        result = netmiko_delete(router, interface_name)
    except PermissionError as e:
        return {"status" : "error", "result" : "authentication_failed"}
    except ConnectionError as e:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception as e:
        return {"status" : "error", "result" : "backend_failed"}

    if result == "not_found":
        return {"status" : "ok", "result" : "not_found", "interface" : None}

    return {"status" : "ok", "result" : "deleted"}