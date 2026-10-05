# English presentation and reliability guide

## Five-minute walkthrough

1. Open [presentation mode](http://127.0.0.1:8000/?mode=demo). Explain the fixed date and frozen catalogue.
2. Load the software startup description and click **Prepare my form** if Ollama is running. Review the answers. If AI is unavailable, use **Load sample form**, which is clearly labelled as authored data.
3. Confirm the form and select **Find funding**. Explain why EIC Accelerator appears and why a topic match does not prove eligibility.
4. Open an official English source. Show the country rules and checks still required.
5. Load the recycling sample form. Its relevant LIFE calls are archived at the reference date. This demonstrates that the system does not promise unavailable funding.

The samples are fictional; programmes are real. Current-date mode uses today's date but is still a manually maintained catalogue, not a live search. EIC and Eureka Network country mappings are deliberately partial. Read each programme's country note before making claims about eligibility.

## Test layers

- Server tests cover validation, preserved answers, country-specific coverage, date boundaries, unchanged demo snapshots, review confirmation and mode propagation.
- The 20 scenarios below test authored form inputs against the frozen catalogue at **2026-10-04**.
- `python -m tools.evaluate_pilot --live --limit 3` separately checks actual Ollama extraction. Model output can vary; deterministic tests do not measure it.
- Non-empty expected groups below list required members, not necessarily the full group. Empty lists require the group to be empty. Scenario expectations are curated pilot checks, not independently certified funding advice.

## Scenarios

### Software startup (`software`)

We are a software startup registered in Ireland. Our company is an SME. We will commercialise innovative software technology. We request EUR 120,000 funding; total project cost is EUR 180,000.

EIC Accelerator is a topic match needing technology-stage and innovation checks. EIC Transition is archived and would also require an eligible prior EU-funded research project.
Expected form:
```json
{
  "country": "Ireland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "commercialization"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "eic-accelerator"
  ],
  "archive": [
    "eic-transition"
  ],
  "first_candidate": "eic-accelerator"
}
```

### Innovative manufacturing (`manufacturing`)

We are a manufacturing SME registered in Germany. We will develop a prototype for a new production process. We will install energy-saving equipment. We request EUR 500,000 funding; total project cost is EUR 800,000.

Eureka Network Projects and Pathfinder Challenges are research-topic leads, not confirmed eligibility. International partners and specific challenge fit need checking. Eurostars and the recorded LIFE calls are closed at this date.
Expected form:
```json
{
  "country": "Germany",
  "company_size": "SME",
  "industry": "manufacturing",
  "activities": [
    "research_and_development",
    "energy_efficiency"
  ],
  "requested_funding": "500000",
  "project_budget": "800000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "eic-pathfinder-challenges",
    "eureka-network"
  ],
  "archive": [
    "eic-pathfinder-open",
    "eic-transition",
    "eurostars",
    "life-climate",
    "life-clean-energy"
  ]
}
```

### Recycling and water reuse (`recycling`)

We are a recycling company registered in the Netherlands. Our company is an SME. We will recycle manufacturing waste. We will install water-saving equipment. We request EUR 400,000 funding; total project cost is EUR 700,000.

The recorded LIFE circular-economy and climate calls match the topics but are closed. This example should show archived matches, not promise an open grant.
Expected form:
```json
{
  "country": "Netherlands",
  "company_size": "SME",
  "industry": "waste_management",
  "activities": [
    "circular_economy",
    "water_efficiency"
  ],
  "requested_funding": "400000",
  "project_budget": "700000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "upcoming": [],
  "archive": [
    "life-circular",
    "life-climate"
  ]
}
```

### Overseas feasibility study (`market-study`)

We are a software SME registered in Ireland. We will conduct a market feasibility study in Canada. We request EUR 60,000 funding; total project cost is EUR 86,000.


Expected form:
```json
{
  "country": "Ireland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "export_promotion"
  ],
  "requested_funding": "60000",
  "project_budget": "86000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "innowwide"
  ],
  "first_candidate": "innowwide",
  "archive": []
}
```

### Above the Innowwide cap (`over-cap`)

We are a software SME registered in Ireland. We will conduct a market feasibility study in Canada. We request EUR 60,000.01 funding; total project cost is EUR 90,000.


Expected form:
```json
{
  "country": "Ireland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "export_promotion"
  ],
  "requested_funding": "60000.01",
  "project_budget": "90000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "excluded": [
    "innowwide"
  ]
}
```

### UK grant-only route (`uk-commercialisation`)

We are a software SME registered in the United Kingdom. We will commercialise innovative software technology. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "United Kingdom",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "commercialization"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "eic-accelerator"
  ],
  "archive": [
    "eic-transition"
  ]
}
```

### UK outside mapped LIFE coverage (`uk-recycling`)

We are a recycling company registered in the United Kingdom. Our company is an SME. We will recycle manufacturing waste. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "United Kingdom",
  "company_size": "SME",
  "industry": "waste_management",
  "activities": [
    "circular_economy"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": [],
  "excluded": [
    "life-circular"
  ]
}
```

