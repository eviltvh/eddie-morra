"""
chart.py — Generador de gráfica polar (radar) del stack cognitivo
"""
import io
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

from substances import SUBSTANCES, SUBSTANCE_MAP, DOMAIN_LABELS, WASHOUT_SUSPEND


# Paleta Eddie Morra — oscuro con acento cyan/azul
BG_COLOR      = "#0a0a0f"
GRID_COLOR    = "#1e2030"
AXIS_COLOR    = "#2a2d45"
FULL_COLOR    = "#1a3a5c"   # azul muy oscuro — stack teórico completo
ACTIVE_COLOR  = "#00d4ff"   # cyan brillante — tu stack activo
INACTIVE_FILL = "#ff4060"   # rojo — lo que falta
TEXT_COLOR    = "#e0e8ff"
LABEL_COLOR   = "#7090cc"
ACCENT        = "#00d4ff"


def compute_domain_scores(available_ids: list, phase: str) -> dict:
    """
    Suma ponderada de los dominios para las sustancias activas del usuario.
    Retorna dos dicts: scores del usuario y scores del stack completo.
    """
    domains = list(DOMAIN_LABELS.keys())

    # Stack completo teórico (todas las sustancias en maintenance)
    full_scores = {d: 0.0 for d in domains}
    for s in SUBSTANCES:
        for d in domains:
            full_scores[d] += s["domains"].get(d, 0)

    # Stack del usuario según disponibilidad y fase
    user_scores = {d: 0.0 for d in domains}
    is_rest = _is_rest_day()

    for s in SUBSTANCES:
        sid = s["id"]
        if sid not in available_ids:
            continue
        # Washout: suspender ciclables
        if phase == "washout" and sid in WASHOUT_SUSPEND:
            continue
        # Drug holiday: suspender boost en descanso
        if is_rest and s["slot"] == "boost":
            continue
        for d in domains:
            user_scores[d] += s["domains"].get(d, 0)

    # Normalizar sobre el máximo teórico
    user_norm = {}
    full_norm = {}
    for d in domains:
        mx = full_scores[d] if full_scores[d] > 0 else 1
        user_norm[d] = min(user_scores[d] / mx, 1.0)
        full_norm[d] = 1.0

    return user_norm, full_norm


def _is_rest_day() -> bool:
    from datetime import date
    return date.today().weekday() >= 5


