from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class MeasurementInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    id_parte: int = Field(gt=0, strict=True)
    timestamp: AwareDatetime
    temperatura: float
    caudal: float = Field(description="Microcirculation measured in perfusion units (PU).")
    movimiento: Literal[0, 1]

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value > datetime.now(timezone.utc):
            raise ValueError("Measurement timestamp cannot be in the future")
        return value.astimezone(timezone.utc)


class MeasurementBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    measurements: list[MeasurementInput] = Field(min_length=1, max_length=1000)
