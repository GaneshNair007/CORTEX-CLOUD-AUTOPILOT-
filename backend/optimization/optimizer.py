"""
CORTEX Cloud Autopilot — Multi-Objective Optimizer
Evaluates candidate infrastructure configurations across Cost, Latency, Reliability, SLO Risk, and Carbon.
Computes the Pareto-optimal frontier and selects candidates based on operational mode.
"""

from typing import Dict, Any, List, Optional
import math


class CandidateConfiguration:
    def __init__(
        self,
        name: str,
        replicas: int,
        estimated_cost_per_hr: float,
        expected_p95_ms: float,
        reliability_risk_score: float,
        slo_violation_probability: float,
        energy_kwh_per_hr: float,
        carbon_gco2_per_hr: float,
        change_risk_score: float
    ):
        self.name = name
        self.replicas = replicas
        self.estimated_cost_per_hr = round(estimated_cost_per_hr, 2)
        self.expected_p95_ms = round(expected_p95_ms, 1)
        self.reliability_risk_score = round(reliability_risk_score, 1)
        self.slo_violation_probability = round(slo_violation_probability, 3)
        self.energy_kwh_per_hr = round(energy_kwh_per_hr, 3)
        self.carbon_gco2_per_hr = round(carbon_gco2_per_hr, 1)
        self.change_risk_score = round(change_risk_score, 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "replicas": self.replicas,
            "estimated_cost_per_hr": self.estimated_cost_per_hr,
            "expected_p95_ms": self.expected_p95_ms,
            "reliability_risk_score": self.reliability_risk_score,
            "slo_violation_probability": self.slo_violation_probability,
            "energy_kwh_per_hr": self.energy_kwh_per_hr,
            "carbon_gco2_per_hr": self.carbon_gco2_per_hr,
            "change_risk_score": self.change_risk_score,
            "slo_status": "PASS" if self.expected_p95_ms <= 200.0 and self.slo_violation_probability <= 0.05 else "RISK"
        }