def generate_radar(available_ids: list, phase: str, username: str = "Eddie") -> bytes:
    """
    Genera la gráfica polar y retorna los bytes de la imagen PNG.
    """
    user_scores, full_scores = compute_domain_scores(available_ids, phase)
    domains = list(DOMAIN_LABELS.keys())
    labels  = [DOMAIN_LABELS[d] for d in domains]
    N = len(domains)

    # Ángulos para cada eje (cerramos el polígono repitiendo el primero)
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    angles += angles[:1]

    user_vals = [user_scores[d] for d in domains] + [user_scores[domains[0]]]
    full_vals = [full_scores[d] for d in domains] + [full_scores[domains[0]]]

    # ── Figura ───────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(7, 7.5), facecolor=BG_COLOR)
    ax  = fig.add_subplot(111, polar=True, facecolor=BG_COLOR)

    # Grilla
    ax.set_facecolor(BG_COLOR)
    levels = [0.25, 0.5, 0.75, 1.0]
    for lvl in levels:
        ring_vals = [lvl] * N + [lvl]
        ax.plot(angles, ring_vals, color=GRID_COLOR, linewidth=0.8, linestyle="-", zorder=1)
        ax.fill(angles, ring_vals, alpha=0.0)

    # Ejes radiales
    for angle in angles[:-1]:
        ax.plot([angle, angle], [0, 1], color=AXIS_COLOR, linewidth=0.8, zorder=1)

    # Área stack completo (referencia tenue)
    ax.fill(angles, full_vals, color=FULL_COLOR, alpha=0.25, zorder=2)
    ax.plot(angles, full_vals, color=FULL_COLOR, linewidth=1.2,
            linestyle="--", alpha=0.5, zorder=2)

    # Área stack activo del usuario
    ax.fill(angles, user_vals, color=ACTIVE_COLOR, alpha=0.18, zorder=3)
    ax.plot(angles, user_vals, color=ACTIVE_COLOR, linewidth=2.5, zorder=4)

    # Puntos en vértices
    ax.scatter(angles[:-1], user_vals[:-1],
               color=ACTIVE_COLOR, s=55, zorder=5, edgecolors=BG_COLOR, linewidths=1.5)

    # Labels de dominio
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([])
    ax.set_yticks([])
    ax.set_ylim(0, 1)
    ax.spines["polar"].set_visible(False)

    # Etiquetas manuales con offset
    label_pad = 1.22
    for i, (angle, label) in enumerate(zip(angles[:-1], labels)):
        x = math.cos(angle - math.pi / 2)
        y = math.sin(angle - math.pi / 2)
        ha = "center"
        if abs(x) > 0.5:
            ha = "left" if x > 0 else "right"

        score_pct = int(user_scores[domains[i]] * 100)
        color = ACTIVE_COLOR if score_pct > 60 else (
            "#ffaa00" if score_pct > 30 else INACTIVE_FILL
        )

        ax.text(
            angle, label_pad, f"{label}\n{score_pct}%",
            ha="center", va="center",
            fontsize=9.5, fontweight="bold",
            color=color,
            transform=ax.transData,
        )

    # Niveles de referencia (25%, 50%, 75%)
    for lvl, txt in [(0.25, "25%"), (0.5, "50%"), (0.75, "75%")]:
        ax.text(0.02, lvl + 0.02, txt, fontsize=6.5, color=LABEL_COLOR,
                ha="left", va="bottom", transform=ax.transData)

    # Cómputo cobertura global
    avg_score = sum(user_scores[d] for d in domains) / N
    coverage  = int(avg_score * 100)

    # Título
    phase_labels = {
        "loading":     "⬆ CARGA",
        "maintenance": "✓ MANTENIMIENTO",
        "washout":     "↺ WASHOUT",
    }
    is_rest = _is_rest_day()
    rest_str = "  •  🏖 Drug Holiday" if is_rest else ""
    subtitle = f"{phase_labels.get(phase, phase)}{rest_str}"

    fig.text(0.5, 0.97, "PERFIL COGNITIVO", ha="center", fontsize=13,
             fontweight="bold", color=TEXT_COLOR, transform=fig.transFigure)
    fig.text(0.5, 0.935, subtitle, ha="center", fontsize=9,
             color=LABEL_COLOR, transform=fig.transFigure)
    fig.text(0.5, 0.905, f"Cobertura global: {coverage}%", ha="center",
             fontsize=11, fontweight="bold",
             color=ACTIVE_COLOR if coverage > 60 else "#ffaa00",
             transform=fig.transFigure)

    # Leyenda
    patch_user = mpatches.Patch(color=ACTIVE_COLOR, alpha=0.7, label="Tu stack activo")
    patch_full = mpatches.Patch(color=FULL_COLOR,   alpha=0.6, label="Stack completo (referencia)")
    leg = ax.legend(
        handles=[patch_user, patch_full],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.13),
        ncol=2,
        frameon=False,
        fontsize=8.5,
    )
    for text in leg.get_texts():
        text.set_color(TEXT_COLOR)

    plt.tight_layout(rect=[0, 0.02, 1, 0.90])

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=BG_COLOR, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_missing_report(available_ids: list) -> str:
    """Genera texto de qué sustancias faltan y cómo impactan."""
    from substances import SUBSTANCES, DOMAIN_LABELS
    missing = [s for s in SUBSTANCES if s["id"] not in available_ids]
    if not missing:
        return "✅ Tienes *todas* las sustancias del stack."

    domains = list(DOMAIN_LABELS.keys())
    lines   = ["❌ *Sustancias que no tienes:*\n"]
    for s in missing:
        top_domains = sorted(s["domains"].items(), key=lambda x: -x[1])[:2]
        top_str = " + ".join(DOMAIN_LABELS[d] for d, v in top_domains if v > 0.3)
        lines.append(f"  • *{s['name']}* `{s['dose']}` — afecta: _{top_str}_")

    lines.append("")
    lines.append("_Usa /stack para activar o desactivar sustancias._")
    return "\n".join(lines)
