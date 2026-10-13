"""Small, dependency-light statistics shared by the pipeline and the views.

The dashboard asks how closely life expectancy follows income. For each year
we fit one ordinary least squares line across countries:

    life_expectancy = a + b * ln(GDP per capita, PPP)

Every country counts once (no population weighting). The *residual* is the
gap between a country's actual life expectancy and the value the line
predicts for its income: positive means people live longer than countries
with similar incomes, negative means shorter.

Uncertainty is reported as approximate 95% confidence intervals: for a slope,
slope ± 1.96 standard errors; for a correlation, Fisher's z transformation.
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
    slope_se: float = float("nan")

    @property
    def correlation(self) -> float:
        """Pearson r, carrying the sign of the slope."""
        return math.copysign(math.sqrt(max(self.r_squared, 0.0)), self.slope)

    def slope_ci(self, scale: float = 1.0) -> tuple[float, float]:
        """Approximate 95% confidence interval for the slope (optionally rescaled)."""
        return (self.slope - Z95 * self.slope_se) * scale, (self.slope + Z95 * self.slope_se) * scale

    def correlation_ci(self) -> tuple[float, float]:
        """Approximate 95% confidence interval for Pearson r (Fisher z transformation)."""
        r = min(max(self.correlation, -0.999999), 0.999999)
        z, se = math.atanh(r), 1 / math.sqrt(max(self.n - 3, 1))
        return math.tanh(z - Z95 * se), math.tanh(z + Z95 * se)


Z95 = 1.96


def includes_zero(interval: tuple[float, float]) -> bool:
    return interval[0] <= 0 <= interval[1]


def format_interval(interval: tuple[float, float], spec: str = "+.2f") -> str:
    return f"{interval[0]:{spec}} to {interval[1]:{spec}}"


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
    slope_se = math.sqrt(ss_res / (len(pairs) - 2) / sxx)
    return LineFit(float(intercept), slope, r_squared, len(pairs), slope_se)


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


def country_changes(data: pd.DataFrame) -> pd.DataFrame:
    """Change within each country between the first and last year in the data."""
    first, last = int(data["year"].min()), int(data["year"].max())
    start = data.loc[data["year"] == first].set_index("country_code")
    end = data.loc[data["year"] == last].set_index("country_code")
    common = start.index.intersection(end.index)
    changes = pd.DataFrame({
        "country": end.loc[common, "country"],
        "income_group": end.loc[common, "income_group"],
        "region": end.loc[common, "region"],
        "income_ratio": end.loc[common, "gdp_pc_ppp"] / start.loc[common, "gdp_pc_ppp"],
        "life_expectancy_change": end.loc[common, "life_expectancy"] - start.loc[common, "life_expectancy"],
    })
    changes["log_income_change"] = np.log(changes["income_ratio"])
    return changes.reset_index()


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
