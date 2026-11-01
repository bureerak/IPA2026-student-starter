MANAGED_FIELDS = ("ipv4","description","admin_state")

def build_plan(desired_interface, current_interface):
    """
    Compare desired interface state with normalized current state
    and return a plan according to specs/plan-spec-v1.md.
    """
    # TODO: implement

    if current_interface is None:
        changed = {}
        for field in MANAGED_FIELDS:
            changed[field] = {'to': desired_interface[field]}
        return {
        "status": "ok",
        "result": "planned",
        "operation": "create",
        "changes": changed
        }

    changed = {}
    for field in MANAGED_FIELDS:
        if desired_interface[field] != current_interface[field]:
            changed[field] = {'from': current_interface[field], 'to': desired_interface[field]}

    if not changed:
        return {
            "status": "ok",
            "result": "planned",
            "operation": "no_change",
            "changes": {}
        }

    return {
        "status": "ok",
        "result": "planned",
        "operation": "update",
        "changes": changed
    }
