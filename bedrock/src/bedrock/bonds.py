"""Module D (optional) - Bonds: is the bond market a fair-priced exit?

Status: method only. Public bond data is thin: NSE bond price lists are scanned PDFs,
and corporate bonds barely trade. Build this only if Rock Data Plus supplies
government yields and corporate bond quotes, or if the brief asks about bonds.

Method
1. Fit a Nelson-Siegel curve to government bond yields (maturity in years -> yield).
2. Corporate spread = corporate yield - government curve at the same maturity.
3. Regress spreads on rating / issuer sector / size; residual > 0 = cheap, < 0 = expensive.
Expected input: data/rock/gov_yields.csv  (date, maturity_years, yield)
                data/rock/corp_bonds.csv  (date, isin, issuer, maturity_years, yield, sector)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import least_squares


def nelson_siegel(m: np.ndarray, b0: float, b1: float, b2: float, tau: float) -> np.ndarray:
    m = np.maximum(np.asarray(m, dtype=float), 1e-6)
    x = m / tau
    f = (1 - np.exp(-x)) / x
    return b0 + b1 * f + b2 * (f - np.exp(-x))


def fit_curve(maturity: np.ndarray, yields: np.ndarray) -> dict:
    def resid(p):
        return nelson_siegel(maturity, *p) - yields
    p0 = [yields.max(), yields.min() - yields.max(), 0.0, 2.0]
    r = least_squares(resid, p0, bounds=([-50, -50, -50, 0.05], [50, 50, 50, 30]))
    return dict(zip(["b0", "b1", "b2", "tau"], r.x)) | {"rmse": float(np.sqrt(np.mean(r.fun ** 2)))}


def corporate_spreads(corp: pd.DataFrame, curve: dict) -> pd.DataFrame:
    c = corp.copy()
    c["gov_yield"] = nelson_siegel(c["maturity_years"].values, curve["b0"], curve["b1"], curve["b2"], curve["tau"])
    c["spread"] = c["yield"] - c["gov_yield"]
    return c
