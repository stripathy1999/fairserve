# FairServe Zone 2: The Analytical Engine - Explained

This document explains the **Zone 2** branch of the FairServe project. This zone is responsible for **Analysis, Simulation, and Verification**. It acts as the brain that processes raw data into actionable insights and hard constraints, without needing intake (Zone 1) or user interfaces (Zone 3).

## 1. Big Picture: What This Branch Does

**Zone 2 is the "Constitution and Calculator" of FairServe.**

*   **Problem Solved**: Raw data tells you *what happened*. Zone 2 tells you *is it fair?*, *why is it happening?*, and *what happens if we change policy?*
*   **Guarantees**: It mathematically guarantees that any proposed policy (like shifting resources) adheres to strict safety limits (the "Constitution") before it can ever be proposed to a human.
*   **Inputs**:
    *   `incidents_historical.parquet`: Past closed tickets (performance history).
    *   `incidents_live.parquet`: Current open tickets (backlog status).
*   **Outputs**:
    *   `city_state.json`: A single "truth" object describing the city's health.
    *   `verifier_outputs.json`: A Pass/Fail verdict on proposed changes.

---

## 2. Data Flow Within Zone 2

The pipeline runs sequentially. Each step builds on the previous one.

1.  **Metric Calculation**:
    *   **Input**: Parquet Files (Raw Data)
    *   `compute_fairness_metrics.py` → Calculates "How bad is the inequality?"
    *   `compute_neighborhood_signals.py` → Calculates "Why is it happening?" (Backlog? Mislabeling?)
2.  **State Aggregation**:
    *   `build_city_state.py` → Merges metrics + signals into `city_state.json`. Adds the "Constitution" (rules).
3.  **Simulation**:
    *   `simulator.py` → Reads `city_state.json`. Tests "What if we change X?" producing `scenario_results.json`.
4.  **Verification**:
    *   `verifier.py` → Audits results against the Constitution. Produces `verifier_outputs.json` (Pass/Fail).

**Why this order?**
You cannot simulate a change (Step 3) if you don't know the current baseline (Step 2). You cannot know the baseline (Step 2) without raw metrics (Step 1). Verification (Step 4) must always be the final gatekeeper.

---

## 3. File-by-File Explanation

### A. `metrics/compute_fairness_metrics.py`
*   **Reads**: `incidents_historical.parquet`
*   **Computes**: The "Speed" and "Fairness" of the system.
    *   It looks at *closed* tickets to see how long they took.
    *   It ranks neighborhoods from best served to worst served.
*   **Writes**: `fairness_metrics.json`
*   **Why Needed**: Identifies *who* needs help (the "Worst K" neighborhoods).

### B. `metrics/compute_neighborhood_signals.py`
*   **Reads**: `incidents_historical.parquet` AND `incidents_live.parquet`
*   **Computes**: Operational signals explaining *why* a neighborhood is slow.
    *   Is it a huge backlog? (Live data)
    *   Is it difficult work (dupes/mislabels)? (Historical patterns)
*   **Writes**: `neighborhood_signals.json`
*   **Why Needed**: Gives the Simulator the "why" so it can model backlog pressure.

### C. `state/build_city_state.py`
*   **Reads**: `fairness_metrics.json` + `neighborhood_signals.json`
*   **Computes**: Nothing heavy. It *aggregates* data.
    *   It defines the **Constitution**: "We will not allow harm > 5%".
    *   It defines the **Policy Space**: "You can shift up to 30% capacity".
*   **Writes**: `city_state.json`
*   **Why Needed**: This is the API for the rest of the system. It packages everything an Agent or UI needs to know into one file.

### D. `sim/simulator.py`
*   **Reads**: `city_state.json` + Raw Parquet (for calibration)
*   **Computes**: **Counterfactuals** (What-if scenarios).
    *   *Scenario*: "Take 20% capacity from the fastest neighborhood and give it to the slowest."
    *   *Result*: "Fastest neighborhood gets 10% slower. Slowest gets 40% faster."
