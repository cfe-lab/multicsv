
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class MultiCSVSection:
    name: str
    descriptor: TextIO
