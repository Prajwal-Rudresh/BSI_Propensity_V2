"""Generate confusion-matrix 'dashboard card' PNGs, before vs after, for all 4 combos."""
import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent / "reports" / "figures"

NAVY = "#1B3C59"
NAVY_DARK = "#122A40"
BLUE_BG = "#E3EEF5"
BLUE_TXT = "#1B3C59"
AMBER_BG = "#FCEFDC"
AMBER_TXT = "#A65E00"
GRAY = "#5B6672"
GRAY_BG = "#EEF1F3"
WHITE = "#FFFFFF"
TEAL = "#2E7D6B"

COMBOS = {
    "fha_same-window": dict(
        label="FHA \u2014 Same-window model (Dec'25\u2013Feb'26 training)",
        tp_b=170, fp_b=13882, fn_b=68, tn_b=19685,
        tp_a=132, fp_a=9345, fn_a=106, tn_a=24222,
    ),
    "fha_production-window": dict(
        label="FHA \u2014 Production-window model (12-month rolling training)",
        tp_b=168, fp_b=13600, fn_b=70, tn_b=19967,
        tp_a=148, fp_a=9009, fn_a=90, tn_a=24558,
    ),
    "conventional_same-window": dict(
        label="Conventional \u2014 Same-window model (Dec'25\u2013Feb'26 training)",
        tp_b=144, fp_b=22223, fn_b=79, tn_b=48932,
        tp_a=120, fp_a=17966, fn_a=103, tn_a=53189,
    ),
    "conventional_production-window": dict(
        label="Conventional \u2014 Production-window model (12-month rolling training)",
        tp_b=143, fp_b=21688, fn_b=80, tn_b=49467,
        tp_a=130, fp_a=19320, fn_a=93, tn_a=51835,
    ),
}


def fmt(n):
    return f"{n:,}"


def wrap(text, width):
    return "\n".join(textwrap.wrap(text, width=width))