### Canadian research partner (`canada-rd`)

We are a software SME registered in Canada. We will develop a prototype. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Canada",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "research_and_development"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": [
    "eurostars"
  ],
  "excluded": [
    "eic-pathfinder-open",
    "eic-pathfinder-challenges",
    "eureka-network"
  ]
}
```

### Unmapped applicant country (`us-rd`)

We are a software SME registered in the United States. We will develop a prototype. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "United States",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "research_and_development"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": []
}
```

### Large enterprise outside pilot (`large-business`)

We are a large software enterprise registered in Ireland. We will commercialise innovative software technology. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Ireland",
  "company_size": "large",
  "industry": "software",
  "activities": [
    "commercialization"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": []
}
```

### No invented innovation (`ordinary-machinery`)

We are a manufacturing SME registered in Germany. We will replace machinery. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Germany",
  "company_size": "SME",
  "industry": "manufacturing",
  "activities": [
    "machinery_replacement"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": []
}
```

### No silent currency conversion (`currency-unassessed`)

We are a software SME registered in Poland. We will conduct a market feasibility study in Canada. We request PLN 300,000 funding; total project cost is PLN 400,000.


Expected form:
```json
{
  "country": "Poland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "export_promotion"
  ],
  "requested_funding": "300000",
  "project_budget": "400000",
  "currency": "PLN"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "innowwide"
  ],
  "amount_unassessed": [
    "innowwide"
  ]
}
```

### Norway is not automatically a LIFE country (`norway-energy`)

We are a manufacturing SME registered in Norway. We will install energy-saving equipment. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Norway",
  "company_size": "SME",
  "industry": "manufacturing",
  "activities": [
    "energy_efficiency"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": [],
  "excluded": [
    "life-climate",
    "life-clean-energy"
  ]
}
```

### LIFE associated-country coverage (`iceland-recycling`)

We are a recycling company registered in Iceland. Our company is an SME. We will recycle manufacturing waste. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Iceland",
  "company_size": "SME",
  "industry": "waste_management",
  "activities": [
    "circular_economy"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [],
  "archive": [
    "life-circular"
  ]
}
```

### Large project cost does not replace request (`budget-not-request`)

We are a software SME registered in Ireland. We will conduct a market feasibility study in Canada. We request EUR 60,000 funding; total project cost is EUR 1,000,000.


Expected form:
```json
{
  "country": "Ireland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "export_promotion"
  ],
  "requested_funding": "60000",
  "project_budget": "1000000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "innowwide"
  ]
}
```

### EU country beyond original dropdown (`portugal-research`)

We are a software SME registered in Portugal. We will develop a prototype. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Portugal",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "research_and_development"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "eic-pathfinder-challenges",
    "eureka-network"
  ],
  "archive": [
    "eic-pathfinder-open",
    "eic-transition",
    "eurostars"
  ]
}
```

### Partial topic coverage (`mixed-topics`)

We are a manufacturing SME registered in Germany. We will commercialise innovative technology. We will replace machinery. We request EUR 120,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Germany",
  "company_size": "SME",
  "industry": "manufacturing",
  "activities": [
    "commercialization",
    "machinery_replacement"
  ],
  "requested_funding": "120000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected shortlist checks:
```json
{
  "candidates": [
    "eic-accelerator"
  ],
  "archive": [
    "eic-transition"
  ]
}
```

### Invalid financial totals (`request-over-budget`)

We are a software SME registered in Ireland. We will commercialise innovative software technology. We request EUR 200,000 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Ireland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "commercialization"
  ],
  "requested_funding": "200000",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected validation errors: `requested_funding`.

### Zero request rejected (`zero-request`)

We are a software SME registered in Ireland. We will commercialise innovative software technology. We request EUR 0 funding; total project cost is EUR 180,000.


Expected form:
```json
{
  "country": "Ireland",
  "company_size": "SME",
  "industry": "software",
  "activities": [
    "commercialization"
  ],
  "requested_funding": "0",
  "project_budget": "180000",
  "currency": "EUR"
}
```

Expected validation errors: `requested_funding`.

### Missing facts stay missing (`missing-details`)

I have a project idea and need help finding funding.


Expected form:
```json
{}
```

Expected validation errors: `country, company_size, industry, activities, requested_funding, project_budget, currency`.
