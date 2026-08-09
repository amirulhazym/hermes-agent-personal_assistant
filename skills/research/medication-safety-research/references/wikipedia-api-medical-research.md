# Wikipedia API for Medical Research

## Why Wikipedia API works when medical sites are blocked

Most medical sites (NCBI/PubMed, Mayo Clinic, MSD Manual, Drugs.com, Medscape) detect automated browser sessions and either CAPTCHA or block. The Wikipedia API via curl consistently works because it's a public API not behind bot protection.

## Basic pattern

### 1. Get the full extract of an article

```bash
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=&explaintext=&titles=ArticleTitle&format=json"
```

Parameters:
- `titles=ArticleTitle` — Wikipedia page title (URL-encoded if needed)
- `exintro=` — when present, returns only the introductory section (before first heading)
- `explaintext=true` — returns plain text, not HTML
- `prop=extracts` — requested content format

### 2. Extract and search within

```bash
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&titles=ArticleTitle&format=json" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
pages=d['query']['pages']
for k,v in pages.items():
    if 'extract' in v:
        text = v['extract']
        # Find specific section
        for term in ['Treatment', 'Management', 'Side effects', 'Adverse']:
            idx = text.find(term)
            if idx > 0:
                print(text[idx:idx+2000])
                break
"
```

### 3. Get full article without section truncation

```bash
curl -sL "https://en.wikipedia.org/w/api.php?action=query&titles=ArticleTitle&prop=extracts&explaintext=true&format=json"
```

(Omit `exintro=` to get the full article text, not just the intro.)

### 4. Chain lookups

When you need info on multiple related topics:

```bash
# First get primary condition
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=&explaintext=&titles=Cushing%27s_syndrome&format=json"

# Then get drug info
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=&explaintext=&titles=Dexamethasone&format=json"

# Then get drug class info
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=&explaintext=&titles=Glucocorticoid&format=json"
```

## Use cases

| Need | API query pattern |
|---|---|
| Medical condition overview | `titles=Cushing%27s_syndrome&exintro=&explaintext=true` |
| Drug side effects | `titles=Dexamethasone&prop=extracts&explaintext=true` |
| Drug class mechanism | `titles=Glucocorticoid&prop=extracts&exintro=&explaintext=true` |
| Find section within article | Pipe extract through python3 and search for section heading strings |
| Physiological explanation | Common sections: "Mechanism of action", "Pharmacodynamics", "Side effects" |

## Limitations

- Wikipedia is a general encyclopedia, not a specialized medical authority. Its quality is good for established conditions (Cushing's syndrome, glucocorticoid effects) but may lag on niche or very recent findings.
- Always check the "cited references" at the bottom of the Wikipedia article — if the article cites primary medical literature, the facts are likely reliable.
- For drug-specific interactions and dosing, still try primary sources (DailyMed, RxList) first; use Wikipedia as a fallback when primary sites are blocked.
- Wikipedia API extracts may truncate long articles — the `exintro` parameter returns only the lead section. Omit it for full article text but the response will be larger.
- Use `explaintext=true` for clean text, omit it for HTML (not recommended for medical content).