def draw_card(fname, eyebrow, title, subtitle, tp, fp, fn, tn, footer_kind, footer_data):
    n_loans = tp + fp + fn + tn
    n_refi = tp + fn
    n_norefi = fp + tn
    n_flagged = tp + fp
    recall = tp / n_refi if n_refi else 0
    precision = tp / n_flagged if n_flagged else 0
    pct_flagged = n_flagged / n_loans if n_loans else 0

    fig = plt.figure(figsize=(11.6, 7.4), dpi=150)
    fig.patch.set_facecolor(WHITE)

    # ---- eyebrow + title + subtitle ----
    fig.text(0.045, 0.962, eyebrow, fontsize=11, color=TEAL, fontweight="bold", fontfamily="sans-serif")
    fig.text(0.045, 0.912, title, fontsize=20, color=NAVY, fontweight="bold", fontfamily="sans-serif")
    fig.text(0.045, 0.865, wrap(subtitle, 92), fontsize=10.5, color=GRAY, fontfamily="sans-serif", va="top")
    fig.add_artist(plt.Line2D([0.045, 0.975], [0.800, 0.800], color="#D9622A", linewidth=2.2, transform=fig.transFigure))

    # ---- vertical budget ----
    label_y = 0.765          # "PREDICTED BY THE SCORE" / "THREE WAYS TO READ IT"
    header_y = 0.715         # column headers
    my, mh = 0.185, 0.49     # matrix grid box (bottom y, height)
    mx, mw = 0.175, 0.40
    col_w = mw / 2
    row_h = mh / 2

    fig.text(mx + mw * 0.5, label_y, "PREDICTED BY THE SCORE", fontsize=8.5, color=GRAY, ha="center", fontweight="bold")
    fig.text(mx + col_w * 0.5, header_y, "Not Flagged", fontsize=11.5, color=NAVY, fontweight="bold", ha="center")
    fig.text(mx + col_w * 1.5, header_y, "Flagged Yes", fontsize=11.5, color=NAVY, fontweight="bold", ha="center")

    fig.text(mx - 0.018, my + row_h * 1.5, "Did not\nrefinance", fontsize=10, color=NAVY, fontweight="bold", ha="right", va="center")
    fig.text(mx - 0.018, my + row_h * 0.5, "Refinanced", fontsize=10, color=NAVY, fontweight="bold", ha="right", va="center")
    fig.text(0.05, my + mh * 0.5, "ACTUAL\n(JUN+JUL+AUG)", fontsize=7.5, color=GRAY, ha="center", va="center", rotation=90, fontweight="bold")

    cells = [
        (0, 1, tn, "Correctly\nSkipped", True),
        (1, 1, fp, "Flagged,\nNo Refi", False),
        (0, 0, fn, "Not\nCaught", False),
        (1, 0, tp, "Caught", True),
    ]
    for col, row, val, label, correct in cells:
        x0 = mx + col * col_w
        y0 = my + row * row_h
        bg = BLUE_BG if correct else AMBER_BG
        txt = BLUE_TXT if correct else AMBER_TXT
        rect = mpatches.FancyBboxPatch((x0 + 0.006, y0 + 0.012), col_w - 0.012, row_h - 0.024,
                                        boxstyle="round,pad=0.002,rounding_size=0.01",
                                        linewidth=0, facecolor=bg, transform=fig.transFigure, zorder=1)
        fig.add_artist(rect)
        fig.text(x0 + col_w * 0.5, y0 + row_h * 0.60, fmt(val), fontsize=23, color=txt, fontweight="bold", ha="center", va="center")
        fig.text(x0 + col_w * 0.5, y0 + row_h * 0.27, label, fontsize=9.5, color=txt, ha="center", va="center")

    # totals column
    tcx = mx + mw + 0.045
    fig.text(tcx, my + row_h * 1.5, fmt(n_norefi), fontsize=12, color=NAVY, fontweight="bold", ha="left", va="center")
    fig.text(tcx, my + row_h * 1.5 - 0.038, "did not refi", fontsize=8, color=GRAY, ha="left", va="center")
    fig.text(tcx, my + row_h * 0.5, fmt(n_refi), fontsize=12, color=NAVY, fontweight="bold", ha="left", va="center")
    fig.text(tcx, my + row_h * 0.5 - 0.038, "refinanced", fontsize=8, color=GRAY, ha="left", va="center")
    fig.text(mx + mw * 0.5, my - 0.045, f"TOTAL LOANS SCORED: {fmt(n_loans)}", fontsize=9, color=GRAY, ha="center", fontweight="bold")

    # ---- sidebar ----
    sx = 0.675
    sw = 0.975 - sx
    fig.text(sx, label_y, "THREE WAYS TO READ IT", fontsize=8.5, color=GRAY, fontweight="bold")
    stats = [
        (NAVY, f"{recall:.0%}", "CAUGHT", f"How many did it see coming? {fmt(tp)} of {fmt(n_refi)} refinancers were flagged."),
        (AMBER_TXT, f"{precision:.2%}", "HIT RATE", f"How often did a flag lead to a refinance? {fmt(tp)} of {fmt(n_flagged)}."),
        (GRAY, f"{pct_flagged:.0%}", "SHARE FLAGGED", f"How much of the book got flagged? {fmt(n_flagged)} of {fmt(n_loans)} loans."),
    ]
    box_h = 0.155
    gap = 0.018
    top = header_y - 0.01
    for i, (color, big, small, desc) in enumerate(stats):
        by = top - i * (box_h + gap)
        bg = {NAVY: BLUE_BG, AMBER_TXT: AMBER_BG, GRAY: GRAY_BG}[color]
        rect = mpatches.Rectangle((sx, by - box_h), sw, box_h, facecolor=bg, edgecolor=color, linewidth=0, transform=fig.transFigure)
        fig.add_artist(rect)
        bar = mpatches.Rectangle((sx, by - box_h), 0.007, box_h, facecolor=color, transform=fig.transFigure)
        fig.add_artist(bar)
        fig.text(sx + 0.028, by - 0.048, big, fontsize=16, color=color, fontweight="bold", va="top")
        fig.text(sx + sw - 0.016, by - 0.022, small, fontsize=7.3, color=color, fontweight="bold", ha="right", va="top")
        fig.text(sx + 0.028, by - box_h + 0.016, wrap(desc, 36), fontsize=7.6, color="#33363B", va="bottom", linespacing=1.3)

    # ---- footer dark bar ----
    fy0, fy1 = 0.025, 0.125
    footer_rect = mpatches.Rectangle((0.045, fy0), 0.93, fy1 - fy0, facecolor=NAVY_DARK, transform=fig.transFigure)
    fig.add_artist(footer_rect)
    if footer_kind == "before":
        cols = footer_data
        colw = 0.93 / len(cols)
        for i, (ftitle, fbody) in enumerate(cols):
            fx = 0.045 + i * colw + 0.022
            fig.text(fx, fy1 - 0.022, ftitle, fontsize=8, color="#F0A860", fontweight="bold", va="top")
            fig.text(fx, fy1 - 0.045, wrap(fbody, 33), fontsize=8.3, color="white", va="top", linespacing=1.35)
    else:
        ftitle, fbody = footer_data
        fig.text(0.07, fy1 - 0.022, ftitle, fontsize=8, color="#7FD6C2", fontweight="bold", va="top")
        fig.text(0.07, fy1 - 0.045, wrap(fbody, 118), fontsize=8.8, color="white", va="top", linespacing=1.4)

    fig.text(0.045, 0.005, "SOURCE: scripts/final_before_after.py  \u2014  Apr+May 2026-trained models scored on Jun 2026, checked against Jun+Jul+Aug 2026 actual refis",
              fontsize=6.3, color="#9AA3AC")

    out = OUT_DIR / fname
    fig.savefig(out, facecolor=WHITE)
    plt.close(fig)
    print("wrote", out)