*   **Writes**: `scenario_results.json`
*   **Why Needed**: Allows us to test ideas safely without experimenting on real people.

### E. `sim/verifier.py`
*   **Reads**: `scenario_results.json` + `city_state.json` (for the rules)
*   **Computes**: **Audits**.
    *   Check: Did the worst neighborhood improve enough?
    *   Check: Did we accidentally ruin a good neighborhood?
*   **Writes**: `verifier_outputs.json`
*   **Why Needed**: The automated safety brake. If this says FAIL, the policy is rejected immediately.

---

## 4. Metrics Explained

| Metric | What it means | Why it matters |
| :--- | :--- | :--- |
| **p50 (Median)** | The "normal" wait time. 50% of people waited less than this. | Good snapshot of typical experience. |
| **p90 (90th %)** | The "worst reasonable" wait time. 90% waited less. | **Critical for equity.** We care about the "tail"—the people waiting the longest. |
| **Ratio p90** | `Neighborhood p90 / City Average p90`. | **The Fairness Score.** 1.0 = Average. 2.0 = You wait twice as long as the city average. |
| **Backlog Pressure** | `Open Tickets / Daily Closure Rate`. | "How many days of work are piled up?" If > 1.5, the team is drowning. |
| **Aging Tail 14d** | % of open tickets older than 14 days. | "Are we ignoring old tickets?" High values mean people are being forgotten. |
| **Duplicate Rate** | % of tickets that are copies. | Efficiency killer. High rate = need better intake tools. |
| **Mislabel Rate** | % of tickets sent to the wrong department. | Wasted trips. High rate = need better AI classification. |

---

## 5. Simulator Logic (Deterministic)

**Philosophy**: "Better roughly right than precisely wrong."
The simulator does not use complex AI models. It uses **Physics/Math**.

*   **Logic**: It treats service delivery like water flowing through a pipe.
    *   **Inflow**: Operational arrival rate (tickets/day).
    *   **Pipe Width**: Capacity (tickets/day).
    *   **Puddle**: Backlog.
*   **The Math**:
    *   `New Backlog = Old Backlog + (Arrivals - New Capacity)`
    *   If you increase Capacity (Pipe Width), the Puddle (Backlog) shrinks.
    *   If Puddle shrinks, Wait Time (p90) drops proportionally.
*   **Why Deterministic?**: It is explainable. If a policy fails, you can point exactly to the math: "You shifted 20% capacity, which reduced their speed by 15%, violating the 5% limit." No "black box" AI guessing.

---

## 6. Verifier Logic (The Hard Gate)

The **Constitution** is a set of hard constraints encoded in `city_state.json`.

1.  **Min Improvement Rule**: "If you change things, the worst-off neighborhoods MUST get significantly better (e.g., 15% faster)."
    *   *Why*: prevents "token gestures" that don't actually help.
2.  **No Harm Rule**: "No neighborhood can get worse by more than 5%."
    *   *Why*: prevents "Robin Hood" policies that destroy high-performing areas to fix low-performing ones.
3.  **Backlog Growth Rule**: "Backlog cannot explode anywhere."
    *   *Why*: prevents kicking the can down the road.

**PASS vs FAIL**: A policy must pass **ALL** checks. One violation = **FAIL**.

---

## 7. How to Explain This Branch

**30-Second Pitch**:
"Zone 2 is the analytics engine. It calculates how unfair city services are today, simulates how to fix it by shifting resources, and mathematically proves that those fixes won't accidentally hurt anyone before we deploy them."

**Engineer Pitch**:
"It's a Python ETL and simulation pipeline. We ingest Parquet, aggregate into a JSON state object using Pandas, run a deterministic resource-allocation simulation to test policy changes, and assert results against a hard-coded constraints config (the Constitution). It's purely functional and runs offline."
