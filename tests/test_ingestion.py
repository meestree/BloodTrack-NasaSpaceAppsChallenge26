from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.ingestion.schemas import SensorPayload


@pytest.fixture
def payload() -> dict:
    return {
        "timestamp": "2026-11-14T12:00:00Z",
        "source": "simulated",
        "regions": {
            **{
                region: {"impedance_ohm": 500, "skin_temperature_c": 32}
                for region in ("left_arm", "right_arm", "left_leg", "right_leg")
            },
            "neck_lateral": {"impedance_ohm": 450},
        },
    }


def test_complete_payload_and_missing_optional_measurement(payload: dict) -> None:
    measurement = SensorPayload.model_validate(payload)
    assert measurement.source == "simulated"
    assert measurement.regions.left_arm.muscle_oxygen_saturation_pct is None


@pytest.mark.parametrize(
    "case",
    ["missing_region", "chest", "missing_temperature", "negative_impedance",
     "invalid_oxygen", "nonfinite", "naive_timestamp", "missing_source"],
)
def test_invalid_payloads_are_rejected(payload: dict, case: str) -> None:
    invalid = deepcopy(payload)
    regions = invalid["regions"]
    if case == "missing_region":
        del regions["neck_lateral"]
    elif case == "chest":
        regions["chest"] = {"impedance_ohm": 500}
    elif case == "missing_temperature":
        del regions["left_arm"]["skin_temperature_c"]
    elif case == "negative_impedance":
        regions["left_arm"]["impedance_ohm"] = -1
    elif case == "invalid_oxygen":
        regions["left_arm"]["muscle_oxygen_saturation_pct"] = 101
    elif case == "nonfinite":
        regions["left_arm"]["impedance_ohm"] = float("inf")
    elif case == "naive_timestamp":
        invalid["timestamp"] = "2026-11-14T12:00:00"
    elif case == "missing_source":
        del invalid["source"]
    with pytest.raises(ValidationError):
        SensorPayload.model_validate(invalid)