def main():
    for key, d in COMBOS.items():
        tp_b, fp_b, fn_b, tn_b = d["tp_b"], d["fp_b"], d["fn_b"], d["tn_b"]
        tp_a, fp_a, fn_a, tn_a = d["tp_a"], d["fp_a"], d["fn_a"], d["tn_a"]
        n_flagged_b = tp_b + fp_b
        n_flagged_a = tp_a + fp_a
        names_per_catch_b = n_flagged_b / tp_b
        names_per_catch_a = n_flagged_a / tp_a
        recall_b = tp_b / (tp_b + fn_b)
        recall_a = tp_a / (tp_a + fn_a)

        draw_card(
            f"cm_dashboard_{key}_before.png",
            "THE CONFUSION MATRIX \u2014 BEFORE",
            "Actual vs Predicted: What the Legacy Flag Gets Right",
            d["label"] + " \u2014 scored with the original 0.025 cutoff + 3 overrides.",
            tp_b, fp_b, fn_b, tn_b,
            "before",
            [
                ("WHAT WORKS", f"Catches {recall_b:.0%} of true refinancers ({tp_b} of {tp_b+fn_b})."),
                ("WHAT TO IMPROVE", f"The list is long: about {names_per_catch_b:.0f} names flagged for every refinancer it finds."),
                ("THE FIX", "Replace the fixed 0.025 cutoff with the model's own trained threshold \u2014 see the After card."),
            ],
        )
        draw_card(
            f"cm_dashboard_{key}_after.png",
            "THE CONFUSION MATRIX \u2014 AFTER THE FIXES",
            "Actual vs Predicted: What the Fixed Flag Gets Right",
            d["label"] + " \u2014 scored with the fixed pipeline + the model's own best_threshold + 3 overrides.",
            tp_a, fp_a, fn_a, tn_a,
            "after",
            (
                "WHAT CHANGED",
                f"Trade-off, not a pure win: {tp_b - tp_a} fewer refinancers caught ({tp_a} vs {tp_b}, recall {recall_a:.0%} vs {recall_b:.0%}), "
                f"but the flagged list shrank by {n_flagged_b - n_flagged_a:,} loans \u2014 about {names_per_catch_a:.0f} names per refinancer found, down from {names_per_catch_b:.0f}.",
            ),
        )


if __name__ == "__main__":
    main()
