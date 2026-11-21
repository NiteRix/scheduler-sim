from __future__ import annotations

from .models import Process, ProcessStats, ScheduleResult, Slice, Snapshot


def merge_slices(slices: list[Slice]) -> list[Slice]:
    merged: list[Slice] = []
    for s in slices:
        if s.length <= 0:
            continue
        if merged and merged[-1].pid == s.pid and merged[-1].end == s.start:
            merged[-1] = Slice(s.pid, merged[-1].start, s.end)
        else:
            merged.append(s)
    return merged


def build_result(algorithm: str, processes: list[Process], timeline: list[Slice]) -> ScheduleResult:
    timeline = merge_slices(timeline)

    first_run: dict[str, int] = {}
    completion: dict[str, int] = {}
    for s in timeline:
        if s.idle:
            continue
        first_run.setdefault(s.pid, s.start)
        completion[s.pid] = s.end

    stats = []
    for p in processes:
        turnaround = completion[p.pid] - p.arrival
        stats.append(
            ProcessStats(
                pid=p.pid,
                arrival=p.arrival,
                burst=p.burst,
                priority=p.priority,
                first_run=first_run[p.pid],
                completion=completion[p.pid],
                turnaround=turnaround,
                waiting=turnaround - p.burst,
                response=first_run[p.pid] - p.arrival,
            )
        )

    n = len(stats)
    makespan = max(completion.values())
    busy = sum(s.length for s in timeline if not s.idle)
    busy_slices = [s for s in timeline if not s.idle]
    switches = sum(1 for a, b in zip(busy_slices, busy_slices[1:]) if a.pid != b.pid)

    return ScheduleResult(
        algorithm=algorithm,
        timeline=timeline,
        stats=stats,
        avg_waiting=sum(s.waiting for s in stats) / n,
        avg_turnaround=sum(s.turnaround for s in stats) / n,
        avg_response=sum(s.response for s in stats) / n,
        cpu_utilization=busy / makespan if makespan else 0.0,
        throughput=n / makespan if makespan else 0.0,
        makespan=makespan,
        context_switches=switches,
    )


def state_at(result: ScheduleResult, t: int) -> Snapshot:
    running = next((s.pid for s in result.timeline if s.start <= t < s.end and not s.idle), None)
    ordered = sorted(result.stats, key=lambda s: (s.arrival, s.pid))
    done = [s.pid for s in ordered if s.completion <= t]
    not_arrived = [s.pid for s in ordered if s.arrival > t]
    ready = [s.pid for s in ordered if s.arrival <= t < s.completion and s.pid != running]
    return Snapshot(time=t, running=running, ready=ready, done=done, not_arrived=not_arrived)
