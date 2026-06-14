import json

import httpx
import pytest

from sesamehr import SesameSDK


class Recorder:
    """Capture outgoing requests and serve canned responses."""

    def __init__(self, responses=None):
        self.requests: list[httpx.Request] = []
        # Either a static payload for every request, or a callable(request) -> httpx.Response
        self.responses = responses if responses is not None else {"data": []}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if callable(self.responses):
            return self.responses(request)
        return httpx.Response(200, json=self.responses)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    def last_json(self):
        return json.loads(self.last.content)


@pytest.fixture
def recorder():
    return Recorder()


def make_sdk(handler, **overrides) -> SesameSDK:
    config = {
        "token": "test-token",
        "region": "EU1",
        "company_id": "company-1",
        "employee_id": "employee-1",
    }
    config.update(overrides)
    return SesameSDK(transport=httpx.MockTransport(handler), **config)


@pytest.fixture
def sdk(recorder):
    return make_sdk(recorder)
