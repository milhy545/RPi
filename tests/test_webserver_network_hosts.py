"""Regresní testy hostitelů zahrnutých v TLS certifikátu."""

from unittest.mock import patch


def test_https_san_uses_shared_network_discovery() -> None:
    """Při tvorbě SAN certifikátu použije sdílenou síťovou službu."""
    import webserver

    names = ["localhost", "rpi-tv"]
    addresses = ["127.0.0.1", "192.168.0.205", "2001:db8::5"]
    with patch(
        "webserver.system_service.dashboard_hostnames_and_ips",
        return_value=(names, addresses),
    ) as discover:
        san = webserver._https_san()

    discover.assert_called_once_with()
    assert san == (
        "subjectAltName=DNS:localhost,DNS:rpi-tv,"
        "IP:127.0.0.1,IP:192.168.0.205,IP:2001:db8::5"
    )
