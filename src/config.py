from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Paths:
    raw: Path = Path("data/raw")
    processed: Path = Path("data/processed")
    outputs: Path = Path("outputs")

@dataclass(frozen=True)
class Settings:
    # Choose a total metric (common choice in Climate TRACE exports)
    target_gas: str = "total_co2e_100gwp"
    # grid size if you do lat/lon binning
    grid_deg: float = 0.1
