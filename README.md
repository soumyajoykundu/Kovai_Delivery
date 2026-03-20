# 🛸 KovaiDelivery — Multi-Agent Autonomous Drone Logistics System

KovaiDelivery is a **multi-agent autonomous logistics controller** designed to coordinate a large fleet of delivery drones under **dynamic weather and energy constraints**.  
The system replaces heuristic routing with **agentic reasoning**, **formal inter-agent communication**, and **predictive safety policies**.

This project was built as a solution to the *Kovai Efficiency Crisis* simulation challenge.

---

## 🧠 Problem Overview

The city logistics hub must manage:
- **100+ drones** with heterogeneous speed and payload capacity
- **200+ delivery orders** arriving over time
- **Dynamic weather events** (CLEAR, WINDY, STORMY)
- **Hard safety constraint**: drones must never crash due to battery depletion

### Core Objective

> Guarantee as many high-priority deliveries as possible while **preventing drone crashes**, especially during storm events.

The system must dynamically decide:
- Which drone should take which order
- When to delay or defer assignments
- When drones must return to hub for safety

---

## 🏗 System Architecture

The solution is implemented as a **multi-agent system** with explicit roles and responsibilities.  
Agents communicate using a **JSON-RPC–style A2A (Agent-to-Agent) protocol**, and all physical calculations are accessed via an **MCP-style tool server**.

### Agent Roles

#### 🧾 Order Analyst
- Parses unstructured order text
- Extracts semantic priority:
  - `medical`, `urgent`, `fragile`, `standard`

#### 🛡 Safety Auditor
- Acts as an energy and weather watchdog
- Validates whether a drone can safely perform a mission
- Returns one of:
  - `ALLOW` — safe to launch
  - `WAIT` — defer until weather improves
  - `REJECT` — permanently unsafe (e.g. payload too heavy)

#### ⚙️ Resource Allocator
- Performs combinatorial matching between drones and orders
- Optimizes based on:
  - Priority (medical/urgent first)
  - ETA for high-priority orders
  - Distance for standard orders

#### 🚦 Dispatcher (Orchestrator)
- Maintains global state and memory
- Tracks active missions and deferred orders
- Issues valid actions to the simulation engine:
  - `PICKUP`, `MOVE`, `DELIVER`

---

## 🔌 Protocols & Design Principles

### A2A (Agent-to-Agent) Protocol
- All agent communication uses a structured JSON-RPC envelope
- Every decision is a formal message exchange
- Enforces clean separation between reasoning units

### MCP (Model Context Protocol)
- All environment queries (distance computation) go through an MCP server
- Agents never compute physics directly
- Ensures tool boundaries and reproducibility

### Pydantic Schemas
- All drones, orders, candidates, and messages are validated using **Pydantic**
- Prevents schema drift and runtime key errors
- Enforces strict contracts between agents

---

## 🔋 Safety & Energy Model

The simulator does **not expose battery telemetry** directly.  
To handle this constraint, the system uses **conservative proxy policies**:

- Distance-based safety thresholds
- Speed-aware allowances (fast vs slow drones)
- Weather-aware deferrals:
  - No launches during `STORMY`
  - Slow drones restricted during `WINDY`
- Immediate return-to-hub policy when drones are idle off-hub

This prevents:
- Mid-air battery depletion
- Storm-induced crashes
- Inefficient hovering

---

## 📊 Performance Metrics

The system is evaluated using:

- **Deliveries**: number of successfully completed drop-offs
- **Efficiency Score**:
Efficiency = Total Distance Traveled / Total Battery Used

- **Reliability**: zero drone crashes is the primary constraint

The design prioritizes **safe completion over reckless throughput**.

---

## 🚀 Running the Simulation

### 1️⃣ Setup Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2️⃣ Running with Sample Data
```bash
python3 run_mission.py \
  --fleet data/sample/fleet_sample.csv \
  --orders data/sample/orders_sample.csv
```


### 3️⃣ Running Full City-Scale Simulation
```bash
python3 run_mission.py
```

### 🧪 What Happens During Execution

- Orders arrive at their specified ticks
- Agents reason and negotiate assignments every tick
- Weather changes dynamically
- Drones:
   *  Deliver orders
   *  Return to hub when idle
   *  Defer launches during unsafe conditions
- The simulation terminates when:
- All orders are delivered, or Time horizon is reached


