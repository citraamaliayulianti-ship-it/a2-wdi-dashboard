"""Small, dependency-light statistics shared by the pipeline and the views.

The dashboard asks how closely life expectancy follows income. For each year
we fit one ordinary least squares line across countries:

    life_expectancy = a + b * ln(GDP per capita, PPP)

Every country counts once (no population weighting). The *residual* is the
gap between a country's actual life expectancy and the value the line
predicts for its income: positive means people live longer than countries
with similar incomes, negative means shorter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LineFit:
    intercept: float
    slope: float
    r_squared: float
    n: int

    @property
    def correlation(self) -> float:
        """Pearson r, carrying the sign of the slope."""
        return math.copysign(math.sqrt(max(self.r_squared, 0.0)), self.slope)


def fit_line(x: pd.Series, y: pd.Series) -> LineFit:
    """Ordinary least squares fit of y on x, ignoring rows with a missing value."""
    pairs = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(pairs) < 3:
        raise ValueError("At least three complete observations are needed for a line fit")
    xs = pairs["x"].to_numpy(dtype=float)
    ys = pairs["y"].to_numpy(dtype=float)
    x_mean, y_mean = xs.mean(), ys.mean()
    sxx = float(((xs - x_mean) ** 2).sum())
    if sxx == 0:
        raise ValueError("x has no variation, so no line can be fitted")
    slope = float(((xs - x_mean) * (ys - y_mean)).sum()) / sxx
    intercept = y_mean - slope * x_mean
    fitted = intercept + slope * xs
    ss_res = float(((ys - fitted) ** 2).sum())
    ss_tot = float(((ys - y_mean) ** 2).sum())
    r_squared = 1 - ss_res / ss_tot if ss_tot else 0.0
    return LineFit(float(intercept), slope, r_squared, len(pairs))


def income_fit(year_frame: pd.DataFrame) -> LineFit:
    """Fit life expectancy on log income for one year of country data."""
    return fit_line(np.log(year_frame["gdp_pc_ppp"].astype(float)), year_frame["life_expectancy"].astype(float))


def add_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    """Add predicted life expectancy and the residual gap, fitted separately for each year."""
    result = frame.copy()
    result["predicted_life_expectancy"] = np.nan
    result["residual_years"] = np.nan
    for _, rows in result.groupby("year", sort=True):
        fit = income_fit(rows)
        predicted = fit.intercept + fit.slope * np.log(rows["gdp_pc_ppp"].astype(float))
        result.loc[rows.index, "predicted_life_expectancy"] = predicted.round(3)
        result.loc[rows.index, "residual_years"] = (rows["life_expectancy"].astype(float) - predicted).round(3)
    return result


def describe_strength(r: float) -> str:
    """Plain-language label for the size of a correlation coefficient."""
    size = abs(r)
    if size < 0.1:
        return "very weak"
    if size < 0.3:
        return "weak"
    if size < 0.5:
        return "moderate"
    return "strong"
