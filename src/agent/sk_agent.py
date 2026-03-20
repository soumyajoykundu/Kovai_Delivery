import math
import random

# ============================================================
# CONFIGURATION (SAFE, DISTANCE-ONLY)
# ============================================================

"""
Maximum one-way distance allowed in CLEAR weather.
Storm is handled separately.
"""
MAX_CLEAR_DISTANCE = 20.0

# Maximum one-way distance allowed during storms
MAX_STORM_DISTANCE = 6.0

# Clear / windy weather thresholds
MAX_DISTANCE_FAST_DRONE = 20.0     # speed >= 3.0
MAX_DISTANCE_SLOW_DRONE = 17.0     # speed < 3.0

# ============================================================
# A2A MESSAGE
# ============================================================

class A2AMessage:
    """JSON-RPC style Agent-to-Agent message."""
    def __init__(self, sender, receiver, method, params):
        self.envelope = {
            "jsonrpc": "2.0",
            "sender": sender,
            "receiver": receiver,
            "method": method,
            "params": params,
            "id": random.randint(1000, 9999)
        }

# ============================================================
# MCP SERVER (TOOLS ONLY)
# ============================================================

class KovaiMCPServer:
    """MCP server exposing allowed tools."""

    @staticmethod
    def calculate_distance(p1, p2):
        return math.sqrt(
            (p1[0] - p2[0]) ** 2 +
            (p1[1] - p2[1]) ** 2
        )

# ============================================================
# AGENTS
# ============================================================

class OrderAnalystAgent:
    """Extracts priority from order text."""

    def handle(self, msg: A2AMessage):
        text = msg.envelope["params"]["text"].lower()
        if "medical" in text:
            return "medical"
        if "urgent" in text:
            return "urgent"
        if "fragile" in text:
            return "fragile"
        return "standard"


class SafetyAuditorAgent:
    """
    Safety gate with deferral (WAIT) instead of hard reject.
    """

    def __init__(self, mcp):
        self.mcp = mcp

    def handle(self, msg: A2AMessage):
        drone = msg.envelope["params"]["drone"]
        order = msg.envelope["params"]["order"]
        weather = msg.envelope["params"]["weather"]

        # Capacity check (hard reject)
        if order["mass"] > drone["capacity"]:
            return "REJECT"

        dist = self.mcp.calculate_distance((0, 0), order["destination"])

        # Storm → WAIT (do NOT reject)
        if weather == "STORMY":
            return "WAIT"

        # Clear / Windy → capability-based allow
        if drone["speed"] >= 3.0:
            return "ALLOW" if dist <= MAX_DISTANCE_FAST_DRONE else "REJECT"
        else:
            return "ALLOW" if dist <= MAX_DISTANCE_SLOW_DRONE else "REJECT"



class AllocatorAgent:
    """
    Simple allocator (can be replaced by Qwen later).
    """

    def handle(self, msg: A2AMessage):
        order = msg.envelope["params"]["order"]
        candidates = msg.envelope["params"]["candidates"]

        if not candidates:
            return None

        # Medical / urgent → fastest
        if order["priority"] in ("medical", "urgent"):
            return min(candidates, key=lambda c: c["eta"])

        # Otherwise → nearest
        return min(candidates, key=lambda c: c["distance"])

# ============================================================
# ORCHESTRATOR
# ============================================================

class KovaiOrchestrator:
    """Central MCP + A2A coordinator."""

    def __init__(self):
        self.name = "Senior Controller"
        self.mcp = KovaiMCPServer()

        self.order_analyst = OrderAnalystAgent()
        self.safety_auditor = SafetyAuditorAgent(self.mcp)
        self.allocator = AllocatorAgent()

        self.drone_targets = {}  # drone_id → order

    def orchestrate(self, state):
        actions = {}
        drones = state["drones"]
        orders = state["pending_orders"]
        weather = state["weather"]

        # ---------------- ASSIGNMENT ----------------

        for drone_id, drone in drones.items():

            if drone["status"] != "IDLE":
                continue
            if drone["pos"] != (0, 0):
                continue
            if drone["load"] != 0:
                continue
            if drone_id in self.drone_targets:
                continue

            candidates = []

            for order in orders:

                if order["id"] in [o["id"] for o in self.drone_targets.values()]:
                    continue

                # Order analyst
                msg = A2AMessage(
                    "Orchestrator", "OrderAnalyst", "analyze",
                    {"text": order["text"]}
                )
                order["priority"] = self.order_analyst.handle(msg)

                # Safety auditor
                msg = A2AMessage(
                    "Orchestrator", "SafetyAuditor", "validate",
                    {
                        "drone": drone,
                        "order": order,
                        "weather": weather
                    }
                )
                if not self.safety_auditor.handle(msg):
                    continue

                dist = self.mcp.calculate_distance((0, 0), order["destination"])
                eta = dist / drone["speed"]

                candidates.append({
                    "drone_id": drone_id,
                    "order": order,
                    "distance": dist,
                    "eta": eta
                })

            if candidates:
                msg = A2AMessage(
                    "Orchestrator", "Allocator", "select",
                    {
                        "order": candidates[0]["order"],
                        "candidates": candidates
                    }
                )
                chosen = self.allocator.handle(msg)

                if chosen:
                    self.drone_targets[drone_id] = chosen["order"]
                    actions[drone_id] = {
                        "action": "PICKUP",
                        "params": {"order_id": chosen["order"]["id"]}
                    }

        # ---------------- MOVE / DELIVER / RETURN ----------------

        HUB = (0, 0)

        for drone_id, drone in drones.items():

            # Case 1: Drone is carrying a package → go deliver
            if drone["load"] > 0:
                order = self.drone_targets.get(drone_id)
                if not order:
                    continue

                dest = order["destination"]
                dist = self.mcp.calculate_distance(drone["pos"], dest)

                if dist < 0.5:
                    actions[drone_id] = {"action": "DELIVER", "params": {}}
                else:
                    actions[drone_id] = {
                        "action": "MOVE",
                        "params": {"target": dest}
                    }

            # Case 2: Drone is empty and NOT at hub → return immediately
            elif drone["pos"] != HUB:
                actions[drone_id] = {
                    "action": "MOVE",
                    "params": {"target": HUB}
                }

            # Case 3: Empty and already at hub → do nothing (idle)

        # ---------------- STORM RECALL ----------------

        if weather == "STORMY":
            for drone_id, drone in drones.items():
                if drone["load"] == 0 and drone["pos"] != HUB:
                    actions[drone_id] = {
                        "action": "MOVE",
                        "params": {"target": HUB}
                    }

        return actions

# ============================================================
# ENTRY POINT
# ============================================================

class KovaiAgent:
    def __init__(self):
        self.orchestrator = KovaiOrchestrator()
        self.name = self.orchestrator.name

    def decide(self, state):
        return self.orchestrator.orchestrate(state)
