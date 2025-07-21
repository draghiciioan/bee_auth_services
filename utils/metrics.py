from prometheus_client import Counter

login_success_counter = Counter(
    "bee_auth_logins_total",
    "Total number of successful user logins",
)

register_failed_counter = Counter(
    "bee_auth_register_failed_total",
    "Total number of failed registration attempts",
)
