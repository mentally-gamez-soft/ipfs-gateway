import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import vcr

# VCR configuration for recording/replaying HTTP interactions
vcr_config = {
    'record_mode': 'once',  # Record only if cassette doesn't exist
    'cassette_library_dir': 'tests/cassettes',
    'decode_compressed_response': True,
    'match_on': ['method', 'scheme', 'host', 'port', 'path', 'query'],
    'filter_headers': ['Authorization', 'X-API-Key', 'X-Admin-Key'],
}

@pytest.fixture
def vcr_cassette(request):
    """
    Fixture for VCR cassette naming based on test function.
    Usage: @pytest.mark.vcr in test functions
    """
    return f"{request.node.nodeid.replace('::', '_').replace('/', '_')}.yaml"
