"""Metsa terviseindeks 0-100."""


def health_index(boniteedi_kood: int, kuivendatud: bool, tuleohu_kood: str | None, yrask_risk: int) -> dict:
    """Terviseindeks 0-100. 100 = terve, 0 = halb."""
    boniteet_map = {0: 100, 1: 90, 2: 80, 3: 65, 4: 50, 5: 35, 6: 20}
    score = boniteet_map.get(boniteedi_kood, 50)

    # Drenaaži korrigeerimine
    if not kuivendatud:
        score -= 15

    # Tuleoht
    if tuleohu_kood == "3":
        score -= 10

    # Üraski risk
    yrask_penalty = {0: 0, 1: -5, 2: -10, 3: -20}
    score += yrask_penalty.get(yrask_risk, 0)

    score = max(0, min(100, score))

    if score >= 70:
        label = "Hea"
    elif score >= 40:
        label = "Keskmine"
    else:
        label = "Halb"

    return {"score": score, "label": label}
