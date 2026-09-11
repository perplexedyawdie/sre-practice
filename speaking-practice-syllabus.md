
### **Module 1: Foundations of Reliability (The "Why")**
**Speaking Prompts (The "Versus" Debates):**
*   **100% Reliability vs. Innovation Velocity:** Argue why aiming for 100% uptime is an engineering anti-pattern. Explain how the Error Budget is actually a tool for *protecting* feature releases, not just restricting them.
*   **Global SLIs vs. Segmented SLIs:** If the global checkout success rate is 99.9%, but 100% of PayPal users are failing, is the SLA met? Debate the tradeoff of metric cardinality (grouping by payment method) vs. Prometheus storage costs.
*   **Good vs. Valid Requests:** When a botnet spams your Cart service with malformed HTTP 400 requests, how do you mathematically exclude them from the denominator of your SLI so your error budget doesn't falsely burn?

**On-Camera Scenario Seed:**
> *"The VP of Product wants a 99.99% SLA on the 'Recommended Products' carousel. Walk through the conversation where you negotiate them down to 99.5%, map out the Error Budget, and explain what happens to the dev team when the budget runs out."*

---

### **Module 2: Observability Primitives (The "How")**
**Speaking Prompts (The "Versus" Debates):**
*   **Averages (p50) vs. Tail Latency (p95/p99):** Speak critically about why a dashboard showing "Average Latency: 45ms" is dangerous. Explain bimodal distributions (e.g., cache hits vs. cache misses).
*   **Logs vs. Metrics vs. Traces:** Argue why logs are the *worst* primary alerting tool (cost, speed, parsing fragility) and why metrics are best. Then explain why metrics are useless for *finding* the root cause without distributed traces.
*   **Synthetic Monitoring (k6/Locust) vs. Real User Monitoring (RUM):** Contrast the pristine, predictable nature of synthetic probes against the noisy, device-fragmented reality of RUM.

**On-Camera Scenario Seed:**
> *"Customers complain that checkout is hanging, but your Grafana dashboard shows Checkout CPU is normal and average latency is fine. Whiteboard how you would use a distributed trace to prove that 5% of requests are silently timing out due to a lock contention in the Redis cart cache."*

---

### **Module 3: Alerting & Incident Response (The "Action")**
**Speaking Prompts (The "Versus" Debates):**
*   **Cause-Based Alerting vs. Symptom-Based Alerting:** Defend the philosophy of deleting alerts for "High CPU" or "DB Connection Pool 80% Full." Argue why you should only page humans for "Checkout SLI burning."
*   **Short-Window (Fast Burn) vs. Long-Window (Slow Burn):** Explain the math tradeoff. If you alert on a 5-minute window, you get pager fatigue from transient spikes. If you alert on a 24-hour window, the budget is empty before the pager fires. Explain Google's multi-burn-rate solution.
*   **Hero Culture vs. Blameless Culture:** Critically analyze why a company relying on the "10x engineer" who memorizes the architecture to save the day during an incident is inherently unscalable and fragile.

**On-Camera Scenario Seed:**
> *"It's Black Friday. You get paged. The Ad Service is crash-looping and throwing 10,000 errors a minute. The Checkout Service is throwing 50 errors a minute. Talk through your Incident Command triage process. Justify why you completely ignore the Ad Service and focus on Checkout."*

---

### **Module 4: Resilient Architecture & Tradeoffs (The "Engineering")**
**Speaking Prompts (The "Versus" Debates):**
*   **Retries vs. Fail-Fast (The Retry Storm):** Explain how a well-intentioned 3x gRPC retry policy can turn a 2-second network blip into a self-sustaining metastable failure (DDoS-ing your own database). Argue for Circuit Breakers and Exponential Backoff.
*   **Synchronous RPC vs. Asynchronous Events:** Tradeoff analysis of a user clicking "Submit Order." If it's a sync gRPC call to the shipping and email services, availability drops. If it's async (Kafka), the UI is fast, but how do you handle a failed email?
*   **Hard Failures vs. Graceful Degradation:** Defend the architectural choice to return HTTP 200 with an empty recommendation list rather than HTTP 500 when the backend ML engine times out. 

**On-Camera Scenario Seed:**
> *"The 3rd-party Payment Gateway API goes down completely. Rather than losing millions in revenue, explain how you would architect a 'degraded mode' that securely queues authorized carts locally, returns a success message to the user, and reconciles the payments asynchronously when the API recovers."*

---

### **Module 5: Philosophies Borrowed from Other Fields**
**Speaking Prompts (The "Versus" Debates):**
*   **Human Error vs. System Flaw (Safety Science):** Contrast the "Bad Apple" theory (fire the engineer who deleted the DB) with the "New Look" theory (the system lacked guardrails to prevent a typo from dropping the DB).
*   **Chaos Engineering vs. Disaster Recovery (Immunology):** Argue why traditional "yearly DR failover tests" are useless compared to continuous, automated chaos injection during business hours.
*   **Automation vs. Automation Surprise (Control Theory):** Discuss the paradox of automation: the more an auto-scaler or failover script handles minor issues, the more complex and catastrophic the failure will be when the automation finally encounters an edge case it can't handle.

**On-Camera Scenario Seed:**
> *"A Junior Engineer accidentally bypassed `flagd` and hardcoded a change that brought down the Frontend for 40 minutes. The CEO is demanding they be reprimanded. Record your verbal brief to the CEO defending a Blameless Post-Mortem and outlining the systemic fixes (CI/CD guardrails, peer review enforcement) instead."*

---

### **Module 6: Future Directions**
**Speaking Prompts (The "Versus" Debates):**
*   **eBPF vs. Application SDKs:** Contrast dropping an eBPF agent into a Kubernetes node (instant network/CPU metrics, no code changes) versus instrumenting an app with the OpenTelemetry SDK (requires developer time, but provides rich business context).
*   **Agentic AI SRE vs. Human-in-the-Loop:** Debate the risks of allowing an AI agent (like the ones evaluated in SREGym) to execute `kubectl patch` or `rollout restart` autonomously in production versus restricting it to read-only diagnosis.
*   **High Reliability vs. GreenOps/FinOps:** Speak critically about the diminishing returns of 99.999%. The cost (carbon footprint and AWS bill) to go from 99.9% to 99.99% is massive. How do you argue for *less* infrastructure?

**On-Camera Scenario Seed:**
> *"The CFO mandates a 30% reduction in cloud infrastructure spend. Whiteboard a strategy using FinOps and Tiered Reliability to identify which services (like the Ad and Recommendation services) can have their replicas cut in half and SLOs lowered, while preserving the compute resources for the Tier 1 Checkout path."*