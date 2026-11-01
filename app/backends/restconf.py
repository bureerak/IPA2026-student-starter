import requests
from ipaddress import IPv4Interface
from app.backends import planning

def get_interface_state(
    router,
    interface_name,
    http_get=None,
):
    """Return normalized interface status using RESTCONF."""
    if http_get is None:
        http_get = requests.get

    url = f"https://{router}/restconf/data/ietf-interfaces:interfaces/interface={interface_name}"

    try:
        response = http_get(url)
    except PermissionError as e:
        return {"status" : "error", "result" : "authentication_failed"}
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionError) as e:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception as e:
        return {"status" : "error", "result" : "backend_failed"}

    if response.status_code == 404:
        return {"status" : "ok", "result" : "not_found", "interface" : None}

    if response.status_code == 200:
        inner = response.json()["ietf-interfaces:interface"]

        ipv4 = inner["ietf-ip:ipv4"]["address"][0]["ip"]
        mask = inner["ietf-ip:ipv4"]["address"][0]["netmask"]

        resp = {
            "name": inner["name"],
            "description": inner.get("description"),
            "admin_state": "up" if inner.get("enabled") else "down",
            "ipv4": IPv4Interface(f"{ipv4}/{mask}").with_prefixlen
        }
        return {"status" : "ok", "result" : "found", "interface" : resp}

    if response.status_code == 401 or response.status_code == 403:
        return {"status" : "error", "result" : "authentication_failed"}

    return {"status" : "error", "result" : "backend_failed"}


def plan_interface(
    router,
    desired_interface,
    http_get=None,
):
    """Return create/update/no_change plan using RESTCONF status."""
    def wrap_get_interface_state(router, interface_name):
        return get_interface_state(router, interface_name, http_get=http_get)
    return planning.plan_interface(router, desired_interface, wrap_get_interface_state)


def apply_interface(
    router,
    desired_interface,
    http_put=None,
):
    """Apply complete desired interface state using RESTCONF."""
    if http_put is None:
        http_put = requests.put

    name = int(desired_interface["name"][len("Loopback"):])

    url = f"https://{router}/restconf/data/Cisco-IOS-XE-native:native/interface/Loopback={name}"

    payload = {
        "Cisco-IOS-XE-native:Loopback": {
            "name": name,
            "description": desired_interface.get("description"),
            "ip": {
                "address": {
                    "primary": {
                        "address": str(IPv4Interface(desired_interface["ipv4"]).ip),
                        "mask": str(IPv4Interface(desired_interface["ipv4"]).netmask)
                    }
                }
            }
        }
    }

    if desired_interface["admin_state"] == "down":
        payload["Cisco-IOS-XE-native:Loopback"]["shutdown"] = [None]

    try:
        response = http_put(url, json=payload)
    except PermissionError as e:
        return {"status" : "error", "result" : "authentication_failed"}
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, ConnectionError) as e:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception as e:
        return {"status" : "error", "result" : "backend_failed"}

    if response.status_code in [200, 201, 204]:
        return {"status" : "ok", "result" : "applied"}

    if response.status_code == 401 or response.status_code == 403:
        return {"status" : "error", "result" : "authentication_failed"}

    return {"status" : "error", "result" : "backend_failed"}
