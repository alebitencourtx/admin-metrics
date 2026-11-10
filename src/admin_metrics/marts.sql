CREATE TABLE report_summary AS
SELECT reporter_id, any_value(reporter) AS reporter, count(*) AS endpoints,
       sum(calls) AS calls, sum(errors) AS errors, sum(rejections) AS rejections,
       100.0 * sum(errors) FILTER(WHERE errors<=calls AND calls>0) /
         nullif(sum(calls) FILTER(WHERE errors<=calls AND calls>0),0) AS error_pct,
       100.0 * sum(rejections) FILTER(WHERE rejections<=calls AND calls>0) /
         nullif(sum(calls) FILTER(WHERE rejections<=calls AND calls>0),0) AS rejection_pct,
       sum(mean_ms::DOUBLE*calls) FILTER(WHERE mean_ms>0 AND calls>0) /
         nullif(sum(calls) FILTER(WHERE mean_ms>0 AND calls>0),0) AS mean_ms
FROM current_rows WHERE fresh AND source_complete GROUP BY reporter_id;

CREATE TABLE family_summary AS
SELECT family,count(*) AS endpoints,sum(calls) AS calls,sum(errors) AS errors,
       100.0*sum(errors) FILTER(WHERE errors<=calls AND calls>0)/
         nullif(sum(calls) FILTER(WHERE errors<=calls AND calls>0),0) AS error_pct
FROM current_rows WHERE fresh AND source_complete GROUP BY family;

CREATE TABLE observation_trends AS
SELECT run_id, observed_at, reporter_id, sum(calls) AS calls, sum(errors) AS errors,
       100.0*sum(errors) FILTER(WHERE errors<=calls AND calls>0)/
         nullif(sum(calls) FILTER(WHERE errors<=calls AND calls>0),0) AS error_pct,
       sum(mean_ms::DOUBLE*calls) FILTER(WHERE mean_ms>0 AND calls>0)/
         nullif(sum(calls) FILTER(WHERE mean_ms>0 AND calls>0),0) AS mean_ms
FROM observations WHERE source_complete GROUP BY ALL ORDER BY observed_at,reporter_id;
