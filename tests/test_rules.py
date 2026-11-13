from pathlib import Path
import json
import re

import pytest

from admin_metrics.rules import DEFAULT_RULES, schedule_cron, validate_rules


@pytest.mark.parametrize('change', [
    {'retention_days': True}, {'minimum_calls': -1}, {'recovery_samples': 1.5},
    {'error_attention_pct': '5'}, {'latency_critical_ms': 100},
    {'error_critical_pct': 101}, {'error_attention_pct': 30},
    {'regression_multiplier': 1}, {'chart_gap_hours': float('nan')},
    {'dashboard_history_days': 31}, {'baseline_minimum_days': 8},
    {'schedule_interval_hours': 5}, {'schedule_minute': 60}, {'typo': 1},
])
def test_invalid_rules_fail_before_collection(change):
    with pytest.raises(ValueError):
        validate_rules({**DEFAULT_RULES, **change})


def test_versioned_configuration_matches_hourly_workflow():
    rules = validate_rules(json.loads(Path('config/rules.json').read_bytes()))
    assert rules == DEFAULT_RULES
    workflow = Path('.github/workflows/pages.yml').read_text(encoding='utf-8')
    assert re.search(r"cron: '([^']+)'", workflow).group(1) == schedule_cron(rules) == '17 * * * *'
    assert rules['dashboard_history_days'] == 3 and rules['retention_days'] == 30
