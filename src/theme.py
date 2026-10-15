"""Shared page banners, so every page opens in the same visual language.

Each banner uses a shade from one blue ramp and a faint backdrop drawn from the
dashboard's own data (a miniature of that page's main chart).
"""

from __future__ import annotations

import html
import math

import numpy as np
import pandas as pd
import streamlit as st

from src.analysis import fit_line, income_fit

# One blue ramp, darkest for the overview and the conclusion (the bookends).
BANNER = {
    "overview": "#0d366b",
    "income": "#184f95",
    "gaps": "#1c5cab",
    "factors": "#256abf",
    "conclusion": "#0d366b",
    "spotlight": "#104281",
}
_DOT = "#b7d3f6"
_W, _H = 520, 220
# Text and backdrop share the banner side by side on wide screens; on a phone the
# text takes the full width and the backdrop fades further into the background.
_STYLE = ("<style>.wdi-banner-text{max-width:min(720px,60%)}.wdi-banner-art{opacity:0.85}"
          "@media (max-width:760px){.wdi-banner-text{max-width:100%}.wdi-banner-art{opacity:0.3}}</style>")


def _scale(values, low, high, out_low, out_high):
    return out_low + (np.clip(values, low, high) - low) / (high - low) * (out_high - out_low)


def _svg(body: str) -> str:
    return (f'<svg class="wdi-banner-art" viewBox="0 0 {_W} {_H}" aria-hidden="true" style="position:absolute;'
            f'right:-6px;bottom:-6px;width:min(38%,460px);height:auto">{body}</svg>')


def pattern_income(now: pd.DataFrame) -> str:
    fit = income_fit(now)
    lo, hi = math.log10(500), math.log10(200000)
    xs = _scale(np.log10(now["gdp_pc_ppp"]), lo, hi, 16, _W - 16)
    ys = _scale(now["life_expectancy"], 45, 90, _H - 16, 16)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{_DOT}" fill-opacity="0.45"/>' for x, y in zip(xs, ys))
    ends = _scale(fit.intercept + fit.slope * np.log(np.array([500.0, 200000.0])), 45, 90, _H - 16, 16)
    return _svg(dots + f'<line x1="16" y1="{ends[0]:.1f}" x2="{_W - 16}" y2="{ends[1]:.1f}" stroke="#ffffff" '
                       f'stroke-opacity="0.5" stroke-width="2.2"/>')


def pattern_gaps(now: pd.DataFrame) -> str:
    ranked = now.sort_values("residual_years", ascending=False)
    rows = pd.concat([ranked.head(6), ranked.tail(6)])
    extent = rows["residual_years"].abs().max()
    zero = _W * 0.6
    parts = [f'<line x1="{zero:.1f}" y1="6" x2="{zero:.1f}" y2="{_H - 6}" stroke="#ffffff" stroke-opacity="0.5"/>']
    for i, value in enumerate(rows["residual_years"]):
        width = abs(value) / extent * ((_W - 16 - zero) if value >= 0 else (zero - 16))
        x = zero if value >= 0 else zero - width
        parts.append(f'<rect x="{x:.1f}" y="{10 + i * 17}" width="{width:.1f}" height="11" rx="3" '
                     f'fill="{_DOT if value >= 0 else "#f7c1c1"}" fill-opacity="0.55"/>')
    return _svg("".join(parts))


def pattern_factors(now: pd.DataFrame) -> str:
    usable = now.dropna(subset=["gov_health_exp_pct_gdp"])
    fit = fit_line(usable["gov_health_exp_pct_gdp"], usable["residual_years"])
    xmax = float(usable["gov_health_exp_pct_gdp"].quantile(0.98))
    xs = _scale(usable["gov_health_exp_pct_gdp"], 0, xmax, 16, _W - 16)
    ys = _scale(usable["residual_years"], -16, 10, _H - 16, 16)
    zero_y = float(_scale(np.array([0.0]), -16, 10, _H - 16, 16)[0])
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{_DOT}" fill-opacity="0.45"/>' for x, y in zip(xs, ys))
    line_y = _scale(fit.intercept + fit.slope * np.array([0.0, xmax]), -16, 10, _H - 16, 16)
    return _svg(f'<line x1="16" y1="{zero_y:.1f}" x2="{_W - 16}" y2="{zero_y:.1f}" stroke="#ffffff" '
                f'stroke-opacity="0.45" stroke-dasharray="5 5"/>' + dots +
                f'<line x1="16" y1="{line_y[0]:.1f}" x2="{_W - 16}" y2="{line_y[1]:.1f}" stroke="#ffffff" '
                f'stroke-opacity="0.55" stroke-width="2.2"/>')


def banner(kicker: str, title: str, subtitle: str, colour: str, pattern: str = "") -> None:
    """A coloured page banner; the title is a real heading for screen readers."""
    st.markdown(
        f'{_STYLE}<div style="position:relative;overflow:hidden;border-radius:14px;background:{colour};'
        f'padding:28px 32px 26px;margin:2px 0 14px">{pattern}'
        f'<div class="wdi-banner-text" style="position:relative">'
        f'<div style="font-size:12.5px;letter-spacing:0.08em;text-transform:uppercase;color:#cde2fb">'
        f'{html.escape(kicker)}</div>'
        f'<h2 style="color:#ffffff;font-size:2rem;line-height:1.2;margin:8px 0 10px;padding:0">{html.escape(title)}</h2>'
        f'<p style="color:#e6eefb;font-size:1.02rem;line-height:1.5;margin:0">{html.escape(subtitle)}</p>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def latest(data: pd.DataFrame) -> pd.DataFrame:
    return data.loc[data["year"] == data["year"].max()]
