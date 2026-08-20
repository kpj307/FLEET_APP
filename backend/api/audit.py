import logging

audit_logger = logging.getLogger("api.audit")


def log_audit_event(
    *,
    event: str,
    request=None,
    user=None,
    organization=None,
    success=True,
    **extra,
):
    """
    Write a structured audit event.

    Never pass passwords, tokens, API keys, payment signatures,
    or other secrets through extra.
    """

    payload = {
        "event": event,
        "success": success,
    }

    if request is not None:
        payload["request_id"] = getattr(request, "request_id", None)
        payload["method"] = request.method
        payload["path"] = request.path

    if user is not None and getattr(user, "is_authenticated", False):
        payload["user_id"] = user.pk

    if organization is not None:
        payload["organization_id"] = getattr(organization, "pk", None)

    payload.update(extra)

    if success:
        audit_logger.info("Audit event", extra=payload)
    else:
        audit_logger.warning("Audit event", extra=payload)