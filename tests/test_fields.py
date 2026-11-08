from ipaddress import IPv4Address

import pytest

from aiophoenixcontactcharx.enums import VehicleStatus
from aiophoenixcontactcharx.fields import IPv4OctetsField, VehicleStatusField


def test_ipv4_decodes_one_octet_per_register() -> None:
    assert IPv4OctetsField(121).decode([192, 168, 1, 50]) == IPv4Address("192.168.1.50")


def test_ipv4_spans_four_registers() -> None:
    assert IPv4OctetsField(121).count == 4


def test_ipv4_above_255_is_none(caplog: pytest.LogCaptureFixture) -> None:
    assert IPv4OctetsField(121).decode([192, 168, 256, 1]) is None
    assert "no IPv4 address" in caplog.text


@pytest.mark.parametrize("status", list(VehicleStatus))
def test_vehicle_status_decodes_every_code(status: VehicleStatus) -> None:
    word = int.from_bytes(status.value.encode(), "big")

    assert VehicleStatusField(299).decode([word]) is status


def test_vehicle_status_without_characters_is_none() -> None:
    assert VehicleStatusField(299).decode([0]) is None


def test_vehicle_status_unknown_code_is_none_and_warns_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    field = VehicleStatusField(299)
    word = int.from_bytes(b"Z9", "big")

    assert field.decode([word]) is None
    assert field.decode([word]) is None
    assert caplog.text.count("unknown vehicle status 'Z9'") == 1
