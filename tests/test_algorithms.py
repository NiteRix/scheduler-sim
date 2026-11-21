import pytest

from engine import Process, Slice, run, state_at


def P(pid, arrival, burst, priority=0):
    return Process(pid, arrival, burst, priority)


def gantt(result):
    return [(s.pid, s.start, s.end) for s in result.timeline]


def test_fcfs_silberschatz():
    ps = [P("P1", 0, 24), P("P2", 0, 3), P("P3", 0, 3)]
    r = run("FCFS", ps)
    assert gantt(r) == [("P1", 0, 24), ("P2", 24, 27), ("P3", 27, 30)]
    assert r.avg_waiting == pytest.approx(17)
    assert r.avg_turnaround == pytest.approx(27)


def test_sjf_silberschatz():
    ps = [P("P1", 0, 6), P("P2", 0, 8), P("P3", 0, 7), P("P4", 0, 3)]
    r = run("SJF", ps)
    assert gantt(r) == [("P4", 0, 3), ("P1", 3, 9), ("P3", 9, 16), ("P2", 16, 24)]
    assert r.avg_waiting == pytest.approx(7)


def test_srtf_silberschatz():
    ps = [P("P1", 0, 8), P("P2", 1, 4), P("P3", 2, 9), P("P4", 3, 5)]
    r = run("SRTF", ps)
    assert gantt(r) == [("P1", 0, 1), ("P2", 1, 5), ("P4", 5, 10), ("P1", 10, 17), ("P3", 17, 26)]
    assert r.avg_waiting == pytest.approx(6.5)


def test_priority_np_silberschatz():
    ps = [P("P1", 0, 10, 3), P("P2", 0, 1, 1), P("P3", 0, 2, 4), P("P4", 0, 1, 5), P("P5", 0, 5, 2)]
    r = run("Priority (NP)", ps)
    assert gantt(r) == [("P2", 0, 1), ("P5", 1, 6), ("P1", 6, 16), ("P3", 16, 18), ("P4", 18, 19)]
    assert r.avg_waiting == pytest.approx(8.2)


def test_priority_preemptive():
    ps = [P("P1", 0, 5, 3), P("P2", 1, 2, 1)]
    r = run("Priority (P)", ps)
    assert gantt(r) == [("P1", 0, 1), ("P2", 1, 3), ("P1", 3, 7)]


def test_priority_np_does_not_preempt():
    ps = [P("P1", 0, 5, 3), P("P2", 1, 2, 1)]
    r = run("Priority (NP)", ps)
    assert gantt(r) == [("P1", 0, 5), ("P2", 5, 7)]


def test_round_robin_silberschatz():
    ps = [P("P1", 0, 24), P("P2", 0, 3), P("P3", 0, 3)]
    r = run("Round Robin", ps, quantum=4)
    assert gantt(r) == [("P1", 0, 4), ("P2", 4, 7), ("P3", 7, 10), ("P1", 10, 30)]
    assert r.avg_waiting == pytest.approx(17 / 3)


def test_round_robin_new_arrival_goes_before_requeued_process():
    ps = [P("P1", 0, 4), P("P2", 2, 2)]
    r = run("Round Robin", ps, quantum=2)
    assert gantt(r) == [("P1", 0, 2), ("P2", 2, 4), ("P1", 4, 6)]


def test_round_robin_large_quantum_equals_fcfs():
    ps = [P("P1", 0, 5), P("P2", 1, 3), P("P3", 2, 1)]
    assert gantt(run("Round Robin", ps, quantum=100)) == gantt(run("FCFS", ps))


@pytest.mark.parametrize("algo", ["FCFS", "SJF", "SRTF", "Priority (NP)", "Priority (P)", "Round Robin"])
def test_idle_gap(algo):
    ps = [P("P1", 0, 2), P("P2", 5, 3)]
    r = run(algo, ps, quantum=2)
    assert gantt(r) == [("P1", 0, 2), (None, 2, 5), ("P2", 5, 8)]
    assert r.cpu_utilization == pytest.approx(5 / 8)


@pytest.mark.parametrize("algo", ["FCFS", "SJF", "SRTF", "Priority (NP)", "Priority (P)", "Round Robin"])
def test_every_process_gets_exactly_its_burst(algo):
    ps = [P("A", 0, 7, 2), P("B", 2, 4, 1), P("C", 4, 1, 3), P("D", 5, 4, 1), P("E", 20, 3, 2)]
    r = run(algo, ps, quantum=3)
    for p in ps:
        assert sum(s.length for s in r.timeline if s.pid == p.pid) == p.burst
    for a, b in zip(r.timeline, r.timeline[1:]):
        assert a.end == b.start


def test_late_first_arrival_starts_with_idle():
    r = run("FCFS", [P("P1", 3, 2)])
    assert gantt(r) == [(None, 0, 3), ("P1", 3, 5)]
    assert r.stats[0].waiting == 0


def test_state_at():
    ps = [P("P1", 0, 24), P("P2", 0, 3), P("P3", 0, 3)]
    r = run("Round Robin", ps, quantum=4)
    snap = state_at(r, 5)
    assert snap.running == "P2"
    assert snap.ready == ["P1", "P3"]
    assert snap.done == []


@pytest.mark.parametrize(
    "ps, msg",
    [
        ([], "at least one"),
        ([P("P1", 0, 2), P("P1", 1, 2)], "unique"),
        ([P("P1", -1, 2)], "negative"),
        ([P("P1", 0, 0)], "at least 1"),
    ],
)
def test_validation(ps, msg):
    with pytest.raises(ValueError, match=msg):
        run("FCFS", ps)
