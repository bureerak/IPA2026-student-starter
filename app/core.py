import yaml

ALLOWED_ROUTERS = {
        "10.0.29.101",
        "10.0.29.102",
        "10.0.29.103",
        "10.0.29.104",
        "10.0.29.105"
    }

METHODS = {
    "restconf": ["status","plan","apply"],
    "netconf": ["status","plan","apply"],
    "ansible": ["apply"],
    "netmiko-textfsm": ["status","delete"]
}

def validate_request(data):
    """
    Validate one IPA2026 desired-state request.

    Return a response dictionary according to
    specs/response-spec-v1.md.
    """
    # TODO: implement

    if type(data.get("version")) is not int or data.get("version") != 1:
        return {
            "status": "error",
            "result": "invalid_version",
        }

    if data.get("router") is None:
        return {
            "status": "error",
            "result": "missing_router",
        }

    if data.get("router") not in ALLOWED_ROUTERS:
        return {
            "status": "error",
            "result": "invalid_router",
        }

    if data.get("method") is None:
        return {
            "status": "error",
            "result": "missing_method",
        }

    if data.get("method") not in METHODS:
        return {
            "status": "error",
            "result": "invalid_method",
        }

    if data.get("action") is None:
        return {
            "status": "error",
            "result": "missing_action",
        }

    if data.get("action") not in METHODS.get(data.get("method")):
        return {
            "status": "error",
            "result": "invalid_action",
        }

    if data.get("desired") is None:
        return {
            "status": "error",
            "result": "missing_desired",
        }

    if data.get("desired").get("interface") is None:
        return {
            "status": "error",
            "result": "missing_interface",
        }

    if data.get("desired").get("interface").get("name") is None:
        return {
            "status": "error",
            "result": "missing_interface_name",
        }

    if data.get("action") in ("plan", "apply"):
        interface = data.get("desired").get("interface")

        if interface.get("ipv4") is None:
            return {
                "status": "error",
                "result": "missing_ipv4",
            }

        if interface.get("description") is None:
            return {
                "status": "error",
                "result": "missing_description",
            }

        if interface.get("admin_state") is None:
            return {
                "status": "error",
                "result": "missing_admin_state",
            }

        if interface.get("admin_state") not in ("up", "down"):
            return {
                "status": "error",
                "result": "invalid_admin_state",
            }

    return {
        "status": "ok",
        "result": "accepted",
    }


def process_request_file(path):
    """
    Read a YAML request file, validate it,
    and return a response dictionary.
    """
    # TODO: implement

    try:
        with open(path, 'r') as f:
                data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return {
            "status": "error",
            "result": "invalid_yaml",
        }
    
    if not isinstance(data, dict):
        return {
            "status": "error",
            "result": "invalid_yaml",
        }

    return validate_request(data)
