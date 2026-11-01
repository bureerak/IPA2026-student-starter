"""Part 4 student implementation."""

import yaml

from app.core import validate_request

from app.dispatcher import dispatch_request

from app.request_handler import validate_webex_envelope

def process_request(mentioned_people, attachment_path, bot_person_id):
    envelope_error = validate_webex_envelope(
        mentioned_people,
        attachment_path,
        bot_person_id,
    )

    if envelope_error is not None:
        return envelope_error

    try:
        with open(attachment_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError:
        return {"status": "error", "result": "invalid_yaml"}
    except OSError:
        return {"status": "error", "result": "invalid_yaml"}

    if not isinstance(data, dict):
        return {"status": "error", "result": "invalid_yaml"}

    response = validate_request(data)

    if response["result"] != "accepted":
        return response

    return dispatch_request(data)
