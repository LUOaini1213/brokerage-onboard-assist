"""Matplotlib renders of the KPIs (figures/*.png), drawn from the same numbers as the results files.

These are static stand-ins for the Power BI pages, which have not been rendered yet. Every title says the data are
SYNTHETIC. Conventions: one y-scale per chart (the Pareto puts bar shares and the cumulative line on one percentage
axis instead of two axes), a single blue for single-series charts, a fixed categorical order for multi-series
charts with a legend, values printed in ink colours rather than series colours, hairline grid.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import kpis as K  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]   # categorical slots 1-4, fixed order
BLUE = SERIES[0]


def _axes(figsize, title, subtitle):
    fig, ax = plt.subplots(figsize=figsize, dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.set_axisbelow(True)
    fig.suptitle(title, x=0.02, y=0.98, ha="left", va="top", fontsize=11, fontweight="bold", color=INK)
    fig.text(0.02, 0.915, subtitle, ha="left", va="top", fontsize=8, color=INK2)
    return fig, ax


def _save(fig, path, top=0.84):
    fig.tight_layout(rect=(0, 0, 1, top))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def _hbars(ax, labels, values, fmt, color=BLUE, xmax=None):
    y = list(range(len(labels)))[::-1]
    ax.barh(y, values, height=0.5, color=color, edgecolor=SURFACE, linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=INK2, fontsize=8)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    top = xmax or max(values) * 1.18
    ax.set_xlim(0, top)
    for yi, v in zip(y, values):
        ax.text(v + top * 0.01, yi, fmt(v), va="center", ha="left", fontsize=8, color=INK)


def funnel(out, frames):
    stages = list(frames["DimStage"].sort_values("StageOrder")["Stage"])
    counts = [K.value("Enrolments at Stage", frames, {"DimStage.Stage": {s}}) or 0 for s in stages]
    fig, ax = _axes((7.2, 3.4), "Onboarding funnel (SYNTHETIC data)",
                    "Enrolment requests that reached each stage; percentage of submitted requests")
    _hbars(ax, stages, counts, lambda v: f"{v:,.0f}  ({v / counts[0]:.0%})")
    ax.set_xlabel("enrolment requests", fontsize=8, color=MUTED)
    _save(fig, out / "onboarding_funnel.png")


def hold_rate_by_seq(out, rates):
    rows = rates["shipment_seq"]
    fig, ax = _axes((4.6, 3.4), "Hold rate by shipment number (SYNTHETIC data)",
                    "Share of each new customer's 1st, 2nd and 3rd shipment with a hold")
    x = [str(r["shipment_seq"]) for r in rows]
    vals = [100 * r["hold_rate"] for r in rows]
    ax.bar(x, vals, width=0.4, color=BLUE)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_ylim(0, max(vals) * 1.2)
    ax.set_ylabel("% of shipments held", fontsize=8, color=MUTED)
    ax.set_xlabel("shipment number", fontsize=8, color=MUTED)
    for xi, (v, r) in enumerate(zip(vals, rows)):
        ax.text(xi, v + max(vals) * 0.02, f"{v:.1f}%\n{r['held']} of {r['shipments']}", ha="center", va="bottom",
                fontsize=8, color=INK)
    _save(fig, out / "hold_rate_by_shipment_number.png")


def pareto(out, par):
    fig, ax = _axes((8.2, 4.0), "Hold-reason Pareto (SYNTHETIC data)",
                    "Bars: share of all holds; line: cumulative share. One percentage axis; hold counts above the bars")
    x = list(range(len(par)))
    share = [100 * r["share"] for r in par]
    cum = [100 * r["cumulative_share"] for r in par]
    ax.bar(x, share, width=0.5, color=SERIES[0], label="share of holds")
    ax.plot(x, cum, color=SERIES[1], linewidth=2, marker="o", markersize=6, markeredgecolor=SURFACE,
            markeredgewidth=1.5, label="cumulative share")
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_ylim(0, 108)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("% of holds", fontsize=8, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels([r["reason_code"].replace("_", "\n") for r in par], fontsize=7, color=INK2)
    for xi, r, s in zip(x, par, share):
        ax.text(xi, s + 1.5, str(r["holds"]), ha="center", va="bottom", fontsize=8, color=INK)
    ax.text(x[-1], cum[-1] + 2.5, "100%", ha="center", va="bottom", fontsize=8, color=INK)
    k = next(i for i, c in enumerate(cum) if c >= 80)
    ax.text(x[k], cum[k] + 2.5, f"{cum[k]:.0f}%", ha="center", va="bottom", fontsize=8, color=INK)
    ax.legend(loc="center right", frameon=False, fontsize=8, labelcolor=INK2)
    _save(fig, out / "hold_reason_pareto.png")


def clearance_by_lane(out, clr):
    rows = sorted(clr, key=lambda r: -r["median_hours"])
    fig, ax = _axes((7.2, 3.8), "Clearance lead time by lane (SYNTHETIC data)",
                    "Hours from arrival to release, time on hold included: median and 90th percentile")
    y = list(range(len(rows)))[::-1]
    for yi, r in zip(y, rows):
        ax.plot([r["median_hours"], r["p90_hours"]], [yi, yi], color=AXIS, linewidth=1.5, zorder=1)
    ax.scatter([r["median_hours"] for r in rows], y, s=52, color=SERIES[0], edgecolor=SURFACE, linewidth=1.5,
               zorder=2, label="median")
    ax.scatter([r["p90_hours"] for r in rows], y, s=52, color=SERIES[1], edgecolor=SURFACE, linewidth=1.5,
               zorder=2, label="90th percentile")
    ax.set_yticks(y)
    ax.set_yticklabels([r["lane_id"] for r in rows], fontsize=8, color=INK2)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_xlim(0, max(r["p90_hours"] for r in rows) * 1.12)
    ax.set_xlabel("hours", fontsize=8, color=MUTED)
    for yi, r in zip(y, rows):
        ax.text(r["p90_hours"] + 2, yi, f"{r['median_hours']:.0f} / {r['p90_hours']:.0f} h", va="center",
                fontsize=8, color=INK)
    ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK2)
    _save(fig, out / "clearance_by_lane.png")


def release_by_reason(out, rel):
    rows = sorted(rel, key=lambda r: -r["median_hours"])
    fig, ax = _axes((7.2, 3.8), "Median hours from hold to release, by reason (SYNTHETIC data)",
                    "Released holds only; number of holds in brackets")
    _hbars(ax, [r["reason_code"] for r in rows], [r["median_hours"] for r in rows], lambda v: f"{v:.1f} h")
    ax.set_yticklabels([f"{r['reason_code']} ({r['holds']})" for r in rows], fontsize=8, color=INK2)
    ax.set_xlabel("hours", fontsize=8, color=MUTED)
    _save(fig, out / "release_hours_by_reason.png")


def classifier(out, metrics):
    methods = [("tfidf_logreg", "TF-IDF + logistic regression"), ("keyword_rules", "keyword rules"),
               ("majority", "majority class")]
    llm = metrics.get("llm", {})
    splits = [("seen", "seen-template test"), ("heldout", "held-out-template test")]
    series = [(label, [metrics[s][key]["accuracy"] for s, _ in splits]) for key, label in methods]
    if all(isinstance(llm.get(s), dict) and "accuracy" in llm[s] for s, _ in splits):
        series.append((f"local LLM ({llm['model']}, zero-shot)", [llm[s]["accuracy"] for s, _ in splits]))
    fig, ax = _axes((7.6, 3.8), "Hold-note classifier accuracy (SYNTHETIC notes)",
                    "Same test notes for every method; held-out templates are phrasings never seen in training")
    width = 0.8 / len(series)
    for i, (label, vals) in enumerate(series):
        xs = [j - 0.4 + width * (i + 0.5) for j in range(len(splits))]
        ax.bar(xs, [100 * v for v in vals], width=width * 0.86, color=SERIES[i], label=label)
        for x, v in zip(xs, vals):
            ax.text(x, 100 * v + 1.5, f"{100 * v:.0f}%", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_xticks(range(len(splits)))
    ax.set_xticklabels([f"{name}\n(n = {metrics[s]['tfidf_logreg']['n']})" for s, name in splits], fontsize=8,
                       color=INK2)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("accuracy, %", fontsize=8, color=MUTED)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False, fontsize=8, labelcolor=INK2)
    _save(fig, out / "classifier_accuracy.png")


def draw_all(out_root, frames, par, rel_r, clr, rates, metrics):
    out = Path(out_root) / "figures"
    funnel(out, frames)
    hold_rate_by_seq(out, rates)
    pareto(out, par)
    clearance_by_lane(out, clr)
    release_by_reason(out, rel_r)
    classifier(out, metrics)
