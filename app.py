import random
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import ALGORITHMS, Process, ScheduleResult, run, state_at

st.set_page_config(page_title="CPU Scheduling Simulator", page_icon="🖥️", layout="wide")

PALETTE = [
    "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2",
    "#B279A2", "#FF9DA6", "#9D755D", "#EECA3B", "#BAB0AC",
]
IDLE_COLOR = "#D9D9D9"

SAMPLES = {
    "Mixed arrivals (SRTF textbook)": [
        ("P1", 0, 8, 3), ("P2", 1, 4, 1), ("P3", 2, 9, 4), ("P4", 3, 5, 2),
    ],
    "Convoy effect (FCFS textbook)": [
        ("P1", 0, 24, 1), ("P2", 0, 3, 2), ("P3", 0, 3, 3),
    ],
    "Priority textbook": [
        ("P1", 0, 10, 3), ("P2", 0, 1, 1), ("P3", 0, 2, 4), ("P4", 0, 1, 5), ("P5", 0, 5, 2),
    ],
    "CPU idle gap": [
        ("P1", 0, 3, 2), ("P2", 1, 2, 1), ("P3", 9, 4, 3), ("P4", 10, 2, 1),
    ],
}
COLUMNS = ["PID", "Arrival", "Burst", "Priority"]


def sample_df(name: str) -> pd.DataFrame:
    return pd.DataFrame(SAMPLES[name], columns=COLUMNS)


def random_df(n: int) -> pd.DataFrame:
    rows = [(f"P{i + 1}", random.randint(0, 10), random.randint(1, 10), random.randint(1, 5)) for i in range(n)]
    return pd.DataFrame(rows, columns=COLUMNS)


def set_processes(df: pd.DataFrame) -> None:
    st.session_state.procs = df
    st.session_state.editor_version += 1


def to_processes(df: pd.DataFrame) -> list[Process]:
    df = df.dropna(how="all")
    if df[COLUMNS].isna().any().any():
        raise ValueError("Every row needs a PID, arrival, burst and priority.")
    return [
        Process(str(r.PID).strip(), int(r.Arrival), int(r.Burst), int(r.Priority))
        for r in df.itertuples(index=False)
    ]


def color_map(pids: list[str]) -> dict[str, str]:
    return {pid: PALETTE[i % len(PALETTE)] for i, pid in enumerate(pids)}


def gantt(result: ScheduleResult, colors: dict[str, str], per_process: bool, until: int | None = None) -> go.Figure:
    end_time = result.makespan if until is None else until
    fig = go.Figure()
    boundaries = {0}

    for s in result.timeline:
        if s.start >= end_time:
            continue
        end = min(s.end, end_time)
        boundaries.update({s.start, end})
        label = "idle" if s.idle else s.pid
        row = ("idle" if s.idle else s.pid) if per_process else "CPU"
        fig.add_trace(
            go.Bar(
                y=[row],
                x=[end - s.start],
                base=[s.start],
                orientation="h",
                marker=dict(color=IDLE_COLOR if s.idle else colors[s.pid], line=dict(color="white", width=2)),
                text=[label],
                textposition="inside",
                textfont=dict(size=14, color="white" if not s.idle else "#555"),
                insidetextanchor="middle",
                hovertemplate=f"<b>{label}</b><br>{s.start} → {s.end}<extra></extra>",
                showlegend=False,
            )
        )

    if until is not None:
        fig.add_vline(x=until, line=dict(color="#E45756", width=2, dash="dash"))

    rows = len({s.pid for s in result.timeline}) if per_process else 1
    fig.update_layout(
        barmode="overlay",
        height=110 + 45 * rows,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            range=[0, result.makespan],
            tickmode="array",
            tickvals=sorted(boundaries),
            title="Time",
            showgrid=True,
        ),
        yaxis=dict(
            autorange="reversed",
            categoryorder="array",
            categoryarray=sorted({s.pid or "idle" for s in result.timeline}, key=lambda p: (p == "idle", p)),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def stats_frame(result: ScheduleResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "PID": s.pid,
                "Arrival": s.arrival,
                "Burst": s.burst,
                "Priority": s.priority,
                "First run": s.first_run,
                "Completion": s.completion,
                "Turnaround": s.turnaround,
                "Waiting": s.waiting,
                "Response": s.response,
            }
            for s in result.stats
        ]
    )


def metric_cards(result: ScheduleResult) -> None:
    cols = st.columns(6)
    cols[0].metric("Avg waiting", f"{result.avg_waiting:.2f}")
    cols[1].metric("Avg turnaround", f"{result.avg_turnaround:.2f}")
    cols[2].metric("Avg response", f"{result.avg_response:.2f}")
    cols[3].metric("CPU utilization", f"{result.cpu_utilization:.0%}")
    cols[4].metric("Throughput", f"{result.throughput:.3f}")
    cols[5].metric("Context switches", result.context_switches)


