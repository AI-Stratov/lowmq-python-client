# Legacy module kept for backward compatibility.
# Prefer importing LowMqClient from lowmq_client.
from .client import LowMqClient

__all__ = ["LowMqClient"]
