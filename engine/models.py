from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0


@dataclass(frozen=True)
class Slice:
    pid: str | None
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def idle(self) -> bool:
        return self.pid is None


@dataclass(frozen=True)
class ProcessStats:
    pid: str
    arrival: int
    burst: int
    priority: int
    first_run: int
    completion: int
    turnaround: int
    waiting: int
    response: int


@dataclass(frozen=True)
class ScheduleResult:
    algorithm: str
    timeline: list[Slice]
    stats: list[ProcessStats]
    avg_waiting: float
    avg_turnaround: float
    avg_response: float
    cpu_utilization: float
    throughput: float
    makespan: int
    context_switches: int


@dataclass(frozen=True)
class Snapshot:
    time: int
    running: str | None
    ready: list[str]
    done: list[str]
    not_arrived: list[str]
