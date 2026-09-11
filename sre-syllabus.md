
### **Module 1: Foundations of Reliability (The "Why")**
*Goal: Shift from binary "is it up?" to statistical user-perceived reliability.*
*   **The SRE Rosetta Stone:** SLAs (Business Contracts) vs. SLOs (Internal Targets) vs. SLIs (Technical Measurements).
*   **The Math of Valid vs. Good:** Defining equations for ratio metrics (e.g., $\frac{\text{Successful Checkouts}}{\text{Total Valid Checkout Attempts}}$).
*   **Error Budgets:** Using math to dictate engineering velocity. When do we freeze feature releases to fix technical debt?
*   **E-Commerce Application:** Classifying services by Critical User Journeys (CUJ).
    *   *Tier 1 (Checkout/Cart):* Hard availability requirements ($99.99\%$).
    *   *Tier 3 (Recommendations/Ads):* Soft requirements; can fail gracefully without halting revenue.
*   **Research Topics:** Google SRE Book (Chapters 2-4), "The Calculus of Service Availability", Error Budget calculation models.

### **Module 2: Observability Primitives & Telemetry Math (The "How")**
*Goal: Learn to extract the truth from distributed systems using RED (Rate, Errors, Duration) metrics.*
*   **Metrics vs. Logs vs. Traces:** Why logs are too slow for alerting, why metrics lack context, and how distributed tracing (OpenTelemetry) bridges the gap.
*   **Why Averages Lie (The Tail Latency Problem):** Bimodal distributions, garbage collection pauses, and the danger of $p50$. Why you must measure $p95$ and $p99$.
*   **PromQL for SREs:** 
    *   `rate()` and `sum()` for availability ratios.
    *   `histogram_quantile()` for latency SLIs.
*   **E-Commerce Application:** Translating a single user clicking "Pay" into a distributed trace spanning the frontend, checkout service, and 3rd-party payment provider, then querying its RED metrics in Prometheus.
*   **Research Topics:** USE Method (Utilization, Saturation, Errors) vs. RED Method, OpenTelemetry Collector architecture, PromQL histogram math.

### **Module 3: Alerting, Toil, & Incident Response (The "Action")**
*Goal: Protect the on-call engineer’s sanity and resolve incidents scientifically.*
*   **Multi-Window, Multi-Burn-Rate Alerting:** Google’s standard alerting algorithm. How to catch a 2% budget burn in 1 hour (page immediately) vs. a 5% burn over 3 days (create Jira ticket).
*   **Symptom vs. Cause Alerting:** Why you alert on the SLI (Checkout failed) and not the cause (CPU is 95%).
*   **Incident Command System (ICS):** Roles during an outage (Commander, Ops, Comm).
*   **E-Commerce Application:** Ignoring "Ad Service CPU High" alerts when Checkout SLIs are green; handling metastable "Retry Storms" when the payment gateway lags.
*   **Research Topics:** Google SRE Book (Chapters 5, 11), The "Greedy Anchoring" cognitive bias in debugging, Blameless Post-Mortems.

### **Module 4: Resilient Architecture & Trade-offs (The "Engineering")**
*Goal: Design systems that survive partial failures.*
*   **Graceful Degradation:** Serving stale cache or hiding UI elements instead of throwing a 500.
*   **Circuit Breakers & Exponential Backoff:** Preventing retry storms from turning a transient network blip into a self-sustaining cascading failure (metastable failure).
*   **Sync vs. Async Boundaries:** Isolating Tier 1 paths from backend batch processing.
*   **E-Commerce Application:** If the Product Catalog goes down, caching previous results. If Kafka queues lag, ensuring the user still gets an "Order Received" HTTP 200 screen.
*   **Research Topics:** Metastable Failures in Distributed Systems, Circuit Breaker Pattern, Little’s Law (Queuing theory).

---

### **Module 5: Philosophies Borrowed from Other Fields**
*SRE is a multidisciplinary engineering practice. Understanding these outside concepts elevates your architectural thinking.*
*   **Control Theory (Mechanical/Chemical Engineering):** Using PID (Proportional-Integral-Derivative) controllers for auto-scaling and rate-limiting. Understanding feedback loops.
*   **Human Factors & Safety Science (Aviation/Nuclear):** "Blameless" culture. Acknowledging that human error is a symptom of poorly designed system constraints, not the root cause. (Research: Sidney Dekker's *Field Guide to Understanding 'Human Error'*).
*   **Epidemiology & Immunology (Biology):** Chaos Engineering. Injecting small, controlled faults (vaccines) to build systemic immunity against catastrophic failures.
*   **Operations Research (Supply Chain):** Queuing theory, bottleneck analysis, and capacity planning.

---

### **Module 6: Future Directions (Based on 2024-2026 SREcon Trends)**
*Where the SRE consulting field is heading right now.*
*   **Agentic SRE & LLM Triage:** Moving beyond "AIOps" anomaly detection. Autonomous agents (like the SREGym framework we discussed) that parse distributed traces, propose hypotheses, and issue read-only `kubectl` commands during incidents to assist human commanders.
*   **eBPF for Zero-Instrumentation Observability:** Using the Linux kernel (eBPF) to auto-discover network maps, RED metrics, and CPU profiling without modifying application source code.
*   **FinOps & GreenOps Integration:** Tying SLOs directly to unit economics and carbon cost. "Do we need 5 replicas running at 3 AM to maintain a 99.9% SLA, or can we accept 99.5% to reduce AWS costs and carbon emissions by 40%?"
*   **Continuous Profiling as standard:** Merging traditional tracing with continuous CPU/Memory profiling to instantly catch memory leaks (like the `recommendationServiceCacheFailure` in Astronomy Shop) in production.

### **Your Immediate Next Steps in the Lab:**
1.  Open Grafana in your Astronomy Shop.
2.  Write a PromQL query for **Checkout Availability** (Module 1 & 2).
3.  Write a PromQL query for **Checkout $p95$ Latency** (Module 2).
4.  Toggle a `flagd` failure, watch the metrics degrade, and calculate the Burn Rate (Module 3).