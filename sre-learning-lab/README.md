# E-Commerce SRE Learning Lab

A local Streamlit companion for learning SRE concepts with the OpenTelemetry
Astronomy Shop. It uses a curated, swappable YAML question bank and can safely
activate hidden feature-flag scenarios in a running demo.

All SLA and SLO values in the starter bank are hypothetical training examples.

## What is included

- A local Streamlit app with four progressive SRE learning levels.
- A versioned, swappable YAML question bank with 12 e-commerce scenarios.
- Guided prompts for observations, diagnosis, PromQL, and incident response.
- Direct links to the Astronomy Shop storefront, Locust, Grafana, and Jaeger.
- Safe feature-flag activation with a persistent recovery snapshot and conflict
  detection.
- Local progress, self-assessment scores, and saved responses under `.state/`.

## Learning flow

1. Select a level and scenario. The app defaults to an incomplete exercise but
   never locks later levels.
2. Read the fictional e-commerce brief, CUJ, SLA, SLOs, SLIs, and error-budget
   context. These are available as reference rather than hidden quiz answers.
3. Activate the hidden fault only when Astronomy Shop is running, then generate
   or observe traffic through Locust and the storefront.
4. Investigate with Grafana and Jaeger, recording your evidence, PromQL, and
   response plan in the app.
5. Reveal the injected flag profile and model answer, score yourself against
   the rubric, and save the review locally.
6. Restore the original feature flags before starting another live scenario.

## Starter curriculum

| Level | Focus | Included exercises |
| --- | --- | --- |
| Reliability foundations | SLA/SLO/SLI language, error budgets, service tiers, and segmented reliability | Checkout contract, ads versus revenue path, invisible broken SKU |
| Metrics, logs, traces, and PromQL | RED metrics, distributed traces, tail latency, and frontend measurement boundaries | Failed checkout trace, international shipping tail, healthy APIs/unhappy shoppers |
| Alerting and incident response | Customer-impact triage, burn rate, and asynchronous freshness | Ambient distraction, fast burn versus slow ticket, Kafka freshness |
| Resilience and architecture | Graceful degradation, contention, saturation, and memory drift | Recommendation fallback, catalog lock contention, slow email memory drift |

The default bank uses actual Astronomy Shop flags such as `paymentFailure`,
`cartFailure`, `kafkaQueueProblems`, `imageSlowLoad`,
`productCatalogLockContention`, and the nested targeted
`productCatalogFailure` rule. Its PromQL examples use the demo's
`traces_span_metrics_calls_total` and
`traces_span_metrics_duration_milliseconds_bucket` series.

## Start the lab

Start Astronomy Shop with its observability services from the repository root:

```bash
docker compose -f compose.yaml -f compose.observability.yaml up -d
```

Then start the learning app:

```bash
cd sre-learning-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open <http://127.0.0.1:8501>. The app remains usable in study mode when the
demo is stopped, but live scenario activation is disabled.

Before activating a scenario, confirm the proxy and observability services are
healthy:

```bash
docker compose -f compose.yaml -f compose.observability.yaml ps
```

The sidebar links to the local tools routed by Astronomy Shop:

- Storefront: <http://localhost:8080>
- Locust: <http://localhost:8080/loadgen/>
- Grafana: <http://localhost:8080/grafana/>
- Jaeger: <http://localhost:8080/jaeger/>

## Safe feature-flag workflow

When you select **Activate hidden scenario**, the app:

1. reads and validates the local flag document;
2. saves the exact original text and parsed document in
   `.state/active-session.json`;
3. resets every flag managed by the selected bank to its safe value;
4. applies only the selected scenario's hidden fault profile through the
   existing flagd UI API; and
5. polls the API to confirm the new state.

Always use **End scenario and restore flags** when finished. If Streamlit or the
browser closes first, restart the app; it detects the recovery file and offers
the restore controls before allowing another activation.

If flags were edited elsewhere during an exercise, normal restore stops and
asks whether to restore the saved snapshot or keep the external changes. The
**Emergency restore** button deliberately overwrites live flags with the saved
snapshot.

Do not delete `.state/active-session.json` while a scenario is active. The
folder is ignored by Git and also stores local learning progress.

## Switch or author a question bank

Put additional `*.yaml` files in `question_banks/` and select them in the
sidebar, or upload a YAML bank for the current browser session. Banks use
`schema_version: 1` and must contain:

```yaml
schema_version: 1
bank:
  id: unique-bank-id
  title: Bank title
  description: What this bank teaches

levels:
  - id: foundations
    title: Level 1
    order: 1
    objective: Learning objective

flag_catalog:
  paymentFailure:
    path: [flags, paymentFailure, defaultVariant]
    variants: ["off", "10%", "100%"]
    safe_variant: "off"

scenarios:
  - id: unique-scenario-id
    level: foundations
    title: Scenario title
    concepts: [SLA, SLO]
    briefing: Learner-visible incident narrative
    critical_user_journey: The user outcome being protected
    service_tier: Tier 1
    sla: {target: 99.9% over 30 days, consequence: Training consequence}
    slos:
      - {indicator: Availability, target: 99.95% over 30 days}
    slis:
      - {name: Success ratio, formula: good / valid, boundary: frontend API}
    error_budget: The allowed bad-event fraction is 0.05%.
    fault_profile:
      - {flag: paymentFailure, variant: "10%"}
    observation_minutes: 5
    tasks: [Measure impact]
    hints: [Start at the user boundary]
    solution:
      root_cause: Hidden cause
      investigation: Model investigation
      remediation: Model response
      learning_notes: Key lesson
      promql: ['example_query']
      expected_evidence: [Expected observation]
    rubric:
      - {id: measure, criterion: I measured user impact., points: 100}
```

Quote YAML values such as `"on"` and `"off"`; otherwise YAML may interpret
them as booleans. Every rubric must total 100 points. Before live activation,
the app also checks mutation paths and variants against
`src/flagd/demo.flagd.json`.

The product-catalog targeted failure demonstrates a nested mutation path:

```yaml
path: [flags, productCatalogFailure, targeting, if, 1]
```

## Configuration

Override local defaults with environment variables before starting Streamlit:

| Variable | Default |
| --- | --- |
| `SRE_LAB_SHOP_URL` | `http://localhost:8080` |
| `SRE_LAB_FLAG_API_URL` | `$SRE_LAB_SHOP_URL/feature/api` |
| `SRE_LAB_GRAFANA_URL` | `$SRE_LAB_SHOP_URL/grafana/` |
| `SRE_LAB_JAEGER_URL` | `$SRE_LAB_SHOP_URL/jaeger/` |
| `SRE_LAB_LOADGEN_URL` | `$SRE_LAB_SHOP_URL/loadgen/` |
| `SRE_LAB_FLAG_FILE` | `../src/flagd/demo.flagd.json` |
| `SRE_LAB_STATE_DIR` | `.state/` |

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```
