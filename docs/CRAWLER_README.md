# Crawler Configuration Generator Documentation

## Overview

`make_crawl_config2.py` generates a crawler configuration YAML file from a CSV of URLs. The script is designed to prepare a crawl definition for Elasticsearch-backed web crawling, where:

- input is a CSV file containing a `url` column
- output is a `crawl-config.yml` file
- URLs are grouped by domain
- exact page URLs are converted into crawl allow/deny regex rules
- generated configuration includes Elasticsearch connection settings and crawl threading options

This is useful when you already have a curated list of target URLs and want to produce a crawler config automatically instead of writing YAML by hand.

---

## What the Script Does

The script performs the following steps:

1. Reads a CSV file using pandas
2. Validates that the CSV contains a `url` column
3. Cleans and deduplicates URLs
4. Validates URLs using `urllib.parse.urlsplit`
5. Groups URLs by bare domain such as:
   - `https://example.com`
   - `https://news.example.org`
6. Builds crawl rules for each domain:
   - either one combined regex covering all URLs for that domain
   - or one allow rule per URL
7. Appends a final deny-all rule
8. Writes the full crawler configuration as YAML

---

## Input Requirements

The CSV file must contain a column named `url`.

Example:

```csv
url
https://example.com/article-1
https://example.com/article-2
https://another-site.com/blog/post-a
```

Rules:
- blank URLs are ignored
- duplicate URLs are removed
- invalid URLs are skipped
- at least one valid URL must remain

If the `url` column is missing, the script exits with an error.

---

## Command Line Arguments

### Required Arguments

| Argument | Description |
|---------|-------------|
| `--csv` | Path to the input CSV containing a `url` column |
| `--out` | Output YAML file path |
| `--index` | Elasticsearch index name |
| `--host` | Elasticsearch host URL |
| `--api-key` | Base64 encoded Elasticsearch API key |

### Optional Arguments

| Argument | Default | Description |
|---------|---------|-------------|
| `--port` | `9200` | Elasticsearch port |
| `--threads` | `1` | Value for `threads_per_crawl` |
| `--allow-any-query` | disabled | Allows any query string on matched URLs |
| `--one-rule-per-url` | disabled | Creates one allow rule per URL instead of one combined regex per domain |

---

## Basic Usage

```bash
cd Notebook

python make_crawl_config2.py \
  --csv ../data/sample_urls.csv \
  --out crawl-config.yml \
  --index web-crawl-df \
  --host https://YOUR-ENDPOINT \
  --api-key YOUR_ENCODED_API_KEY \
  --threads 1
```

This generates a YAML file with:
- Elasticsearch output settings
- one domain entry per unique domain
- exact seed URLs
- regex allow rules
- a deny-all fallback rule

---

## Usage Modes

### 1. Combined Regex Mode

This is the default mode.

For each domain, the script creates:
- one allow rule containing a combined regex for all URLs in that domain
- one deny rule matching everything else

Example command:

```bash
python make_crawl_config2.py \
  --csv urls.csv \
  --out crawl-config.yml \
  --index web-crawl-df \
  --host https://YOUR-ENDPOINT \
  --api-key YOUR_ENCODED_API_KEY
```

Generated rule style:

```yaml
crawl_rules:
  - policy: allow
    rule: regex
    pattern: ^(?:https://example\.com/page1/?|https://example\.com/page2/?)$
  - policy: deny
    rule: regex
    pattern: .*
```

This keeps the YAML smaller when many URLs belong to the same domain.

---

### 2. One Rule Per URL Mode

Use `--one-rule-per-url` when you want one explicit allow rule for each seed URL.

```bash
python make_crawl_config2.py \
  --csv urls.csv \
  --out crawl-config.yml \
  --index web-crawl-df \
  --host https://YOUR-ENDPOINT \
  --api-key YOUR_ENCODED_API_KEY \
  --one-rule-per-url
```

Generated rule style:

```yaml
crawl_rules:
  - policy: allow
    rule: regex
    pattern: ^https://example\.com/page1/?$
  - policy: allow
    rule: regex
    pattern: ^https://example\.com/page2/?$
  - policy: deny
    rule: regex
    pattern: .*
```

This mode is easier to inspect and debug.

---

## Query String Handling

By default, URL matching is strict and does not allow arbitrary query strings.

Example default pattern:

```regex
^https://example\.com/article/?$
```

If you enable `--allow-any-query`, the script accepts optional query parameters for each URL.

Example:

```bash
python make_crawl_config2.py \
  --csv urls.csv \
  --out crawl-config.yml \
  --index web-crawl-df \
  --host https://YOUR-ENDPOINT \
  --api-key YOUR_ENCODED_API_KEY \
  --allow-any-query
```

Pattern becomes:

```regex
^https://example\.com/article(?:\?.*)?/?$
```

Use this if the same page may appear with tracking or filter parameters.

---

## Generated YAML Structure

The YAML output contains these top-level sections:

