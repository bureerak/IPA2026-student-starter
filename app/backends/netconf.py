from ncclient import manager
from ipaddress import IPv4Interface
from app.backends import planning
import xml.etree.ElementTree as ET


NS = {
    "if": "urn:ietf:params:xml:ns:yang:ietf-interfaces",
    "ip": "urn:ietf:params:xml:ns:yang:ietf-ip",
}

def get_interface_state(
    router,
    interface_name,
    netconf_get_config=None,
):
    """Return normalized interface status using NETCONF."""

    if netconf_get_config is None:
        netconf_get_config = manager.connect

    xml_filter = f"""
    <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface>
            <name>{interface_name}</name>
        </interface>
    </interfaces>
    """

    try:
        xml_text = netconf_get_config(router, xml_filter)

    except PermissionError as e:
        return {"status" : "error", "result" : "authentication_failed"}
    except ConnectionError as e:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception as e:
        return {"status" : "error", "result" : "backend_failed"}

    root = ET.fromstring(xml_text)
    iface = root.find(".//if:interface", NS)

    if iface is None:
        return {"status" : "ok", "result" : "not_found", "interface" : None}

    name_el = iface.find("if:name", NS)
    desc_el = iface.find("if:description", NS)
    enabled_el = iface.find("if:enabled", NS)
    ip_el   = iface.find(".//ip:ip", NS)
    mask_el = iface.find(".//ip:netmask", NS)

    if name_el is None or enabled_el is None:
        return {"status" : "error", "result" : "backend_failed"}

    if desc_el is not None:
        description = desc_el.text
    else:
        description = None

    if enabled_el.text == "true":
        admin_state = "up"
    else:
        admin_state = "down"

    if ip_el is not None and mask_el is not None:
        ipv4 = ip_el.text
        mask = mask_el.text
        ipv4_with_prefix = IPv4Interface(f"{ipv4}/{mask}").with_prefixlen
    else:
        ipv4_with_prefix = None

    return {
        "status" : "ok",
        "result" : "found",
        "interface" : {
            "name": name_el.text,
            "description": description,
            "admin_state": admin_state,
            "ipv4": ipv4_with_prefix
        }
    }



def plan_interface(
    router,
    desired_interface,
    netconf_get_config=None,
):
    """Return create/update/no_change plan using NETCONF status."""
    def wrap_get_interface_state(router, interface_name):
        return get_interface_state(router, interface_name, netconf_get_config=netconf_get_config)
    return planning.plan_interface(router, desired_interface, wrap_get_interface_state)


def apply_interface(
    router,
    desired_interface,
    netconf_edit_config=None,
):
    """Apply complete desired interface state using NETCONF."""

    if netconf_edit_config is None:
        netconf_edit_config = manager.connect
        
    name = int(desired_interface["name"][len("Loopback"):])

    xml_payload = f"""
    <config
        xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
        xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">

        <native xmlns="http://cisco.com/ns/yang/Cisco-IOS-XE-native">
            <interface>
                <Loopback nc:operation="replace">
                    <name>{name}</name>
                    <description>{desired_interface.get("description", "")}</description>
                    <ip>
                        <address>
                            <primary>
                                <address>{IPv4Interface(desired_interface["ipv4"]).ip}</address>
                                <mask>{IPv4Interface(desired_interface["ipv4"]).netmask}</mask>
                            </primary>
                        </address>
                    </ip>
                    {"<shutdown/>" if desired_interface["admin_state"] == "down" else ""}
                </Loopback>
            </interface>
        </native>
    </config>
    """

    try:
        netconf_edit_config(router, xml_payload)
    except PermissionError as e:
        return {"status" : "error", "result" : "authentication_failed"}
    except ConnectionError as e:
        return {"status" : "error", "result" : "connection_failed"}
    except Exception as e:
        return {"status" : "error", "result" : "backend_failed"}

    return {"status" : "ok", "result" : "applied"}
