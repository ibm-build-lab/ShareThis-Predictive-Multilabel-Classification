# ShareThis Predictive Multilabel Classification

Every URL tells a story. This project figures out what that story is.

Give it any web page and it comes back with the topics it covers, the key terms it uses, the people and brands it mentions, and the big ideas behind it — all in one shot, powered by IBM Watsonx AI.

It was built to solve a real problem: content on the web doesn't come with labels. This system reads the page, understands what it's about, and produces structured metadata you can actually use — for content targeting, audience segmentation, recommendation engines, or anything else that needs to know what a piece of content is really about.

---

## What does it do?

You send a URL. The app visits that page, reads the content, and tells you:

- **What it's about** — scored topic categories like `/home_&_garden/diy/hacks`
- **Key terms** — important single words, phrases, and the overall theme
- **Who and what is mentioned** — people, organizations, places, products, dates
- **Big ideas** — high-level concepts the page is discussing

Everything comes back in one response. No multiple calls needed.

---

## How it works

1. The scraper fetches the page. If the site blocks simple requests (like many news or social sites do), it automatically tries again using a real headless browser.
2. The page text is compared against a library of known categories using sentence embeddings to narrow down the candidates.
3. A single call to IBM Watsonx AI (`mistral-small-3-2-24b-instruct-2506`) does the final analysis and returns everything at once.

---

## Project layout

```
app/                        ← the API lives here
├── main.py                 ← FastAPI routes and request/response shapes
├── src/
│   ├── prompts.py          ← the prompt sent to the AI model
│   ├── watsonx_client.py   ← talks to Watsonx, retries on failure
│   ├── pipeline.py         ← ties everything together
│   ├── web_scraper.py      ← fetches and cleans page content
│   ├── embeddings.py       ← converts text to vectors
│   └── category_matcher.py ← finds the most relevant category candidates
└── data/
    └── with_label.csv      ← labelled training URLs used to build category examples

Notebook/
├── api_test_20_urls.ipynb  ← run 20 URLs through the API and see results
└── EDA.ipynb               ← data exploration
```

---

## Quickstart

You need Python 3.10+, and an IBM Watsonx AI API key + Project ID.

```bash
cd app
python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the example config and fill in your credentials:

```bash
cp env.example .env
```

The only two things you **must** set:

```
WATSONX_API_KEY=...
WATSONX_PROJECT_ID=...
```

Start the API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080/docs` in your browser to explore the API interactively.

---

## Try it

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://ikeahackers.net/2014/07/hackers-help-can-new-billy-doors-fit-old-billy-frame.html",
    "features": {
      "categories": { "limit": 3 },
      "keywords":   { "limit": 20 },
      "entities":   { "limit": 10 },
      "concepts":   { "limit": 10 }
    }
  }'
```

You'll get back something like:

```json
{
  "url": "https://ikeahackers.net/...",
  "status": "success",
  "categories": [
    { "label": "/home_&_garden/furniture/storage", "score": 0.9 },
    { "label": "/home_&_garden/diy/hacks",         "score": 0.8 }
  ],
  "keywords": {
    "theme": "IKEA Billy Bookcase Door Replacement",
    "keywords": ["Billy", "Oxberg", "hack", "shelves"],
    "phrases":  ["Billy bookcase", "glass doors"]
  },
  "entities": {
    "ORGANIZATION": ["IKEA"],
    "LOCATION":     ["UK"],
    "PRODUCT":      ["Billy", "Oxberg"],
    ...
  },
  "concepts": ["DIY modifications", "Product compatibility"],
  "metadata": {
    "title":      "Hackers Help: Can new Billy doors fit old Billy frame?",
    "domain":     "ikeahackers.net",
    "word_count": 5749
  }
}
```

Set `"return_analyzed_text": true` in your request if you also want the cleaned page text back.

---

## Available endpoints

| Endpoint | What it does |
|---|---|
| `POST /analyze` | The main one — scrape a URL and analyse it |
| `GET /categories` | See all the categories the model knows about |
| `GET /health` | Check if the API is up and ready |

---

## Notebook testing

There's a notebook that runs 20 URLs through the API automatically and saves the results:

```bash
jupyter notebook Notebook/api_test_20_urls.ipynb
```

Results are saved to `Notebook/results/` as both JSON and CSV.

---

## A note on web scraping

Some websites block automated access. When that happens, the scraper automatically tries again using a headless browser (Playwright) that behaves more like a real user. Most sites work fine without it, but if you're hitting a lot of blocked pages you can install it with:

```bash
playwright install chromium
```

---

## Configuration options

All settings go in `app/.env`. See `app/env.example` for the full list. Most have sensible defaults — you really only need the two Watsonx credentials to get started.

| Variable | Required | Default |
|---|---|---|
| `WATSONX_API_KEY` | ✅ | — |
| `WATSONX_PROJECT_ID` | ✅ | — |
| `WATSONX_URL` | no | `https://us-south.ml.cloud.ibm.com` |
| `WATSONX_MODEL_ID` | no | `mistralai/mistral-small-3-2-24b-instruct-2506` |
| `DATA_PATH` | no | `with_label.csv` |
| `LOG_LEVEL` | no | `INFO` |

---

## Run with Docker

```bash
cd app
docker build -t sharethis-classify .
docker run -p 8080:8080 \
  -e WATSONX_API_KEY=your_key \
  -e WATSONX_PROJECT_ID=your_project_id \
  sharethis-classify
```

---

## Notebooks

| Notebook | What's in it |
|---|---|
| `Notebook/api_test_20_urls.ipynb` | Test the running API against 20 real URLs, save results |
| `Notebook/EDA.ipynb` | Explore the training data |
| `Notebook/watsonx_url_keyword_entity_extraction_updated.ipynb` | Keyword and entity extraction experiments |

---

## Links

- [IBM Watsonx AI](https://cloud.ibm.com/docs/watsonx-ai)
- [IBM Code Engine](https://cloud.ibm.com/docs/codeengine)
- [IBM Cloud Credentials Setup](./docs/IBM_CREDENTIALS_SETUP.md)
