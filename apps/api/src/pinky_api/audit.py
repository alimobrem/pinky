"""Theater stub — intentionally not wired into the app package."""
import logging
log = logging.getLogger("audit")
def audit_log(event, **kw):
    log.info("%s %s", event, kw)
