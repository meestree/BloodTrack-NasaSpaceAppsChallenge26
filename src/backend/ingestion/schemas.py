"""Sensor contract: five regions, one timestamp, explicit data provenance."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SensorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class RegionMeasurement(SensorModel):
    impedance_ohm: float = Field(gt=0)
    muscle_oxygen_saturation_pct: float | None = Field(default=None, ge=0, le=100)


class ExtremityMeasurement(RegionMeasurement):
    skin_temperature_c: float


class BodyRegions(SensorModel):
    left_arm: ExtremityMeasurement
    right_arm: ExtremityMeasurement
    left_leg: ExtremityMeasurement
    right_leg: ExtremityMeasurement
    neck_lateral: RegionMeasurement


class SensorPayload(SensorModel):
    timestamp: AwareDatetime
    source: Literal["real", "simulated"]
    regions: BodyRegions
