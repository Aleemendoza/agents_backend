"""Generate secure API keys for EAR."""

import secrets

print(secrets.token_hex(32))
