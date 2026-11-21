from __future__ import annotations

from collections import deque
from typing import Callable

from .metrics import build_result
from .models import Process, ScheduleResult, Slice

SelectionKey = Callable[[Process, int], tuple]


def validate(processes: list[Process]) -> None:
    if not processes:
        raise ValueError("Add at least one process.")
    pids = [p.pid for p in processes]
    if len(set(pids)) != len(pids):
        raise ValueError("Process IDs must be unique.")
    for p in processes:
        if p.arrival < 0:
            raise ValueError(f"{p.pid}: arrival time can't be negative.")
        if p.burst < 1:
            raise ValueError(f"{p.pid}: burst time must be at least 1.")


def _tick_simulation(processes: list[Process], key: SelectionKey, preemptive: bool) -> list[Slice]:
    """Advance one time unit at a time, picking the process with the smallest key.

    Ties break by: keep the running process (preemptive only), then earlier arrival,
    then input order.
    """
    order = {p.pid: i for i, p in enumerate(processes)}
    remaining = {p.pid: p.burst for p in processes}
    pending = deque(sorted(processes, key=lambda p: (p.arrival, order[p.pid])))
    ready: list[Process] = []
    slices: list[Slice] = []
    current: Process | None = None
    time = 0
    finished = 0

    while finished < len(processes):
        while pending and pending[0].arrival <= time:
            ready.append(pending.popleft())

        if not ready:
            next_arrival = pending[0].arrival
            slices.append(Slice(None, time, next_arrival))
            time = next_arrival
            continue

        if current is None or preemptive:
            current = min(
                ready,
                key=lambda p: (key(p, remaining[p.pid]), p is not current, p.arrival, order[p.pid]),
            )

        slices.append(Slice(current.pid, time, time + 1))
        remaining[current.pid] -= 1
        time += 1

        if remaining[current.pid] == 0:
            ready.remove(current)
            finished += 1
            current = None

    return slices


def fcfs(processes: list[Process]) -> ScheduleResult:
    timeline = _tick_simulation(processes, lambda p, r: (p.arrival,), preemptive=False)
    return build_result("FCFS", processes, timeline)


def sjf(processes: list[Process]) -> ScheduleResult:
    timeline = _tick_simulation(processes, lambda p, r: (p.burst,), preemptive=False)
    return build_result("SJF", processes, timeline)


def srtf(processes: list[Process]) -> ScheduleResult:
    timeline = _tick_simulation(processes, lambda p, r: (r,), preemptive=True)
    return build_result("SRTF", processes, timeline)


def priority_np(processes: list[Process]) -> ScheduleResult:
    timeline = _tick_simulation(processes, lambda p, r: (p.priority,), preemptive=False)
    return build_result("Priority (NP)", processes, timeline)


def priority_p(processes: list[Process]) -> ScheduleResult:
    timeline = _tick_simulation(processes, lambda p, r: (p.priority,), preemptive=True)
    return build_result("Priority (P)", processes, timeline)


def round_robin(processes: list[Process], quantum: int) -> ScheduleResult:
    """Processes that arrive while a quantum is running join the queue
    before the preempted process is put back at the tail."""
    if quantum < 1:
        raise ValueError("Quantum must be at least 1.")

    order = {p.pid: i for i, p in enumerate(processes)}
    pending = deque(sorted(processes, key=lambda p: (p.arrival, order[p.pid])))
    remaining = {p.pid: p.burst for p in processes}
    queue: deque[Process] = deque()
    slices: list[Slice] = []
    time = 0

    def admit(until: int) -> None:
        while pending and pending[0].arrival <= until:
            queue.append(pending.popleft())

    admit(time)
    while queue or pending:
        if not queue:
            next_arrival = pending[0].arrival
            slices.append(Slice(None, time, next_arrival))
            time = next_arrival
            admit(time)
            continue

        p = queue.popleft()
        run = min(quantum, remaining[p.pid])
        slices.append(Slice(p.pid, time, time + run))
        time += run
        remaining[p.pid] -= run
        admit(time)
        if remaining[p.pid] > 0:
            queue.append(p)

    return build_result(f"Round Robin (q={quantum})", processes, slices)


ALGORITHMS: dict[str, str] = {
    "FCFS": "First-Come, First-Served. Runs processes in arrival order, no preemption.",
    "SJF": "Shortest Job First (non-preemptive). Picks the shortest burst among arrived processes.",
    "SRTF": "Shortest Remaining Time First (preemptive SJF). A shorter arrival preempts the running process.",
    "Priority (NP)": "Non-preemptive priority. Lower number = higher priority.",
    "Priority (P)": "Preemptive priority. A higher-priority arrival preempts the running process.",
    "Round Robin": "Each process gets a time quantum, then goes to the back of the ready queue.",
}


def run(algorithm: str, processes: list[Process], quantum: int = 2) -> ScheduleResult:
    validate(processes)
    dispatch = {
        "FCFS": fcfs,
        "SJF": sjf,
        "SRTF": srtf,
        "Priority (NP)": priority_np,
        "Priority (P)": priority_p,
        "Round Robin": lambda ps: round_robin(ps, quantum),
    }
    if algorithm not in dispatch:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    return dispatch[algorithm](processes)
