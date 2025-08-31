# file: C:\Users\Novaes Engenharia\github - deploy\VRP\frontend\VRP_STYLES\brand.py
from pathlib import Path

# Paleta (padrão azul-claro)
COLORS = {
    "primary":        "#0EA5E9",  # sky-500
    "primary_600":    "#0284C7",  # sky-600
    "primary_100":    "#E0F2FE",  # sky-100
    "bg":             "#F8FBFF",
    "bg2":            "#EEF6FF",
    "text":           "#0F172A",
    "muted":          "#475569",
    "border":         "#DBEAFE",
    "success":        "#16A34A",
    "warning":        "#F59E0B",
    "danger":         "#DC2626",
}

def logo_path() -> str:
    # mesmo logo usado no relatório
    p = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "logos" / "NOVAES.png"
    return str(p)
