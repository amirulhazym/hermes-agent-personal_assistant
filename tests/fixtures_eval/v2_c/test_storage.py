# Test verifying active configuration
from .storage_config import DEFAULT_RETENTION_DAYS, DEFAULT_PORT

def test_retention():
    assert DEFAULT_RETENTION_DAYS == 90
    assert DEFAULT_PORT == 9443
