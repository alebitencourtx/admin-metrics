"""Validated analytical and presentation settings shared by every layer."""
import math

DEFAULT_RULES = {
    'retention_days': 30, 'dashboard_history_days': 3,
    'schedule_interval_hours': 1, 'schedule_minute': 17,
    'error_attention_pct': 5, 'error_critical_pct': 20,
    'minimum_calls': 100, 'critical_minimum_calls': 1000,
    'rejection_attention_pct': 5, 'latency_attention_ms': 2000,
    'latency_critical_ms': 4000, 'regression_multiplier': 2,
    'recovery_samples': 2, 'confirmation_samples': 2,
    'baseline_minimum_days': 3, 'recurrent_minimum_days': 3,
    'reported_history_days': 7, 'clock_skew_seconds': 900,
    'stale_after_hours': 2, 'chart_gap_hours': 1.5,
}


def validate_rules(rules):
    if not isinstance(rules, dict) or set(rules) != set(DEFAULT_RULES):
        raise ValueError('Regras: parâmetros ausentes ou desconhecidos')
    fractions = {'error_attention_pct', 'error_critical_pct', 'rejection_attention_pct',
                 'regression_multiplier', 'stale_after_hours', 'chart_gap_hours'}
    for key, value in rules.items():
        if (type(value) not in (int, float) or not math.isfinite(value)
                or (key not in fractions and type(value) is not int)
                or value < 0 or (key != 'schedule_minute' and value == 0)):
            raise ValueError('Regra inválida: ' + key)
    for key in ('error_attention_pct', 'error_critical_pct', 'rejection_attention_pct'):
        if rules[key] > 100:
            raise ValueError('Percentual fora dos limites: ' + key)
    ordered = [('error_attention_pct', 'error_critical_pct'),
               ('minimum_calls', 'critical_minimum_calls'),
               ('latency_attention_ms', 'latency_critical_ms'),
               ('dashboard_history_days', 'retention_days'),
               ('baseline_minimum_days', 'reported_history_days'),
               ('recurrent_minimum_days', 'reported_history_days'),
               ('schedule_interval_hours', 'stale_after_hours'),
               ('schedule_interval_hours', 'chart_gap_hours')]
    if (any(rules[low] > rules[high] for low, high in ordered)
            or rules['reported_history_days'] > 7 or rules['schedule_minute'] > 59
            or rules['schedule_interval_hours'] not in (1, 2, 3, 4, 6, 8, 12, 24)
            or rules['regression_multiplier'] <= 1):
        raise ValueError('Regras: limites ou ordem de limiares incompatíveis')
    return rules


def schedule_cron(rules):
    hours = '*' if rules['schedule_interval_hours'] == 1 else '*/' + str(rules['schedule_interval_hours'])
    return f"{rules['schedule_minute']} {hours} * * *"
