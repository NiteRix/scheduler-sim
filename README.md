# CPU Scheduling Simulator

An interactive simulator for the CPU scheduling algorithms covered in OS courses, with an animated Gantt chart, per-process metrics, and a side-by-side comparison of every algorithm.

https://scheduler-sim.streamlit.app/

**Algorithms:** FCFS · SJF (non-preemptive) · SRTF (preemptive SJF) · Priority (non-preemptive) · Priority (preemptive) · Round Robin

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Run the tests:

```bash
pytest
```

## Project structure

```
engine/              pure Python, no UI code
  models.py          Process, Slice, ProcessStats, ScheduleResult, Snapshot
  algorithms.py      the six schedulers + run() dispatcher + input validation
  metrics.py         waiting / turnaround / response, CPU utilization, throughput, state_at()
app.py               Streamlit UI (input table, Gantt chart, playback, comparison)
tests/               checks against the Silberschatz textbook examples + edge cases
```

**The contract between engine and UI:** `run(algorithm, processes, quantum)` returns a `ScheduleResult`, which holds a list of `Slice(pid, start, end)` (where `pid=None` means the CPU is idle) plus all the metrics. The UI never computes scheduling logic itself.

## Conventions (state these in the report)

- Lower priority number = higher priority.
- Tie-breaking: in preemptive modes, the running process keeps the CPU on a tie; after that, the earlier arrival wins, then input order.
- Round Robin: a process arriving at the same moment a quantum expires joins the ready queue **before** the preempted process.
- Context-switch time is 0.
- CPU utilization and throughput are measured over `[0, last completion]`.

## Formulas

- Turnaround = Completion − Arrival
- Waiting = Turnaround − Burst
- Response = First run − Arrival

## Splitting the work

| Person A: engine | Person B: interface |
|---|---|
| `engine/` + `tests/` | `app.py` |
| New algorithms (MLFQ, …) | Visuals, playback, comparison view |
| Correctness vs textbook | Demo flow, screenshots for report |

## Extension ideas

- Multilevel Feedback Queue (MLFQ)
- Context-switch overhead as a setting
- Aging to fix starvation in Priority scheduling
- I/O bursts (CPU → I/O → CPU)
- Deploy for free on Streamlit Community Cloud to get a demo link
