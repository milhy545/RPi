"""Regression tests for bounded HTTP client disconnect handling."""

from io import BytesIO
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from webserver import H


class DisconnectingWriter:
    def __init__(self, error: OSError) -> None:
        self.error = error

    def write(self, _body: bytes) -> None:
        raise self.error


def _handler(writer: object) -> Any:
    handler = cast(Any, object.__new__(H))
    handler.wfile = writer
    handler.close_connection = False
    handler.headers = {}
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    return handler


def test_write_body_succeeds_for_connected_client() -> None:
    writer = BytesIO()
    handler = _handler(writer)

    assert handler._write_body(b"payload") is True
    assert writer.getvalue() == b"payload"
    assert handler.close_connection is False


@pytest.mark.parametrize("error", [BrokenPipeError("gone"), ConnectionResetError("reset")])
def test_write_body_bounds_expected_client_disconnect(error: OSError) -> None:
    handler = _handler(DisconnectingWriter(error))

    assert handler._write_body(b"payload") is False
    assert handler.close_connection is True


def test_json_response_does_not_recurse_after_disconnect() -> None:
    handler = _handler(DisconnectingWriter(BrokenPipeError("gone")))

    handler.sj(200, {"ok": True})

    handler.send_response.assert_called_once_with(200)
    handler.end_headers.assert_called_once_with()
    assert handler.close_connection is True


def test_text_response_does_not_recurse_after_disconnect() -> None:
    handler = _handler(DisconnectingWriter(ConnectionResetError("reset")))

    handler.st(200, "hello")

    handler.send_response.assert_called_once_with(200)
    handler.end_headers.assert_called_once_with()
    assert handler.close_connection is True
