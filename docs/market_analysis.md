# MIRAGE — Market Analysis

**Project:** MIRAGE  
**Industry:** Cybersecurity / Deception Technology / AI-Assisted Threat Detection  
**Target market:** European mid-sized businesses (50–249 employees) and Managed Security Service Providers (MSSPs)  
**Research date:** October 2026

MIRAGE protects a company's most sensitive files against data theft: when an intruder opens a trap file ("mine"), the real files are swapped for realistic fakes in under a second. If the intruder is an AI agent, the trap also makes it reveal its mission. This document analyses the market the project addresses. Market figures come from the public sources listed at the end. Market sizing, pricing and commercial milestones are marked as assumptions: the project has no customers or revenue yet.

## 1. Executive summary

The project targets a real, growing and consolidating market: deception technology, worth about USD 2.7 billion in 2025 and forecast to reach USD 7.3 billion by 2034 (IMARC).

- **The threat has shifted to data theft.** More than 76% of ransomware attacks involved data exfiltration in Q3 2025 (Coveware). Backups do not undo a leak.
- **Smaller companies are hit hardest.** Ransomware was involved in 88% of breaches at small and mid-sized businesses, against 39% at large organisations (Verizon DBIR 2025).
- **Attackers are becoming AI agents.** In the GTG-1002 campaign, AI ran about 80–90% of tactical operations at several requests per second (Anthropic).
- **Big vendors have absorbed the deception pioneers.** SentinelOne bought Attivo (~USD 617 million, 2022), Proofpoint bought Illusive (2022), Zscaler bought Smokescreen (2021). Deception now ships as a feature of large platforms aimed at large enterprises.
- **The gap:** existing deception products detect the intruder but leave the real files exposed. We found no commercial product that takes the real data out of reach the moment a trap is touched.
- **The most exposed buyers are under-served:** the EU's 251,000 mid-sized enterprises (Eurostat), many now pulled into NIS2 (~15,000 entities in France), which increasingly outsource security to managed providers.

## 2. Market definition

The project sits where three markets overlap; deception technology is the core one.

| Market | What it covers | How the project relates |
| --- | --- | --- |
| Deception technology (core) | Decoys, honeyfiles, honeytokens and fake credentials that expose intruders | Uses mines and beacons, like existing products |
| Data-theft protection (DLP, data security, data loss detection) | Stopping or detecting sensitive data leaving the organisation | Its response goal: whatever is stolen is worthless |
| Defence against AI-driven attacks (emerging) | Detecting and disrupting autonomous AI attackers | Its bonus layer: identify an AI intruder and make it reveal its mission |

The buying context is the SOC: tools like this are run by the security team or by the managed security service provider (MSSP) that runs the SOC for the client.

## 3. Market size and growth

### 3.1 Top-down: the markets MIRAGE sits in

| Market | Size | Forecast | Growth | Source |
| --- | --- | --- | --- | --- |
| Deception technology, global | USD 2.7 B (2025) | USD 7.3 B (2034) | 11.4% CAGR, 2026–2034 | IMARC |
| Deception technology, global | USD 1.8 B (2021) | USD 5.8 B (2031) | 12.2% CAGR, 2022–2031 | Allied Market Research |
| Managed security services, Europe | USD 11.4 B (2025) | USD 39.5 B (2034) | 14.9% CAGR, 2026–2034 | Market Data Forecast |

Within deception, Allied Market Research expects small and mid-size enterprises to be the fastest-growing segment, while large enterprises hold the largest share today. IMARC links SME adoption to low initial costs. These are analyst estimates with different scopes and base years, so they should be quoted as ranges.

### 3.2 Reference population

The EU had about **251,000 medium-sized enterprises** (50–249 employees) in 2024: 0.8% of all enterprises, but 15.2% of employment and 17.2% of turnover (Eurostat). Not all are realistic customers: companies with little sensitive digital data or no relevant infrastructure are excluded below.

### 3.3 Bottom-up estimate *(assumption-based)*

**Serviceable segment:** 5–10% of EU medium-sized enterprises, about **12,550–25,100** organisations. This share is a modelling assumption to be refined with sector counts, security budgets and customer interviews.

