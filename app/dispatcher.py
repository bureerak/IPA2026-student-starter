"""Part 4 student implementation."""

from app.backends import ansible, netconf, netmiko_textfsm, restconf

TABLE = {
        ("restconf", "status") : (restconf, "get_interface_state"),
        ("restconf", "plan") : (restconf, "plan_interface"),
        ("restconf", "apply") : (restconf, "apply_interface"),
        ("netconf", "status") : (netconf, "get_interface_state"),
        ("netconf", "plan") : (netconf, "plan_interface"),
        ("netconf", "apply") : (netconf, "apply_interface"),
        ("ansible", "apply") : (ansible, "apply_interface"),
        ("netmiko-textfsm", "status") : (netmiko_textfsm, "get_interface_state"),
        ("netmiko-textfsm", "delete") : (netmiko_textfsm, "delete_interface"),
    }

def dispatch_request(data):
    # TODO: implement according to Part 4 specification
    method = data["method"]
    action = data["action"]
    router = data["router"]
    interface = data["desired"]["interface"]

    module, function_name = TABLE[(method, action)]
    function = getattr(module, function_name)
    if action in ["status", "delete"]:
        return function(router, interface["name"])
    return function(router, interface)
