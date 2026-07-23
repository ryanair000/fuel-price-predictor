from __future__ import annotations


def _positive(value: float, label: str) -> float:
    number = float(value)
    if number <= 0:
        raise ValueError(f"{label} must be greater than zero")
    return number


def cost_for_litres(litres: float, price_per_litre: float) -> float:
    return _positive(litres, "Litres") * _positive(price_per_litre, "Price")


def litres_for_budget(budget: float, price_per_litre: float) -> float:
    return _positive(budget, "Budget") / _positive(price_per_litre, "Price")


def trip_estimate(distance_km: float, efficiency_km_per_litre: float, price_per_litre: float, contingency_pct: float = 0) -> dict[str, float]:
    distance = _positive(distance_km, "Distance")
    efficiency = _positive(efficiency_km_per_litre, "Efficiency")
    price = _positive(price_per_litre, "Price")
    contingency = float(contingency_pct)
    if not 0 <= contingency <= 100:
        raise ValueError("Contingency must be between 0 and 100")
    base_litres = distance / efficiency
    litres = base_litres * (1 + contingency / 100)
    return {"base_litres": base_litres, "litres": litres, "cost": litres * price}
