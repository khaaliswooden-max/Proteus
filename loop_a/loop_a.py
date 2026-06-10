#!/usr/bin/env python3
"""Proteus Loop A core — engagement signal, ACI skill proxy, flow-band controller.

Implements spec §5.1 against PROTEUS-Bench v1.0 (manifest a802d7e0…d3ff2331).

Components:
  EntropySignal       — windowed (W=64) mean pre-sampling token entropy,
                        normalized to a percentile against a frozen
                        calibration distribution (challenge proxy c_t).
  ACISkill            — Adaptive Conformal Inference (Gibbs & Candès 2021)
                        skill proxy. alpha_{t+1} = alpha_t + gamma*(alpha_target - err_t)
                        [the corrected sign — same fix as the VBX-ISPS substrate].
                        skill_t = 1 - normalized band width.
  FlowBandController  — banded controller with hysteresis (m=3).
                        Actuators: g (control-vector gain level 0-2),
                        k (retrieval depth 0-8), s (scaffold density 0-3).
                        Decoding params are never touched (cheat C3).

Provisional constants (flagged per Gap Analysis Protocol — empirically
ungrounded until F0 calibration): DELTA_LO=0.05, DELTA_HI=0.25, M=3,
GAMMA=0.05, ALPHA_TARGET=0.10.
"""
from bisect import bisect_left
from collections import deque
from statistics import mean, quantiles

DELTA_LO = 0.05
DELTA_HI = 0.25
M_HYSTERESIS = 3
GAMMA = 0.05
ALPHA_TARGET = 0.10
WINDOW = 64


class EntropySignal:
    """Challenge proxy c_t: percentile of windowed mean entropy vs calibration."""

    def __init__(self, calibration: list[float], window: int = WINDOW):
        if len(calibration) < 20:
            raise ValueError("calibration distribution too small (<20 samples)")
        self.cal = sorted(calibration)
        self.buf = deque(maxlen=window)

    def push(self, token_entropy: float) -> None:
        self.buf.append(float(token_entropy))

    def challenge(self) -> float:
        if not self.buf:
            return 0.5
        m = mean(self.buf)
        # percentile rank in the frozen calibration distribution
        return bisect_left(self.cal, m) / len(self.cal)


class ACISkill:
    """Skill proxy via Adaptive Conformal Inference band width.

    Nonconformity scores in [0,1] (1 - task quality). Coverage check uses the
    current (1 - alpha_t) empirical quantile; alpha then adapts. Skill is
    1 - band_width, so a narrow calibrated band reads as high skill.
    """

    def __init__(self, alpha_target: float = ALPHA_TARGET, gamma: float = GAMMA,
                 score_window: int = 200):
        self.alpha = alpha_target
        self.alpha_target = alpha_target
        self.gamma = gamma
        self.scores = deque(maxlen=score_window)

    def _quantile(self) -> float:
        if len(self.scores) < 10:
            return 1.0  # maximum uncertainty until calibrated
        qs = quantiles(self.scores, n=100, method="inclusive")
        idx = min(max(int(round((1.0 - self.alpha) * 100)) - 1, 0), 98)
        return min(max(qs[idx], 0.0), 1.0)

    def update(self, nonconformity: float) -> None:
        nonconformity = min(max(float(nonconformity), 0.0), 1.0)
        covered = nonconformity <= self._quantile()
        err = 0.0 if covered else 1.0
        # corrected-sign ACI update
        self.alpha = self.alpha + self.gamma * (self.alpha_target - err)
        self.alpha = min(max(self.alpha, 0.001), 0.5)
        self.scores.append(nonconformity)

    def band_width(self) -> float:
        return self._quantile()

    def skill(self) -> float:
        return 1.0 - self.band_width()


class FlowBandController:
    """Banded controller with hysteresis. Targets gap = c_t - skill_t in
    [DELTA_LO, DELTA_HI]: challenge held slightly above calibrated skill."""

    K_MAX, G_MAX, S_MAX = 8, 2, 3

    def __init__(self, d_lo: float = DELTA_LO, d_hi: float = DELTA_HI,
                 m: int = M_HYSTERESIS):
        self.d_lo, self.d_hi, self.m = d_lo, d_hi, m
        self.k = 0   # retrieval depth
        self.g = 0   # control-vector gain level (quantized, F8 rung 2)
        self.s = 0   # scaffold density tier
        self._over = 0
        self._under = 0

    def step(self, c_t: float, skill_t: float) -> dict:
        gap = c_t - skill_t
        if gap > self.d_hi:
            self._over += 1
            self._under = 0
        elif gap < self.d_lo:
            self._under += 1
            self._over = 0
        else:
            self._over = self._under = 0

        before = (self.k, self.g, self.s)
        if self._over >= self.m:          # overwhelmed: add support
            self.k = min(self.k + 1, self.K_MAX)
            self.g = min(self.g + 1, self.G_MAX)
            self.s = min(self.s + 1, self.S_MAX)
            self._over = 0
        elif self._under >= self.m:       # under-challenged: release scaffolding
            self.k = max(self.k - 1, 0)
            self.g = max(self.g - 1, 0)
            self.s = max(self.s - 1, 0)
            self._under = 0
        # An adaptation event is a CHANGE OF VALUES, not a fired branch.
        # Saturated actuators firing the branch produced signed no-op
        # transitions — the exact C5 degeneracy the committed auditor rejects
        # (caught live by verify_chain.py, exit 4, on 2026-06-09).
        changed = (self.k, self.g, self.s) != before

        return {"gap": gap, "in_band": self.d_lo <= gap <= self.d_hi,
                "k": self.k, "g": self.g, "s": self.s,
                "adaptation_event": changed}