```yaml
output_sink: elasticsearch
output_index: web-crawl-df
threads_per_crawl: 1
elasticsearch:
  host: https://YOUR-ENDPOINT
  port: 9200
  api_key: YOUR_ENCODED_API_KEY
  pipeline_enabled: false
domains:
  - url: https://example.com
    seed_urls:
      - https://example.com/page1
      - https://example.com/page2
    crawl_rules:
      - policy: allow
        rule: regex
        pattern: ^(?:https://example\.com/page1/?|https://example\.com/page2/?)$
      - policy: deny
        rule: regex
        pattern: .*
```

### Field Explanation

| Field | Description |
|------|-------------|
| `output_sink` | Fixed to `elasticsearch` |
| `output_index` | Target Elasticsearch index |
| `threads_per_crawl` | Crawl concurrency setting |
| `elasticsearch.host` | Elasticsearch endpoint |
| `elasticsearch.port` | Elasticsearch port |
| `elasticsearch.api_key` | Encoded API key |
| `elasticsearch.pipeline_enabled` | Fixed to `False` in this script |
| `domains` | List of grouped domain crawl definitions |
| `domains[].url` | Bare domain only |
| `domains[].seed_urls` | Exact URLs from input CSV |
| `domains[].crawl_rules` | Allow/deny regex rules |

---

## Grouping Logic

The script groups URLs by:

```text
scheme://netloc
```

Examples:

- `https://example.com/page1` → `https://example.com`
- `https://example.com/blog/post` → `https://example.com`
- `https://sub.example.com/a` → `https://sub.example.com`

This means:
- different subdomains become separate domain entries
- `http` and `https` are treated as different domains
- only URLs under the same exact scheme + host are grouped together

---

## Validation and Error Behavior

The script exits with an error in these cases:

### Missing `url` Column
If the CSV does not include `url`:

```text
CSV must have a 'url' column
```

### No URLs Found
If all values are empty or missing:

```text
No URLs found
```

### Invalid URLs
Malformed URLs are skipped with a stderr message:

```text
Skipping invalid URL: not-a-valid-url
```

---

## Console Output

After successful generation, the script prints a summary like:

```text
Wrote crawl-config.yml with 25 seed URLs across 3 domain(s).
- threads_per_crawl: 1
- allow_any_query: False
- one_rule_per_url: False
```

This helps verify:
- how many seed URLs were included
- how many domain groups were created
- which mode was used

---

## Example End-to-End Workflow

### Step 1: Prepare CSV

```csv
url
https://example.com/page1
https://example.com/page2
https://another.org/post1
```

### Step 2: Run the Script

```bash
python make_crawl_config2.py \
  --csv urls.csv \
  --out crawl-config.yml \
  --index web-crawl-df \
  --host https://cluster.example.com \
  --api-key BASE64_API_KEY \
  --threads 2 \
  --one-rule-per-url
```

### Step 3: Review Output

Inspect `crawl-config.yml` and confirm:
- domains are grouped correctly
- all expected seed URLs are present
- regex patterns match your intended crawl targets

---

## When to Use Which Mode

### Use combined regex mode when:
- you want smaller YAML output
- domains contain many URLs
- you prefer compact configuration

### Use one-rule-per-url mode when:
- you want more readable crawl rules
- debugging individual URL matching
- you need explicit allow entries per seed URL

### Use `--allow-any-query` when:
- URLs may include tracking parameters
- the crawler may encounter the same page with query strings
- strict exact path-only matching is too restrictive

---

## Dependencies

The script imports:

- `argparse`
- `re`
- `urllib.parse`
- `sys`
- `pandas`
- `yaml`

Install missing packages if needed:

```bash
pip install pandas pyyaml
```

---

## Example Input and Output

### Input CSV

```csv
url
https://docs.example.com/start
https://docs.example.com/install
https://blog.example.com/post-1
```

### Resulting Domain Groups

- `https://docs.example.com`
- `https://blog.example.com`

### Output Behavior

The script creates two entries under `domains`, each with:
- its own bare domain
- its own seed URLs
- allow rules matching only those URLs
- a deny-all rule afterward

---

## Limitations

- Requires a CSV with a `url` column
- Only generates config; it does not perform crawling
- Invalid URLs are skipped rather than corrected
- Query handling is either strict or fully permissive for any query string
- `pipeline_enabled` is hard-coded to `False`
- Assumes Elasticsearch as the output sink

---

## Recommended Improvements

If you plan to extend the script, possible enhancements include:

- support for additional output sinks
- configurable `pipeline_enabled`
- optional include/exclude path patterns
- validation report for skipped URLs
- support for input formats other than CSV
- optional logging instead of plain print statements

---

## File Location

Script path:

```text
Notebook/make_crawl_config2.py
```

Suggested documentation path:

```text
Notebook/CRAWLER_README.md
```

---

## Summary

`make_crawl_config2.py` is a utility for turning a curated CSV of URLs into a structured crawler YAML configuration for Elasticsearch-based crawling. It standardizes domain grouping, creates regex-based crawl rules, and saves time when preparing targeted crawl jobs from known URLs.