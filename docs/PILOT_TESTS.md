# English presentation and reliability guide

## Five-minute walkthrough

1. Open [presentation mode](http://127.0.0.1:8000/?mode=demo). Explain the fixed date and frozen catalogue.
2. Load **Forest fire early warning** and click **Prepare my form** if Ollama is running. Review the answers. If AI is unavailable, use **Load sample form**, which is clearly labelled as authored data.
3. Confirm the form and select **Find funding**. Explain why EIC Accelerator appears and why a topic match does not prove eligibility.
4. Select **Review my project and next steps**. The description is enough to start; extra answers are optional. Explain why 90-second detection does not prove low false alarms, and why municipal interest is weaker than a signed paid pilot. Add better evidence and update the review.
5. Load the recycling sample form. Its relevant LIFE calls are archived at the reference date. This demonstrates that the system does not promise unavailable funding.

The samples are fictional; programmes are real. Current-date mode uses today's date but is still a manually maintained catalogue, not a live search. EIC and Eureka Network country mappings are deliberately partial. Read each programme's country note before making claims about eligibility.

## Test layers

- Server tests cover validation, preserved answers, country-specific coverage, date boundaries, unchanged demo snapshots, review confirmation and mode propagation.
- The 21 authored scenarios test form inputs against the frozen catalogue at **2026-10-04**.
- `python -m tools.evaluate_pilot --live --limit 3` separately checks actual Ollama extraction. Model output can vary; deterministic tests do not measure it.
- Non-empty expected groups below list required members, not necessarily the full group. Empty lists require the group to be empty. Scenario expectations are curated pilot checks, not independently certified funding advice.

## Scenarios

### Forest fire early warning (`wildfire`)

A fictional Portuguese SME builds solar-powered forest cameras that use AI to detect smoke. Three controlled forest tests reached 90-second detection, but false alarms and comparison with alternatives are unmeasured. Two municipalities are interested; neither has signed. Requested support is EUR 120,000 of EUR 180,000 total, with EUR 60,000 company savings.

The shortlist should include EIC Accelerator as a lead. The AI review should identify the weak technical comparison and customer proof, ask for field reliability data, team roles and itemised costs, and provide a preparation plan. It must not call this project eligible or application-ready.

Stronger follow-up evidence is available in `tools/evaluate_readiness.py`. All sample projects and evidence are fictional.

### Wind turbine fault detector (`software`)

We are a small software company (SME) registered in Ireland. We built software that spots early faults in wind turbines from sensor readings, and tested a prototype at one wind farm. We will commercialise it by running field trials at more farms and getting it ready to sell across Europe. The total project cost is EUR 180,000 for two engineers, sensors and field trials, and independent security testing. We request EUR 120,000 funding and will pay the remaining EUR 60,000 ourselves.

The budget is fictional: for example, EUR 100,000 for two engineers, EUR 50,000 for sensors and field trials, and EUR 30,000 for independent testing. The company would cover EUR 60,000 of the EUR 180,000 total. EIC Accelerator is only a topic lead; its technology, market and budget rules still need checking. EIC Transition is archived and has extra prior-research rules.
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

### Less waste in a metal factory (`manufacturing`)

We are a small manufacturing company (SME) registered in Germany. We make metal parts for electric buses. We will develop a prototype that uses less metal to make each part. We will install energy-saving equipment on the test line. The total project cost is EUR 800,000. It covers prototype machinery, engineers and factory testing. We request EUR 500,000 funding. We will pay EUR 300,000 ourselves.

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

### Plastic recycling and water saving (`recycling`)

We are a small recycling company (SME) registered in the Netherlands. We will recycle plastic offcuts from factories into new packaging material. We will install water-saving equipment to wash the plastic. The total project cost is EUR 700,000. It covers sorting and washing machines, site changes and testing. We request EUR 400,000 funding. We will pay EUR 300,000 ourselves.

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

### Farm software in Canada (`market-study`)

We are a small software company (SME) registered in Ireland. We sell software that helps farms spot crop disease from satellite images. We will conduct a market feasibility study in Canada: interview farmers, check local rules and work with a Canadian partner to see whether farms would buy it. The total project cost is EUR 86,000 for local research, travel and the partner's work. We request EUR 60,000 funding and will pay EUR 26,000 ourselves.


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

We are a small software company (SME) registered in Ireland. We sell software that helps farms spot crop disease from satellite images. We will conduct a market feasibility study in Canada to interview farmers and check local rules. We request EUR 60,000.01 funding; total project cost is EUR 90,000.


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

We are a small software company (SME) registered in the United Kingdom. We built software that spots early faults in wind turbines from sensor readings. We will commercialise it by testing it with more farms and preparing to sell it across Europe. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small recycling company (SME) registered in the United Kingdom. We will recycle plastic offcuts from factories into new packaging material. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small software company (SME) registered in Canada. We will develop a prototype that spots forest fires from satellite images before they spread. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small software company (SME) registered in the United States. We will develop a prototype that spots forest fires from satellite images before they spread. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a large software company registered in Ireland. We built software that spots early faults in wind turbines. We will commercialise it by testing it with more farms and preparing to sell it across Europe. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small manufacturing company (SME) registered in Germany. We make bicycle parts and will replace machinery that is worn out. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small software company (SME) registered in Poland. We sell software that helps farms spot crop disease from satellite images. We will conduct a market feasibility study in Canada to interview farmers and check local rules. We request PLN 300,000 funding; total project cost is PLN 400,000.


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

We are a small manufacturing company (SME) registered in Norway. We make metal parts and will install energy-saving equipment on our production line. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small recycling company (SME) registered in Iceland. We will recycle plastic offcuts from factories into new packaging material. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small software company (SME) registered in Ireland. We sell software that helps farms spot crop disease from satellite images. We will conduct a market feasibility study in Canada before opening a larger overseas business. We request EUR 60,000 funding; total project cost is EUR 1,000,000.


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

We are a small software company (SME) registered in Portugal. We will develop a prototype that finds leaks in city water pipes from meter readings. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small manufacturing company (SME) registered in Germany. We built a camera system that detects defects in metal parts. We will commercialise this technology by testing it with other factories. We will also replace machinery on our own production line. We request EUR 120,000 funding; total project cost is EUR 180,000.


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

We are a small software company (SME) registered in Ireland. We built software that spots early faults in wind turbines. We will commercialise it by testing it with more farms. We request EUR 200,000 funding; total project cost is EUR 180,000.


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

We are a small software company (SME) registered in Ireland. We built software that spots early faults in wind turbines. We will commercialise it by testing it with more farms. We request EUR 0 funding; total project cost is EUR 180,000.


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
