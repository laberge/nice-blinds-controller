"""Minimal aiohttp mock for the tests, in the style of aioresponses.

aioresponses 0.7.9 can't build responses on aiohttp 3.14 (the version Home
Assistant 2026.9+ ships), so the tests patch ClientSession._request with this.
Each registered URL answers one request (or every request with repeat=True),
in registration order.
"""
from collections import defaultdict
from typing import Any, NamedTuple
from unittest.mock import patch

import aiohttp
from multidict import CIMultiDict
from yarl import URL


def normalize_url(url: URL | str) -> URL:
    """Sort query params so URLs compare regardless of param order."""
    url = URL(url)
    return url.with_query(sorted(url.query.items()))


class RequestCall(NamedTuple):
    args: tuple
    kwargs: dict[str, Any]


class _Response:
    def __init__(self, method: str, url: URL, status: int, body: str) -> None:
        self.method = method
        self.url = url
        self.status = status
        self._body = body

    async def text(self, encoding: str | None = None) -> str:
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                aiohttp.RequestInfo(self.url, self.method, CIMultiDict(), self.url),
                (),
                status=self.status,
            )

    async def __aenter__(self) -> "_Response":
        return self

    async def __aexit__(self, *exc: object) -> None:
        pass

    def release(self) -> None:
        pass

    async def wait_for_close(self) -> None:
        pass


class MockHTTP:
    """Context manager that intercepts every aiohttp ClientSession request."""

    def __init__(self) -> None:
        self._responses: list[tuple[URL, int, str, BaseException | None, bool]] = []
        self.requests: dict[tuple[str, URL], list[RequestCall]] = defaultdict(list)
        self._patcher = patch.object(aiohttp.ClientSession, "_request", self._request)

    def __enter__(self) -> "MockHTTP":
        self._patcher.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._patcher.stop()

    def get(
        self,
        url: str,
        *,
        status: int = 200,
        body: str = "",
        exception: BaseException | None = None,
        repeat: bool = False,
    ) -> None:
        self._responses.append((normalize_url(url), status, body, exception, repeat))

    async def _request(self, method: str, str_or_url: Any, **kwargs: Any) -> _Response:
        url = normalize_url(str_or_url)
        self.requests[(method.upper(), url)].append(RequestCall((), kwargs))
        for i, (match, status, body, exception, repeat) in enumerate(self._responses):
            if method.upper() == "GET" and match == url:
                if not repeat:
                    del self._responses[i]
                if exception is not None:
                    raise exception
                return _Response(method, url, status, body)
        raise aiohttp.ClientConnectionError(f"Connection refused: {method} {url}")

    def assert_called_once(self) -> None:
        calls = sum(len(c) for c in self.requests.values())
        assert calls == 1, f"expected 1 request, got {calls}"

    def assert_called_once_with(self, url: str, **kwargs: Any) -> None:
        self.assert_called_once()
        (call,) = self.requests.get(("GET", normalize_url(url)), [None])
        assert call is not None, f"GET {url} was not requested"
        for key, value in kwargs.items():
            assert call.kwargs.get(key) == value, f"{key}: {call.kwargs.get(key)!r} != {value!r}"
