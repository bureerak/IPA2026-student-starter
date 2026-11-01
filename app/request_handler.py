from app.core import  process_request_file

def validate_webex_envelope(
    mentioned_people,
    attachment_path,
    bot_person_id,
):
    """
    Validate the target bot's actual mention and YAML attachment.
    Return an error response, or None when the envelope is valid.
    """
    # TODO: implement according to the published specifications

    bot_id_ok = not ( bot_person_id == "" or not isinstance(bot_person_id, str) )
    mentioned_is_list = isinstance(mentioned_people, list)

    if not (bot_id_ok and mentioned_is_list and bot_person_id in mentioned_people):
        return {
            "status": "error",
            "result": "missing_bot_mention",
        }

    if not attachment_path:
        return {
            "status": "error",
            "result": "no_yaml",
        }

    return None


def handle_webex_request(
    mentioned_people,
    attachment_path,
    bot_person_id,
):
    """
    Validate the envelope, then validate the attached YAML request.
    Return a response dictionary. Do not dispatch to a router.
    """
    # TODO: implement according to the published specifications

    envelope_error = validate_webex_envelope(mentioned_people, attachment_path, bot_person_id)

    if envelope_error:
        return envelope_error

    # TODO: Validate the attached YAML request
    return process_request_file(attachment_path)
