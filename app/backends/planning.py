from app.planner import build_plan

def plan_interface(
    router,
    desired_interface,
    get_interface_state,
):
    """Build a Part 2 plan from backend status."""
    response = get_interface_state(router, desired_interface["name"])
    current_interface = None

    if response["status"] == "error":
        return response

    if response["result"] == "not_found":
        current_interface = None

    if response["result"] == "found":
        current_interface = response["interface"]

    return build_plan(desired_interface, current_interface)
