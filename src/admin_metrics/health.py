"""Collection outcome is independent from successful processing/publication."""


def outcome(report):
    count = report.get('records', len(report.get('rows', [])))
    if report['status'] == 0:
        return 'transport_error'
    if report['status'] != 200:
        return 'http_error'
    if not count and ('empty_report' in report['issues'] or report.get('complete')):
        return 'empty'
    return 'valid' if report['complete'] and count > 0 else 'invalid_report'


def collection_health(reports):
    valid = sum(outcome(r) == 'valid' for r in reports)
    return {'status': 'healthy' if valid == len(reports) and reports else 'partial' if valid else 'unavailable',
            'valid_sources': valid, 'total_sources': len(reports)}
