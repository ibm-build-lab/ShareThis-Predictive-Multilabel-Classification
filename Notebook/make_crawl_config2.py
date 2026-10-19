# make_crawl_config.py
# Usage (combined regex, default):
#   python make_crawl_config.py --csv urls.csv --out crawl-config.yml \
#     --index web-crawl-df --host https://YOUR-ENDPOINT --api-key YOUR_ENCODED_API_KEY \
#     --threads 1 [--allow-any-query]
#
# Usage (one rule per URL):
#   python make_crawl_config.py --csv urls.csv --out crawl-config.yml \
#     --index web-crawl-df --host https://YOUR-ENDPOINT --api-key YOUR_ENCODED_API_KEY \
#     --threads 1 --one-rule-per-url [--allow-any-query]
import argparse, re, urllib.parse, sys
import pandas as pd
import yaml
def pattern_for_url(u: str, allow_any_query: bool) -> str:
    """Anchored regex for a single URL."""
    base = u.rstrip('/')
    if allow_any_query:
        return r'^' + re.escape(base) + r'(?:\?.*)?/?$'
    return r'^' + re.escape(base) + r'/?$'
def build_combined_regex(urls, allow_any_query: bool) -> str:
    parts = []
    for u in urls:
        parts.append(pattern_for_url(u, allow_any_query)[1:-1])  # strip ^$
    return r'^(?:' + '|'.join(parts) + r')$'
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True, help="CSV with a 'url' column")
    ap.add_argument('--out', required=True, help='Output crawl-config.yml')
    ap.add_argument('--index', required=True, help='Elasticsearch index name')
    ap.add_argument('--host', required=True, help='Elasticsearch host (https://...)')
    ap.add_argument('--api-key', required=True, help='Encoded ApiKey (base64 id:api_key)')
    ap.add_argument('--port', type=int, default=9200)
    ap.add_argument('--threads', type=int, default=1, help='threads_per_crawl (default: 1)')
    ap.add_argument('--allow-any-query', action='store_true',
                    help='Allow any ?querystring on each URL')
    ap.add_argument('--one-rule-per-url', action='store_true',
                    help='Emit one allow rule per URL (vs one combined regex)')
    args = ap.parse_args()
    # Load and normalize URLs
    df = pd.read_csv(args.csv)
    if 'url' not in df.columns:
        print("CSV must have a 'url' column", file=sys.stderr); sys.exit(2)
    urls = sorted({str(u).strip() for u in df['url'].dropna() if str(u).strip()})
    if not urls:
        print("No URLs found", file=sys.stderr); sys.exit(2)
    # Group by bare domain
    by_domain = {}
    for u in urls:
        p = urllib.parse.urlsplit(u)
        if not p.scheme or not p.netloc:
            print(f"Skipping invalid URL: {u}", file=sys.stderr); continue
        domain = f"{p.scheme}://{p.netloc}"
        by_domain.setdefault(domain, []).append(u)
    domains_cfg = []
    for domain, seeds in by_domain.items():
        seeds_sorted = sorted(seeds)
        if args.one_rule_per_url:
            rules = [{"policy": "allow", "rule": "regex",
                      "pattern": pattern_for_url(s, args.allow_any_query)}
                     for s in seeds_sorted]
            rules.append({"policy": "deny", "rule": "regex", "pattern": r".*"})
        else:
            allow_regex = build_combined_regex(seeds_sorted, args.allow_any_query)
            rules = [
                {"policy": "allow", "rule": "regex", "pattern": allow_regex},
                {"policy": "deny",  "rule": "regex", "pattern": r".*"},
            ]
        domains_cfg.append({
            "url": domain,              # bare domain only (no path)
            "seed_urls": seeds_sorted,  # exact pages
            "crawl_rules": rules
        })
    config = {
        "output_sink": "elasticsearch",
        "output_index": args.index,
        "threads_per_crawl": args.threads,
        "elasticsearch": {
            "host": args.host,
            "port": args.port,
            "api_key": args.api_key,
            "pipeline_enabled": False
        },
        "domains": domains_cfg
    }
    with open(args.out, 'w') as f:
        yaml.safe_dump(config, f, sort_keys=False)
    print(f"Wrote {args.out} with {sum(len(v) for v in by_domain.values())} seed URLs across {len(domains_cfg)} domain(s).")
    print(f"- threads_per_crawl: {args.threads}")
    print(f"- allow_any_query: {args.allow_any_query}")
    print(f"- one_rule_per_url: {args.one_rule_per_url}")
if __name__ == '__main__':
    main()