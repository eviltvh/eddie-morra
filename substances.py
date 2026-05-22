"""
substances.py — Definición completa del stack de Eddie Morra
Cada sustancia tiene: slot, dosis, dominios cognitivos y si es ciclable.

Dominios cognitivos (escala 0-10):
  memoria      — consolidación, retención, recall
  foco         — concentración, atención sostenida
  neuroprot    — neuroprotección, NGF, BDNF
  energia      — energía mental, reducción de fatiga
  animo        — estado de ánimo, motivación
  sueno        — calidad de sueño, recuperación
"""

# Cada sustancia: id único, nombre, dosis, slot, nota, si es ciclable,
#   y scores por dominio cognitivo (0.0–1.0)
SUBSTANCES = [
    # ── Mañana ──────────────────────────────────────────────────────────────
    {
        "id":       "lions_mane",
        "name":     "Lion's Mane",
        "dose":     "500mg",
        "slot":     "morning",
        "note":     "Estimula NGF → neuroplasticidad",
        "cyclable": False,
        "domains":  {
            "memoria":   0.8,
            "foco":      0.5,
            "neuroprot": 1.0,
            "energia":   0.2,
            "animo":     0.4,
            "sueno":     0.2,
        }
    },
    {
        "id":       "bacopa",
        "name":     "Bacopa Monnieri",
        "dose":     "300mg",
        "slot":     "morning",
        "note":     "Memoria y aprendizaje (acumulativo)",
        "cyclable": True,
        "domains":  {
            "memoria":   1.0,
            "foco":      0.5,
            "neuroprot": 0.6,
            "energia":   0.1,
            "animo":     0.5,
            "sueno":     0.3,
        }
    },
    {
        "id":       "omega3",
        "name":     "Omega-3 DHA/EPA",
        "dose":     "2g",
        "slot":     "morning",
        "note":     "Base estructural de membranas neuronales",
        "cyclable": False,
        "domains":  {
            "memoria":   0.6,
            "foco":      0.4,
            "neuroprot": 0.9,
            "energia":   0.2,
            "animo":     0.5,
            "sueno":     0.3,
        }
    },
    {
        "id":       "magnesio",
        "name":     "Magnesio L-Treonato",
        "dose":     "144mg",
        "slot":     "morning",
        "note":     "Cruza barrera hematoencefálica",
        "cyclable": False,
        "domains":  {
            "memoria":   0.7,
            "foco":      0.4,
            "neuroprot": 0.5,
            "energia":   0.3,
            "animo":     0.4,
            "sueno":     0.8,
        }
    },
    {
        "id":       "d3k2",
        "name":     "Vitamina D3 + K2",
        "dose":     "2000UI + 100mcg",
        "slot":     "morning",
        "note":     "Cofactor cognitivo — casi todos deficientes",
        "cyclable": False,
        "domains":  {
            "memoria":   0.4,
            "foco":      0.3,
            "neuroprot": 0.7,
            "energia":   0.5,
            "animo":     0.6,
            "sueno":     0.3,
        }
    },
    {
        "id":       "ginkgo",
        "name":     "Ginkgo Biloba",
        "dose":     "120mg",
        "slot":     "morning",
        "note":     "Circulación cerebral y oxigenación",
        "cyclable": True,
        "domains":  {
            "memoria":   0.6,
            "foco":      0.5,
            "neuroprot": 0.5,
            "energia":   0.4,
            "animo":     0.3,
            "sueno":     0.1,
        }
    },

    # ── Boost (media mañana) ─────────────────────────────────────────────────
    {
        "id":       "lteanina",
        "name":     "L-Teanina",
        "dose":     "200mg",
        "slot":     "boost",
        "note":     "Suaviza la cafeína, calma el jitter",
        "cyclable": False,
        "domains":  {
            "memoria":   0.3,
            "foco":      0.7,
            "neuroprot": 0.2,
            "energia":   0.3,
            "animo":     0.6,
            "sueno":     0.4,
        }
    },
    {
        "id":       "cafeina",
        "name":     "Cafeína",
        "dose":     "100mg",
        "slot":     "boost",
        "note":     "Foco limpio 4-6h (con L-Teanina)",
        "cyclable": False,
        "domains":  {
            "memoria":   0.3,
            "foco":      0.9,
            "neuroprot": 0.1,
            "energia":   1.0,
            "animo":     0.5,
            "sueno":     0.0,
        }
    },
    {
        "id":       "rhodiola",
        "name":     "Rhodiola Rosea",
        "dose":     "300mg",
        "slot":     "boost",
        "note":     "Anti-fatiga mental, adaptógeno",
        "cyclable": True,
        "domains":  {
            "memoria":   0.4,
            "foco":      0.7,
            "neuroprot": 0.3,
            "energia":   0.8,
            "animo":     0.7,
            "sueno":     0.2,
        }
    },

    # ── Noche ────────────────────────────────────────────────────────────────
    {
        "id":       "ashwagandha",
        "name":     "Ashwagandha KSM-66",
        "dose":     "600mg",
        "slot":     "night",
        "note":     "Regula cortisol, mejora sueño profundo",
        "cyclable": False,
        "domains":  {
            "memoria":   0.3,
            "foco":      0.2,
            "neuroprot": 0.4,
            "energia":   0.3,
            "animo":     0.8,
            "sueno":     0.9,
        }
    },
    {
        "id":       "glicina",
        "name":     "Glicina",
        "dose":     "3g",
        "slot":     "night",
        "note":     "Mejora sueño REM y consolidación",
        "cyclable": False,
        "domains":  {
            "memoria":   0.5,
            "foco":      0.1,
            "neuroprot": 0.3,
            "energia":   0.1,
            "animo":     0.3,
            "sueno":     1.0,
        }
    },
    {
        "id":       "magnesio_night",
        "name":     "Magnesio L-Treonato (noche)",
        "dose":     "144mg",
        "slot":     "night",
        "note":     "Dosis nocturna para sueño profundo",
        "cyclable": False,
        "domains":  {
            "memoria":   0.5,
            "foco":      0.2,
            "neuroprot": 0.4,
            "energia":   0.2,
            "animo":     0.3,
            "sueno":     0.9,
        }
    },
]

# Mapeo rápido por id
SUBSTANCE_MAP = {s["id"]: s for s in SUBSTANCES}

DOMAIN_LABELS = {
    "memoria":   "Memoria",
    "foco":      "Foco",
    "neuroprot": "Neuroprot.",
    "energia":   "Energía",
    "animo":     "Ánimo",
    "sueno":     "Sueño",
}

SLOT_META = {
    "morning": {"emoji": "🌅", "label": "Mañana (con desayuno)"},
    "boost":   {"emoji": "⚡", "label": "Boost cognitivo"},
    "night":   {"emoji": "🌙", "label": "Recuperación nocturna"},
}

# Sustancias que se suspenden en washout
WASHOUT_SUSPEND = {"bacopa", "rhodiola", "ginkgo", "cafeina", "lteanina"}
