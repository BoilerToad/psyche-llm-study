# Sample SQL Queries — Experiment Results

All queries run against SQLite databases in `experiments/<id>/results/` and `experiments/<id>/analysis/`.

```bash
sqlite3 experiments/<id>/results/run_TIMESTAMP.db
sqlite3 experiments/<id>/analysis/judge_TIMESTAMP.db
```

---

## Model Responses (`run_*.db`)

### Overview

```sql
-- All models tested and response counts
SELECT model_name, COUNT(*) as total,
       SUM(success) as successful,
       COUNT(*) - SUM(success) as failed
FROM queries
GROUP BY model_name
ORDER BY model_name;
```

```sql
-- Total queries and success rate
SELECT COUNT(*) as total,
       SUM(success) as successful,
       ROUND(100.0 * SUM(success) / COUNT(*), 1) as pct_success
FROM queries;
```

### By Question

```sql
-- All responses for a specific question
SELECT model_name, content, elapsed_seconds
FROM queries
WHERE tags_json LIKE '%Q01%' AND success = 1
ORDER BY model_name;
```

```sql
-- Which models answered every question
SELECT model_name, COUNT(DISTINCT json_extract(value, '$')) as questions_answered
FROM queries, json_each(tags_json)
WHERE value LIKE 'Q%' AND success = 1
GROUP BY model_name
ORDER BY questions_answered DESC;
```

```sql
-- Response count per question
SELECT json_extract(tags_json, '$[0]') as question_id,
       COUNT(*) as model_count,
       SUM(success) as successful
FROM queries
GROUP BY question_id
ORDER BY question_id;
```

### Think Blocks

```sql
-- Models that produced think blocks
SELECT DISTINCT model_name
FROM queries
WHERE think_block != '' AND success = 1;
```

```sql
-- Think block usage rate per model
SELECT model_name,
       COUNT(*) as total,
       SUM(CASE WHEN think_block != '' THEN 1 ELSE 0 END) as with_think,
       ROUND(100.0 * SUM(CASE WHEN think_block != '' THEN 1 ELSE 0 END) / COUNT(*), 1) as pct
FROM queries
WHERE success = 1
GROUP BY model_name
ORDER BY pct DESC;
```

```sql
-- Average think block length per model
SELECT model_name,
       ROUND(AVG(LENGTH(think_block))) as avg_think_chars,
       ROUND(AVG(LENGTH(content))) as avg_response_chars
FROM queries
WHERE success = 1 AND think_block != ''
GROUP BY model_name
ORDER BY avg_think_chars DESC;
```

### Response Length

```sql
-- Average response length per model
SELECT model_name,
       ROUND(AVG(LENGTH(content))) as avg_chars,
       MIN(LENGTH(content)) as min_chars,
       MAX(LENGTH(content)) as max_chars
FROM queries
WHERE success = 1
GROUP BY model_name
ORDER BY avg_chars DESC;
```

```sql
-- Shortest and longest responses for a question
SELECT model_name, LENGTH(content) as chars, content
FROM queries
WHERE tags_json LIKE '%Q01%' AND success = 1
ORDER BY chars DESC;
```

### Timing

```sql
-- Average response time per model
SELECT model_name,
       ROUND(AVG(elapsed_seconds), 2) as avg_s,
       ROUND(MIN(elapsed_seconds), 2) as min_s,
       ROUND(MAX(elapsed_seconds), 2) as max_s
FROM queries
WHERE success = 1
GROUP BY model_name
ORDER BY avg_s;
```

```sql
-- Slowest individual responses
SELECT model_name, tags_json, ROUND(elapsed_seconds, 2) as seconds
FROM queries
WHERE success = 1
ORDER BY elapsed_seconds DESC
LIMIT 10;
```

### Failures

```sql
-- All failed queries
SELECT model_name, tags_json, error
FROM queries
WHERE success = 0;
```

---

## Judge Analyses (`judge_*.db`)

### Overview

```sql
-- All judge runs
SELECT id, experiment_id, judge_model, created_at
FROM judge_runs
ORDER BY created_at DESC;
```

```sql
-- All analyses in latest run
SELECT question_id, category, models_included, elapsed_seconds, success
FROM judge_analyses
ORDER BY question_id;
```

### By Question

```sql
-- Full judge response for a specific question
SELECT judge_response
FROM judge_analyses
WHERE question_id = 'Q01';
```

```sql
-- Models skipped per question (failed/empty responses)
SELECT question_id, models_skipped
FROM judge_analyses
ORDER BY question_id;
```

### Cross-Run Comparisons

```sql
-- Compare judge assessments across runs (if multiple judge runs exist)
SELECT r.created_at, r.judge_model, a.question_id,
       a.models_included, a.elapsed_seconds, a.success
FROM judge_runs r
JOIN judge_analyses a ON a.run_id = r.id
ORDER BY a.question_id, r.created_at;
```

```sql
-- Judge timing per question
SELECT question_id,
       ROUND(elapsed_seconds, 2) as judge_seconds
FROM judge_analyses
ORDER BY judge_seconds DESC;
```