def render_state(slot, result: ScheduleResult, t: int, colors: dict[str, str]) -> None:
    snap = state_at(result, t)

    def chips(pids: list[str]) -> str:
        if not pids:
            return "<span style='opacity:.5'>—</span>"
        return " ".join(
            f"<span style='background:{colors[p]};color:white;padding:3px 10px;border-radius:12px;"
            f"margin-right:4px;font-weight:600'>{p}</span>"
            for p in pids
        )

    with slot.container():
        c = st.columns(4)
        c[0].markdown(f"**Running @ t={t}**<br>{chips([snap.running] if snap.running else [])}", unsafe_allow_html=True)
        c[1].markdown(f"**Ready queue**<br>{chips(snap.ready)}", unsafe_allow_html=True)
        c[2].markdown(f"**Finished**<br>{chips(snap.done)}", unsafe_allow_html=True)
        c[3].markdown(f"**Not arrived yet**<br>{chips(snap.not_arrived)}", unsafe_allow_html=True)


if "procs" not in st.session_state:
    st.session_state.procs = sample_df(next(iter(SAMPLES)))
    st.session_state.editor_version = 0

with st.sidebar:
    st.header("⚙️ Settings")
    quantum = st.number_input("Round Robin quantum", min_value=1, max_value=50, value=2, step=1)
    per_process = st.toggle("Gantt: one row per process", value=False)
    speed = st.slider("Playback speed (sec per tick)", 0.05, 1.0, 0.3, 0.05)

    st.divider()
    st.subheader("Load processes")
    sample = st.selectbox("Sample set", list(SAMPLES))
    if st.button("Load sample", width="stretch"):
        set_processes(sample_df(sample))
    n_random = st.slider("Random processes", 2, 10, 5)
    if st.button("🎲 Generate random", width="stretch"):
        set_processes(random_df(n_random))

    st.divider()
    st.caption("Lower priority number = higher priority. Ties go to the running process, then earlier arrival.")

st.title("🖥️ CPU Scheduling Simulator")
st.caption("FCFS · SJF · SRTF · Priority (NP / P) · Round Robin")

st.subheader("Processes")
edited = st.data_editor(
    st.session_state.procs,
    key=f"editor_{st.session_state.editor_version}",
    num_rows="dynamic",
    width="stretch",
    hide_index=True,
    column_config={
        "PID": st.column_config.TextColumn("PID", required=True),
        "Arrival": st.column_config.NumberColumn("Arrival", min_value=0, step=1, required=True),
        "Burst": st.column_config.NumberColumn("Burst", min_value=1, step=1, required=True),
        "Priority": st.column_config.NumberColumn("Priority", min_value=0, step=1, required=True),
    },
)

try:
    processes = to_processes(edited)
    results = {name: run(name, processes, quantum) for name in ALGORITHMS}
except ValueError as e:
    st.error(str(e))
    st.stop()

colors = color_map([p.pid for p in processes])

sim_tab, compare_tab = st.tabs(["▶️ Simulate", "📊 Compare all"])

with sim_tab:
    algo = st.radio("Algorithm", list(ALGORITHMS), horizontal=True)
    st.caption(ALGORITHMS[algo])
    result = results[algo]

    metric_cards(result)

    controls = st.columns([4, 1])
    t = controls[0].slider("Step through time", 0, result.makespan, result.makespan)
    play = controls[1].button("▶ Play", width="stretch")

    chart_slot = st.empty()
    state_slot = st.empty()

    if play:
        for tick in range(result.makespan + 1):
            chart_slot.plotly_chart(
                gantt(result, colors, per_process, until=tick), width="stretch", key=f"play_{tick}"
            )
            render_state(state_slot, result, tick, colors)
            time.sleep(speed)
    else:
        until = None if t == result.makespan else t
        chart_slot.plotly_chart(gantt(result, colors, per_process, until=until), width="stretch")
        render_state(state_slot, result, t, colors)

    st.subheader("Per-process results")
    table = stats_frame(result)
    st.dataframe(table, width="stretch", hide_index=True)
    st.download_button(
        "⬇️ Download results (CSV)",
        table.to_csv(index=False).encode(),
        file_name=f"{result.algorithm}.csv".replace(" ", "_"),
        mime="text/csv",
    )

with compare_tab:
    summary = pd.DataFrame(
        [
            {
                "Algorithm": r.algorithm,
                "Avg waiting": r.avg_waiting,
                "Avg turnaround": r.avg_turnaround,
                "Avg response": r.avg_response,
                "CPU util %": r.cpu_utilization * 100,
                "Context switches": r.context_switches,
            }
            for r in results.values()
        ]
    )

    st.subheader("Summary (best in green)")
    st.dataframe(
        summary.style.format(precision=2).highlight_min(
            subset=["Avg waiting", "Avg turnaround", "Avg response", "Context switches"], color="#C7E9C0"
        ),
        width="stretch",
        hide_index=True,
    )

    bars = go.Figure()
    for metric, color in [("Avg waiting", "#4C78A8"), ("Avg turnaround", "#F58518"), ("Avg response", "#54A24B")]:
        bars.add_trace(go.Bar(name=metric, x=summary["Algorithm"], y=summary[metric], marker_color=color))
    bars.update_layout(barmode="group", height=380, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="Time units")
    st.plotly_chart(bars, width="stretch")

    st.subheader("All Gantt charts")
    for name, r in results.items():
        st.markdown(f"**{r.algorithm}** · avg waiting {r.avg_waiting:.2f}")
        st.plotly_chart(gantt(r, colors, per_process), width="stretch", key=f"cmp_{name}")
