"""Prometheus metrics for observability."""

from prometheus_client import Counter, Histogram

login_success_counter = Counter(
    "bee_auth_logins_total",
    "Total number of successful user logins",
)

register_failed_counter = Counter(
    "bee_auth_register_failed_total",
    "Total number of failed registration attempts",
)

error_counter = Counter(
    "bee_auth_errors_total",
    "Total number of unhandled application errors",
)

# Track registrations per provider
user_registration_counter = Counter(
    "user_registrations_by_provider",
    "Registrations by provider",
    ["provider"],
)

# Measure authentication request latency in seconds
authentication_latency = Histogram(
    "auth_request_duration_seconds",
    "Authentication request latency in seconds",
)

# Track password reset requests
password_reset_requested_counter = Counter(
    "bee_auth_password_reset_requested_total",
    "Total number of password reset requests",
)

# Track generated two-factor authentication tokens
twofa_token_generated_counter = Counter(
    "bee_auth_twofa_tokens_generated_total",
    "Total number of generated 2FA tokens",
)
