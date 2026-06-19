import re

from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)

# DRF's built-in parse_rate only supports "N/<single-unit>" (e.g. "5/min").
# FR-026 needs "N per M minutes/hours" windows, so we extend the rate syntax
# to "N/Mmin", "N/Mhour" etc. and parse it ourselves.
_RATE_RE = re.compile(r"^(\d+)/(\d*)(s|sec|second|m|min|minute|h|hour|d|day)s?$")
_UNIT_SECONDS = {
    "s": 1,
    "sec": 1,
    "second": 1,
    "m": 60,
    "min": 60,
    "minute": 60,
    "h": 3600,
    "hour": 3600,
    "d": 86400,
    "day": 86400,
}


class _WindowRateThrottle(SimpleRateThrottle):
    def parse_rate(self, rate):
        if rate is None:
            return (None, None)
        match = _RATE_RE.match(rate)
        if not match:
            return super().parse_rate(rate)
        num, count, unit = match.groups()
        count = int(count) if count else 1
        return int(num), count * _UNIT_SECONDS[unit]


class AccountRateThrottle(_WindowRateThrottle):
    """Per-account throttle keyed on the submitted email/identifier.

    Used on endpoints where the requester isn't authenticated yet, so we key
    on the request body instead of request.user.
    """

    def get_cache_key(self, request, view):
        identifier = (request.data.get("email") or "").strip().lower()
        if not identifier:
            return None
        return self.cache_format % {"scope": self.scope, "ident": identifier}


class IPRateThrottle(_WindowRateThrottle, AnonRateThrottle):
    pass


class AuthenticatedUserRateThrottle(_WindowRateThrottle, UserRateThrottle):
    """Keyed on request.user — for endpoints that require authentication."""


class RegisterIPThrottle(IPRateThrottle):
    scope = "register"
    rate = "5/5min"


class RegisterAccountThrottle(AccountRateThrottle):
    scope = "register"
    rate = "5/5min"


class LoginIPThrottle(IPRateThrottle):
    scope = "login"
    rate = "5/5min"


class LoginAccountThrottle(AccountRateThrottle):
    scope = "login"
    rate = "5/5min"


class ForgotPasswordIPThrottle(IPRateThrottle):
    scope = "forgot-password"
    rate = "3/15min"


class ForgotPasswordAccountThrottle(AccountRateThrottle):
    scope = "forgot-password"
    rate = "3/15min"


class VerifyResetTokenIPThrottle(IPRateThrottle):
    scope = "verify-reset-token"
    rate = "5/15min"


class SendVerificationEmailUserThrottle(AuthenticatedUserRateThrottle):
    scope = "send-verification-email"
    rate = "3/hour"