At an assumed annual subscription of **€6,000** (our hypothesis, set below Thinkst Canary's median of ~USD 9,900 a year; to be validated with customers):

| Scenario | Potential customers | Annual subscription value |
| --- | ---: | ---: |
| Lower assumption (5%) | 12,550 | €75.3 M |
| Upper assumption (10%) | 25,100 | €150.6 M |

These figures are **theoretical capacity at 100% adoption** within the assumed segment, not market spending or a forecast.

### 3.4 Initial commercial objective *(planning scenario)*

- 10–25 paying customers in year one
- Average annual contract of €6,000
- **€60,000–€150,000** in annual recurring revenue

This depends on successful pilots, acquisition costs, product reliability and support capacity.

## 4. Drivers and trends

| Trend | Evidence | What it means for this market |
| --- | --- | --- |
| Data theft is the main extortion lever | > 76% of ransomware attacks involved exfiltration; payment rate fell to 23%, 19% for theft-only attacks (Q3 2025) | Protecting the data itself matters more than restoring systems |
| Smaller firms are hit hardest | Ransomware in 88% of SMB breaches vs 39% at large organisations; median ransom paid USD 115,000; 64% of victims did not pay (Verizon DBIR 2025) | The under-equipped middle market is the main victim |
| Attackers move toward mid-size firms | Akira and Qilin (44% of Q3 2025 attacks) shifted toward medium-sized companies | The middle market is now the target |
| Breaches are costly and slow to contain, worst in health | Global average USD 4.44 M; US healthcare USD 7.42 M, costliest sector for 14 years; 279 days to identify and contain in health; 16% of breaches involved attacker AI (2025) | Response time is the weak point |
| AI agents run attacks | GTG-1002: ~30 targets, 80–90% of tactical work by AI, several operations per second; stopped when the provider banned the accounts | Defence must react in seconds, not hours |
| Regulation and outsourcing | NIS2: 24 h early warning, fines ≥ €10 M or 2% of turnover; > 99% of the EU's 33 M+ enterprises are SMEs, many relying on external providers | Compliance budgets open; MSSPs become the buying channel |

**Healthcare examples:** the 2024 Change Healthcare breach reached 192.7 million people. In France, ANSSI recorded 30 ransomware compromises of health facilities in 2022–2023, about 10% of ransomware incidents reported to it.

## 5. Competitors

None of the competitors we found swaps the real data for fakes on first contact.

### Direct: deception platforms

| Company | Status | What it does | Gap versus the project |
| --- | --- | --- | --- |
| Attivo Networks | Acquired by SentinelOne for ~USD 617 M (announced March 2022); 300+ customers | Decoys and honeypots, then Active Directory identity protection, now in SentinelOne's XDR | Detection; real files stay exposed |
| Illusive Networks | Acquired by Proofpoint (announced Dec 2022); ~USD 54 M raised before | Decoy-based breach detection, focused on lateral movement | Same |
| Smokescreen | Acquired by Zscaler (announced May 2021) | Decoys across network, endpoints and applications, inside Zscaler's Zero Trust Exchange | Same; tied to the Zscaler platform |
| Fortinet FortiDeceptor | Part of Fortinet's security platform | Decoys across the network, threat analysis, incident isolation, integration with Fortinet products | Built for Fortinet environments; heavier for mid-sized firms |
| Acalvio ShadowPlex | Independent; USD 17 M Series A+B (2016) | Auto-generated, changing decoys across IT, identity, cloud and OT | Decoy systems, not protection of the real files |
| CounterCraft | Independent, Spain; USD 5 M round (2020) | Decoy infrastructure, digital twins and counter-intelligence; defence, intelligence and finance customers | Aimed at large, mature organisations |
| Thinkst Canary / Canarytokens | Independent; free Canarytokens | Simple honeypots and tokens; high-signal alerts; popular with small teams | Alerts only; real files stay exposed |

### Indirect: other ways to protect data

| Category | Example | Why it is indirect |
| --- | --- | --- |
| Data loss detection with decoy documents | Allure Security (Columbia spin-out, 8+ US patents on beaconing and deception) | Detects and tracks stolen documents; does not swap the originals |
| DLP and data security suites | Data classification and blocking tools | Rules on data leaving; little help once an intruder uses valid credentials |
| EDR / MDR services | Endpoint detection, often sold through MSSPs | Detect and isolate machines at human speed; can also be partners |

### Emerging: defence against AI attackers

| Project | Status | What it does | Gap |
| --- | --- | --- | --- |
| Mantis | Research, George Mason University | Prompt injection in decoy services to derail AI attackers; reports > 95% effectiveness | Includes a "counterstrike" mode that takes over the attacker's machine (hack back); no data protection |

**Consolidation signal:** three of the best-known deception start-ups were bought by large platforms in 2021–2022. Buyers value the technology, and there is room for an independent, lightweight product aimed at mid-size firms.

## 6. Positioning

|  | **Detects the intruder** | **Protects the real data** |
| --- | --- | --- |
| **Platform, large enterprise** | SentinelOne (Attivo), Proofpoint (Illusive), Zscaler (Smokescreen), Fortinet, Acalvio, CounterCraft | DLP and data security suites |
| **Lightweight, mid-size** | Thinkst Canary, Allure Security, Mantis (research) | **MIRAGE** (open space) |

Competitors are placed by quadrant, not by exact score. MIRAGE's differentiation remains a hypothesis until prototype comparisons and customer feedback support it.

## 7. Segmentation

### By sector

| Sector | Sensitive data | Why it matters |
| --- | --- | --- |
| Healthcare (clinics, labs, hospitals) | Patient records, results, billing | Costliest breaches of any sector; NIS2 essential entities; frequent ransomware target in France |
| Software and IT services | Source code, customer data, credentials | Data-intensive; technically able to deploy |
| Legal, accounting and consulting | Contracts, client files, payroll | Client confidentiality; leaks used for extortion; small IT teams |
| Engineering, research and manufacturing | Designs, quotes, IP, supplier contracts | Espionage and extortion; NIS2 manufacturing sectors |
| Public sector and local government | Citizen records | In NIS2 scope; tight budgets |

### By company size

| Size | Security set-up | Fit |
| --- | --- | --- |
| Large enterprises (250+ staff) | In-house SOC, already buying platform deception | Served by SentinelOne, Proofpoint, Zscaler, Fortinet, Acalvio |
| Mid-size (50–249 staff, NIS2 threshold) | Small IT team, outsourced SOC | Under-served; fastest-growing deception segment; 251,000 in the EU |
| Small businesses (< 50 staff) | No security team | Mostly outside NIS2; price-sensitive |

**By deployment:** on-premises file servers versus cloud storage. Cloud adoption is growing, so a product limited to file servers covers only part of the market.

**By buying channel:** direct to the company, or through MSSPs and MDR providers that run SOCs for many clients.

## 8. Targeting

Recommended first target: **mid-size healthcare organisations under NIS2, reached through the MSSPs that run their SOC.**

| Criterion | Mid-size healthcare | Why |
| --- | --- | --- |
| Pain | Very high | Costliest breaches, longest containment (279 days), patient data used for extortion |
| Regulatory pressure | High | Hospitals and major private clinics are NIS2 essential entities |
| Competition | Low | Platform deception vendors focus on large enterprises |
| Ability to buy | Medium | Small security teams; buying often through the MSSP |
| Fit with the product | High | Patient files and billing data sit on shared drives, the exact scope protected |

- **Second wave:** software companies, legal, accounting and payroll firms (concentrated sensitive files, small teams).
- **Channel:** MSSPs and MDR providers; one partner gives access to many mid-size clients, and the European MSS market grows ~15% a year.
- **Not first:** large enterprises (served by incumbents) and very small businesses (mostly outside NIS2).

This recommendation is drawn from the data above and still needs to be validated through interviews with clinic IT managers and MSSPs.

## 9. Buyers and users

| Role | Part in the decision | What they look for |
| --- | --- | --- |
| Director / CEO / medical director | Signs the budget | Cost of a breach versus cost of the tool; reputation |
| IT manager or CISO | Recommends and deploys | Easy install, no disruption to staff, very few false alarms |
| SOC analyst (in-house or at the MSSP) | Daily user | Clear alerts, fast and safe actions, fewer alerts to sort |
| DPO / compliance officer | Influences | Evidence for NIS2 and GDPR breach notifications |
| MSSP / MDR provider | Reseller or operator | A service to add to existing contracts, multi-client management |

### Customer requirements

| Requirement | Implication for MIRAGE |
| --- | --- |
| Limited IT resources | Simple installation and management |
| Existing security investments | Complements current tools (SIEM, EDR) |
| Data confidentiality | Fake twins must contain no real values (checked by code) |
| Reliability | False alerts and disruption minimised; every swap reversible |
| Compliance | Configurable logging, access control and retention; supports NIS2 24 h early warning |
| Budget limits | Price must reflect demonstrable value |

## 10. Business model and pricing

### Market pricing benchmarks

| Product | Public price data |
| --- | --- |
| Thinkst Canary | Median USD 9,900 / year; range USD 5,100–13,620; no public list price; unlimited canary tokens included (Vendr transaction data) |
| Enterprise deception (SentinelOne, Proofpoint, Zscaler, Fortinet, Acalvio) | Not published; sold inside larger platform contracts |
| Cost being avoided | Average breach USD 4.44 M globally; median ransom payment USD 140,000 (Coveware, Q3 2025) |

### Pricing hypothesis *(not validated)*

| Plan | Proposed annual price | Intended customer |
| --- | ---: | --- |
| Starter | €3,000 | Small IT teams, limited deployments |
| Business | €6,000 | Mid-sized companies with several protected resources |
| Enterprise | From €15,000 | Larger or more complex environments |
| MSSP | Custom | Providers managing several organisations |

These prices are preliminary assumptions, not validated willingness-to-pay figures. Optional onboarding, configuration and integration services could complement subscriptions.

## 11. Go-to-market

1. **Customer discovery:** interview IT managers, security consultants and MSSPs about monitoring gaps and willingness to adopt deception.
2. **Controlled pilots:** deploy in authorised test environments alongside existing tools; measure deployment time, detection, false positives and investigation effort.
3. **Initial adoption:** mid-sized firms with clear file-security needs (healthcare first, then software and professional services); MSSP partnerships as second channel.
4. **Expansion:** integrations (SIEM, cloud storage APIs), multi-client features for MSSPs, broader European rollout.

## 12. Demand validation

Market research shows a relevant problem; it **does not prove customers will buy MIRAGE**.

| Hypothesis | Validation method | Initial target |
| --- | --- | --- |
| Customers have the problem | Structured interviews | 10–15 interviews |
| Existing tools leave a gap | Competitor and workflow assessment | 3–5 customer demos |
| MIRAGE adds operational value | Controlled technical testing | Measurable improvement over a baseline |
| Companies will deploy it | Supervised pilot | 2–3 pilot organisations |
| Customers will pay | Pricing interviews, pilot conversion | At least 2 serious expressions of interest |

These are proposed milestones, not completed achievements.

## 13. PESTEL and Porter's five forces

### PESTEL

| Factor | Effect on the market |
| --- | --- |
| Political | EU push for cyber sovereignty; state-linked groups use AI agents (GTG-1002) |
| Economic | Breaches cost millions; mid-size firms have small security budgets and outsource |
| Social | Patient and client trust; public reporting of health-data leaks |
| Technological | AI attackers act in seconds; LLMs make realistic fake documents cheap to produce; shift to cloud storage |
| Environmental | Minor factor |
| Legal | NIS2 (24 h early warning, fines ≥ €10 M or 2%), GDPR breach notification, DORA for finance, AI Act human oversight |

### Porter's five forces

| Force | Level | Why |
| --- | --- | --- |
| Rivalry | Medium-high | Big platforms bundle deception; many security tools compete for the same budget |
| Threat of new entrants | High | A basic swap mechanism is simple to copy; AI lowers the cost of building decoys |
| Threat of substitutes | Medium | EDR/MDR, DLP, backups and cyber insurance address parts of the same risk |
| Buyer power | Medium | Mid-size buyers are price-sensitive; MSSPs aggregate demand and negotiate |
| Supplier power | Low | Built on open-source tools; LLM providers are interchangeable (local models work) |

## 14. Barriers to entry and market risks

| Risk or barrier | Why it matters | How to address it |
| --- | --- | --- |
| Incumbents copy the idea | SentinelOne, Proofpoint, Zscaler and Fortinet already own deception tech and large customer bases | Focus on the mid-size segment they serve least; sell through MSSPs |
| Trust: "you move our files?" | A wrong swap could disrupt care or business | Reversible by design, only crown jewels move, false-positive rate shown openly |
| Backups and antivirus can open traps | Risk of false alarms | Identify the process that opens the file before acting |
| Cloud storage | Much sensitive data no longer sits on file servers | Same logic via storage APIs (versioning, permissions) as a later step |
| Attacker copies data before touching a trap | That data is lost | Place traps where attackers look first; state this limit openly |
| AI reliability | Summaries and confessions can be wrong | Every claim checked against recorded evidence |
| Commercial viability | Support and infrastructure costs may exceed small subscriptions | MSSP channel; simple deployment |
| Sales cycles and certification | Health and public buyers expect references and certifications | Pilots, published test results, partnerships with known MSSPs |

## 15. Conclusion

MIRAGE addresses a real and growing problem: ransomware is involved in 88% of SMB breaches, data theft is the main extortion lever, and AI attackers move faster than human response. Deception is a proven category with established competitors, which validates the approach but raises the bar.

MIRAGE's opportunity is to make data-protecting deception accessible to the EU's 251,000 mid-sized firms and the MSSPs that serve them. Success depends on three things:

1. demonstrating measurable defensive effectiveness;
2. delivering a simpler, more valuable experience than existing tools for this segment;
3. validating that customers will adopt and pay for it.

---

## Sources

- [IMARC — Global deception technology market](https://www.imarcgroup.com/global-deception-technology-market)
- [Allied Market Research — Deception technology market](https://alliedmarketresearch.com/press-release/deception-technology-market.html)
- [Market Data Forecast — Europe managed security services market](https://www.marketdataforecast.com/market-reports/europe-managed-security-services-market)
- [Verizon — 2025 Data Breach Investigations Report](https://www.verizon.com/business/resources/T16f/reports/2025-dbir-data-breach-investigations-report.pdf)
- [The Record — Ransomware in half of all data breaches (Verizon DBIR 2025 summary)](https://therecord.media/ransomware-in-half-of-all-data-breaches-verizon)
- [Eurostat — Large businesses in the EU: small number, high turnover (Dec 2025)](https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20251209-2)
- [ENISA — Threat Landscape](https://www.enisa.europa.eu/topics/cyber-threats/threat-landscape)
- [ENISA — Cybersecurity for SMEs](https://www.enisa.europa.eu/topics/awareness-and-cyber-hygiene/smes-cybersecurity)
- [BleepingComputer — Coveware Q3 2025 ransomware data](https://www.bleepingcomputer.com/news/security/ransomware-profits-drop-as-victims-stop-paying-hackers/amp)
- [HIPAA Journal — IBM Cost of a Data Breach 2025, healthcare](https://www.hipaajournal.com/average-cost-of-a-healthcare-data-breach-2025/)
- [Anthropic — Disrupting the first reported AI-orchestrated cyber espionage campaign](https://www-cdn.anthropic.com/d7dd50dd1185f59be051b307150d877f2b82bd2c.pdf)
- [CyberInsider — Change Healthcare breach revised to 192.7 million](https://cyberinsider.com/change-healthcare-revises-breach-impact-to-192-7-million-individuals/)
- [IT-Connect — ANSSI: 30 French hospitals hit by ransomware in two years](https://www.it-connect.fr/30-hopitaux-francais-victimes-ransomware-en-2-ans-rapport-anssi/)
- [Numeum — NIS2 in France](https://numeum.fr/en/cybersecurity/nis2-directive-understanding-the-new-european-cybersecurity-framework-and-its-impact-on-businesses-in-france/)
- [nisd2.eu — What is NIS2](https://nisd2.eu/en/what-is-nis2)
- [TechTarget — SentinelOne acquires Attivo Networks](https://www.techtarget.com/cybersecurity/news/252514653/SentinelOne-acquires-Attivo-Networks-for-617M)
- [SecurityWeek — Proofpoint buys Illusive Networks](https://www.securityweek.com/proofpoint-buys-deception-tech-startup-illusive-networks)
- [Zscaler — Zscaler to acquire Smokescreen](https://www.zscaler.com/press/zscaler-acquire-smokescreen-enhance-zscaler-zero-trust-exchange-advanced-active-defense)
- [Fortinet — FortiDeceptor](https://www.fortinet.com/products/fortideceptor)
- [Acalvio — ShadowPlex](https://www.acalvio.com/shadowplex-platform/)
- [TechCrunch — Acalvio emerges with USD 17 M](https://techcrunch.com/2016/07/26/acalvio-emerges-from-stealth-with-17m-to-bring-its-deception-based-cybersecurity-system-to-market)
- [CounterCraft — Products](https://www.countercraftsec.com/products/)
- [Tech.eu — CounterCraft raises USD 5 M](https://tech.eu/2020/06/17/countercraft-fundraise/)
- [Thinkst Canary](https://canary.tools/)
- [Vendr — Thinkst Canary pricing](https://vendr.com/buyer-guides/thinkst-canary)
- [Dark Reading — Allure Security data loss detection platform](https://www.darkreading.com/endpoint-security/allure-security-unveils-data-loss-detection-and-response-platform)
- [arXiv — Hacking Back the AI-Hacker (Mantis)](https://arxiv.org/html/2410.20911v2)

*Research note: market-sizing scenarios, pricing and commercial milestones are analytical assumptions as of October 2026. They are not verified demand, actual sales or measured MIRAGE prototype results.*