class MultiObjectiveOptimizer:
    def __init__(self):
        self.mode_weights = {
            "BALANCED": {"cost": 0.25, "latency": 0.25, "reliability": 0.25, "slo": 0.25, "energy": 0.0},
            "COST": {"cost": 0.55, "latency": 0.15, "reliability": 0.15, "slo": 0.15, "energy": 0.0},
            "PERFORMANCE": {"cost": 0.10, "latency": 0.50, "reliability": 0.20, "slo": 0.20, "energy": 0.0},
            "RELIABILITY": {"cost": 0.10, "latency": 0.20, "reliability": 0.45, "slo": 0.25, "energy": 0.0},
            "GREEN": {"cost": 0.15, "latency": 0.15, "reliability": 0.20, "slo": 0.20, "energy": 0.30},
            "EMERGENCY": {"cost": 0.00, "latency": 0.30, "reliability": 0.40, "slo": 0.30, "energy": 0.0}
        }

    def generate_candidates(self, current_replicas: int = 6, forecast_rps: float = 480.0) -> List[CandidateConfiguration]:
        """Generates candidate capacity configurations for payment-api."""
        replica_options = [4, 6, 8, 9, 11, 14]
        candidates = []

        cost_per_pod_hr = 0.08  # e.g. 0.5 vCPU + 1GB RAM on AWS/GCP
        pue = 1.15  # Data center Power Usage Effectiveness
        watt_per_pod = 22.0  # Estimated average active watts
        regional_carbon_intensity = 380.0  # gCO2/kWh (us-east-1 grid average)

        for reps in replica_options:
            cost = reps * cost_per_pod_hr
            # Calibrated queuing delay approximation for p95 latency
            capacity = reps * 60.0
            load_factor = min(0.95, forecast_rps / max(capacity, 1.0))
            expected_p95 = max(55.0, 75.0 + (25.0 * (load_factor ** 2) / max(0.08, 1.0 - load_factor)))

            # Reliability risk is higher if redundancy is minimal or load factor is near saturation
            if load_factor > 0.85:
                rel_risk = 65.0 + (load_factor - 0.85) * 200.0
                slo_prob = min(0.45, (load_factor - 0.80) * 2.0)
            else:
                rel_risk = max(10.0, (1.0 - (reps / 14.0)) * 30.0)
                slo_prob = 0.005

            energy_kwh = (reps * watt_per_pod * pue) / 1000.0
            carbon_g = energy_kwh * regional_carbon_intensity
            change_delta = abs(reps - current_replicas)
            change_risk = min(change_delta * 4.0, 30.0)

            name = f"{reps} Replicas"
            if reps == current_replicas:
                name += " (Current)"

            candidates.append(CandidateConfiguration(
                name=name,
                replicas=reps,
                estimated_cost_per_hr=cost,
                expected_p95_ms=expected_p95,
                reliability_risk_score=min(100.0, rel_risk),
                slo_violation_probability=slo_prob,
                energy_kwh_per_hr=energy_kwh,
                carbon_gco2_per_hr=carbon_g,
                change_risk_score=change_risk
            ))

        return candidates

    def compute_pareto_frontier(self, candidates: List[CandidateConfiguration]) -> List[CandidateConfiguration]:
        """Identifies non-dominated Pareto candidates considering Cost and p95 Latency."""
        pareto = []
        for c1 in candidates:
            is_dominated = False
            for c2 in candidates:
                if c1.replicas == c2.replicas:
                    continue
                # c2 dominates c1 if it is both cheaper AND faster
                if c2.estimated_cost_per_hr <= c1.estimated_cost_per_hr and c2.expected_p95_ms <= c1.expected_p95_ms:
                    if c2.estimated_cost_per_hr < c1.estimated_cost_per_hr or c2.expected_p95_ms < c1.expected_p95_ms:
                        is_dominated = True
                        break
            if not is_dominated:
                pareto.append(c1)
        return pareto if pareto else candidates

    def optimize(self, mode: str = "BALANCED", current_replicas: int = 6, forecast_rps: float = 480.0) -> Dict[str, Any]:
        """
        Calculates candidate scores, identifies Pareto frontier, and selects best option.
        """
        mode = mode.upper()
        if mode not in self.mode_weights:
            mode = "BALANCED"

        weights = self.mode_weights[mode]
        candidates = self.generate_candidates(current_replicas, forecast_rps)
        pareto_candidates = self.compute_pareto_frontier(candidates)

        scored_candidates = []
        best_candidate = None
        min_loss = float("inf")

        for c in candidates:
            # Normalized losses (lower is better)
            norm_cost = c.estimated_cost_per_hr / 1.50
            norm_lat = min(1.0, c.expected_p95_ms / 350.0)
            norm_rel = c.reliability_risk_score / 100.0
            norm_slo = c.slo_violation_probability / 0.50
            norm_energy = c.energy_kwh_per_hr / 0.50

            loss = (
                weights["cost"] * norm_cost +
                weights["latency"] * norm_lat +
                weights["reliability"] * norm_rel +
                weights["slo"] * norm_slo +
                weights.get("energy", 0.0) * norm_energy
            )

            is_pareto = any(p.replicas == c.replicas for p in pareto_candidates)
            c_dict = c.to_dict()
            c_dict["composite_loss"] = round(loss, 3)
            c_dict["is_pareto"] = is_pareto
            scored_candidates.append(c_dict)

            # Hard constraints: p95 must be <= 200ms SLO except under emergency
            if c.expected_p95_ms <= 200.0 or mode == "EMERGENCY":
                if loss < min_loss:
                    min_loss = loss
                    best_candidate = c_dict

        if not best_candidate:
            best_candidate = scored_candidates[2]  # Fallback to middle safe candidate

        return {
            "mode": mode,
            "weights": weights,
            "current_replicas": current_replicas,
            "forecast_rps": forecast_rps,
            "recommended_replicas": best_candidate["replicas"],
            "trade_offs": {
                "latency_ms": best_candidate["expected_p95_ms"],
                "hourly_cost_usd": best_candidate["estimated_cost_per_hr"]
            },
            "candidates": scored_candidates,
            "selected_candidate": best_candidate,
            "pareto_count": len(pareto_candidates),
            "selection_rationale": (
                f"Under mode '{mode}', selected '{best_candidate['name']}' with composite score {best_candidate['composite_loss']}. "
                f"Expected p95: {best_candidate['expected_p95_ms']}ms (SLO: 200ms), Est cost: ${best_candidate['estimated_cost_per_hr']}/hr."
            )
        }


# Global singleton optimizer instance
optimizer = MultiObjectiveOptimizer()
