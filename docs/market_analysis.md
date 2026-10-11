# MIRAGE — Market Analysis

**Project:** MIRAGE  
**Industry:** Cybersecurity / Deception Technology / AI-Assisted Threat Detection  
**Target market:** clinics and the medical sector in Europe: private clinics and clinic groups, medical laboratories and imaging centres, starting in France; reached directly and through the Managed Security Service Providers (MSSPs) that run their SOC  
**Research date:** October 2026

MIRAGE protects a clinic's most sensitive files (patient records, lab results, billing data, credentials) against data theft: when an intruder opens a trap file ("mine"), the real files are swapped for realistic fakes in under a second. If the intruder is an AI agent, the trap also makes it reveal its mission. This document analyses the market the project addresses. Market figures come from the public sources listed at the end. Market sizing, pricing and commercial milestones are marked as assumptions: the project has no customers or revenue yet.

## 1. Executive summary

The project targets a real, growing and consolidating market: deception technology, worth about USD 2.7 billion in 2025 and forecast to reach USD 7.3 billion by 2034 (IMARC).

- **The threat has shifted to data theft.** More than 76% of ransomware attacks involved data exfiltration in Q3 2025 (Coveware). Backups do not undo a leak.
- **Healthcare is the most attacked critical sector in the EU.** The health sector reported 309 significant cyber incidents in 2023, more than any other critical sector (European Commission, Jan 2025). Ransomware accounted for 54% of health-sector incidents, and 46% of incidents aimed to steal or leak data (ENISA, 2023).
- **Healthcare breaches cost the most.** USD 7.42 M on average, the costliest sector for 14 years, and 279 days to identify and contain (IBM Cost of a Data Breach 2025).
- **Attackers are becoming AI agents.** In the GTG-1002 campaign, AI ran about 80–90% of tactical operations at several requests per second (Anthropic).
- **Big vendors have absorbed the deception pioneers.** SentinelOne bought Attivo (~USD 617 million, 2022), Proofpoint bought Illusive (2022), Zscaler bought Smokescreen (2021). Deception now ships as a feature of large platforms aimed at large enterprises.
- **The gap:** existing deception products detect the intruder but leave the real files exposed. We found no commercial product that takes the real data out of reach the moment a trap is touched.
- **Our target: clinics and the medical sector.** Private clinics, medical labs and imaging centres keep patient files on shared drives, run small IT teams, often rely on an outsourced SOC, and are now in NIS2 scope (healthcare is a high-criticality sector). France alone has about 1,000 private clinics (FHP, 2026), and 46% of them were in deficit in 2025, so the product must be light and affordable.

## 2. Market definition

The project sits where three markets overlap; deception technology is the core one.

| Market | What it covers | How the project relates |
| --- | --- | --- |
| Deception technology (core) | Decoys, honeyfiles, honeytokens and fake credentials that expose intruders | Uses mines and beacons, like existing products |
| Data-theft protection (DLP, data security, data loss detection) | Stopping or detecting sensitive data leaving the organisation | Its response goal: whatever is stolen is worthless |
| Defence against AI-driven attacks (emerging) | Detecting and disrupting autonomous AI attackers | Its bonus layer: identify an AI intruder and make it reveal its mission |

The buying context is the clinic's IT team and its SOC: tools like this are run by the clinic's IT or security team, or by the managed security service provider (MSSP) that runs the SOC for the clinic.

## 3. Market size and growth

### 3.1 Top-down: the markets MIRAGE sits in

| Market | Size | Forecast | Growth | Source |
| --- | --- | --- | --- | --- |
| Deception technology, global | USD 2.7 B (2025) | USD 7.3 B (2034) | 11.4% CAGR, 2026–2034 | IMARC |
| Deception technology, global | USD 1.8 B (2021) | USD 5.8 B (2031) | 12.2% CAGR, 2022–2031 | Allied Market Research |
| Managed security services, Europe | USD 11.4 B (2025) | USD 39.5 B (2034) | 14.9% CAGR, 2026–2034 | Market Data Forecast |

Within deception, Allied Market Research expects small and mid-size enterprises to be the fastest-growing segment, while large enterprises hold the largest share today. IMARC links SME adoption to low initial costs. These are analyst estimates with different scopes and base years, so they should be quoted as ranges. We found no published figure for deception technology in healthcare alone.

### 3.2 Reference population: clinics and the medical sector

| Population | Count | Source |
| --- | ---: | --- |
| Private clinics and private hospitals, France | about 1,000 | FHP (Fédération de l'hospitalisation privée), April 2026 |
| Private clinics, medical labs and imaging centres, EU | not yet sized | To be built from national registries (e.g. FINESS in France) |

We found no reliable EU-wide count of private clinics, medical laboratories and imaging centres, so we do not quote one. Building it from national health-establishment registries is part of the validation work.

### 3.3 Bottom-up estimate *(assumption-based)*

**Beachhead: French private clinics.** At an assumed annual subscription of **€6,000 per clinic** (our hypothesis, set below Thinkst Canary's median of ~USD 9,900 a year; to be validated with clinics):

| Scenario | Clinics | Annual subscription value |
| --- | ---: | ---: |
| All French private clinics (theoretical) | ~1,000 | ~€6 M |
| 10% of French private clinics *(assumption)* | ~100 | ~€0.6 M |

These figures are **theoretical capacity**, not market spending or a forecast. Medical labs, imaging centres and other EU countries add to this once counted; the EU-wide figure is: number of target clinics × €6,000.

### 3.4 Initial commercial objective *(planning scenario)*

- 10–25 paying clinics in year one
- Average annual contract of €6,000 per clinic
- **€60,000–€150,000** in annual recurring revenue

This depends on successful clinic pilots, acquisition costs, product reliability and support capacity.

## 4. Drivers and trends

| Trend | Evidence | What it means for this market |
| --- | --- | --- |
| Data theft is the main extortion lever | > 76% of ransomware attacks involved exfiltration; payment rate fell to 23%, 19% for theft-only attacks (Q3 2025) | Protecting the data itself matters more than restoring systems |
| Health is the EU's most attacked critical sector | 309 significant incidents in 2023, more than any other critical sector (European Commission); ransomware 54% of health incidents; 53% of incidents hit healthcare providers, 42% hospitals; patient data the most targeted asset (30%) (ENISA) | Clinics and their patient data are a prime target |
| Smaller organisations are hit hardest | Ransomware in 88% of SMB breaches vs 39% at large organisations; median ransom paid USD 115,000; 64% of victims did not pay (Verizon DBIR 2025) | Clinics with small IT teams are exposed |
| Attackers move toward mid-size firms | Akira and Qilin (44% of Q3 2025 attacks) shifted toward medium-sized companies | The middle market is now the target |
| Breaches are costly and slow to contain, worst in health | Global average USD 4.44 M; healthcare USD 7.42 M, costliest sector for 14 years; 279 days to identify and contain in health; 16% of breaches involved attacker AI (2025) | Response time is the weak point |
| AI agents run attacks | GTG-1002: ~30 targets, 80–90% of tactical work by AI, several operations per second; stopped when the provider banned the accounts | Defence must react in seconds, not hours |
| Regulation and outsourcing | NIS2 lists healthcare providers among high-criticality sectors (large ones are essential entities, medium ones important entities): 24 h early warning, fines up to €10 M or 2% of turnover for essential entities; GDPR treats health data as a special category | Compliance budgets open; MSSPs become the buying channel |

**Healthcare examples:** the 2024 Change Healthcare breach reached 192.7 million people. In France, ANSSI recorded 30 ransomware compromises of health facilities in 2022–2023, about 10% of ransomware incidents reported to it.

## 5. Competitors

None of the competitors we found swaps the real data for fakes on first contact.

### Direct: deception platforms

| Company | Status | What it does | Gap versus the project |
| --- | --- | --- | --- |
| Attivo Networks | Acquired by SentinelOne for ~USD 617 M (announced March 2022); 300+ customers | Decoys and honeypots, then Active Directory identity protection, now in SentinelOne's XDR | Detection; real files stay exposed |
| Illusive Networks | Acquired by Proofpoint (announced Dec 2022); ~USD 54 M raised before | Decoy-based breach detection, focused on lateral movement | Same |
| Smokescreen | Acquired by Zscaler (announced May 2021) | Decoys across network, endpoints and applications, inside Zscaler's Zero Trust Exchange | Same; tied to the Zscaler platform |
| Fortinet FortiDeceptor | Part of Fortinet's security platform | Decoys across the network, threat analysis, incident isolation, integration with Fortinet products | Built for Fortinet environments; heavier for a clinic's small IT team |
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

**Consolidation signal:** three of the best-known deception start-ups were bought by large platforms in 2021–2022. Buyers value the technology, and there is room for an independent, lightweight product aimed at clinics and the medical sector.

## 6. Positioning

|  | **Detects the intruder** | **Protects the real data** |
| --- | --- | --- |
| **Platform, large enterprise** | SentinelOne (Attivo), Proofpoint (Illusive), Zscaler (Smokescreen), Fortinet, Acalvio, CounterCraft | DLP and data security suites |
| **Lightweight, clinics and mid-size** | Thinkst Canary, Allure Security, Mantis (research) | **MIRAGE** (open space) |

Competitors are placed by quadrant, not by exact score. MIRAGE's differentiation remains a hypothesis until prototype comparisons and customer feedback support it.

## 7. Segmentation

Our market is **clinics and the medical sector**. Segmentation is done inside healthcare; other sectors are listed only as later expansion.

### Inside healthcare

| Segment | Sensitive data on file servers | Security set-up | Fit |
| --- | --- | --- | --- |
| **Private clinics and clinic groups** | Patient records, discharge letters, billing, staff credentials | Small IT team, often an outsourced SOC | **Core target** |
| **Medical laboratories** | Test results linked to patient identities, billing | Small IT team; networks of sites | **Core target** |
| **Imaging and radiology centres** | Reports, patient identities, billing | Small IT team | **Core target** |
| Public hospitals | Patient records at large scale | Larger IT teams; public procurement | Later: long sales cycles |
| Large hospital groups | Patient records across many sites | In-house SOC, platform security | Later: served by platform vendors |
| Small practices (GPs, dentists) | Few files, mostly in practice software | No IT team | Not targeted: price-sensitive, mostly outside NIS2 |

**By deployment:** on-premises file servers versus cloud storage. Many clinics still keep shared drives on site, but cloud adoption is growing, so a product limited to file servers covers only part of the market.

**By buying channel:** direct to the clinic or clinic group, or through MSSPs and MDR providers that run SOCs for several healthcare clients.

### Later expansion (outside the initial focus)

Software and IT services, legal and accounting firms, engineering and research: the same problem (sensitive files on shared drives, small IT teams), to be addressed only after the healthcare offer is validated.

## 8. Targeting

First target: **private clinics, medical laboratories and imaging centres in Europe, starting in France, reached directly and through the MSSPs that run their SOC.**

| Criterion | Clinics, labs, imaging centres | Why |
| --- | --- | --- |
| Pain | Very high | Costliest breaches, longest containment (279 days), patient data used for extortion |
| Regulatory pressure | High | Healthcare providers are in NIS2 scope (large ones essential, medium ones important entities); GDPR special-category health data |
| Competition | Low | Platform deception vendors focus on large enterprises and hospital groups |
| Ability to buy | Medium | Tight budgets (46% of French private clinics in deficit in 2025, FHP); buying often through the MSSP |
| Fit with the product | High | Patient files and billing data sit on shared drives, the exact scope protected |

- **Next in healthcare:** clinic groups (multi-site) and hospital groups, once pilots give references.
- **Channel:** MSSPs and MDR providers that serve healthcare; one partner gives access to many clinics, and the European MSS market grows ~15% a year.
- **Not first:** large hospital groups (served by incumbents), small practices (no IT team), and sectors outside healthcare.

This choice is drawn from the data above and still needs to be validated through interviews with clinic, lab and imaging-centre IT managers and with MSSPs.

## 9. Buyers and users

| Role | Part in the decision | What they look for |
| --- | --- | --- |
| Clinic director / medical director | Signs the budget | Cost of a breach versus cost of the tool; continuity of care; patient trust |
| IT manager or CISO | Recommends and deploys | Easy install, no disruption to staff, very few false alarms |
| SOC analyst (in-house or at the MSSP) | Daily user | Clear alerts, fast and safe actions, fewer alerts to sort |
| DPO / compliance officer | Influences | Evidence for NIS2 and GDPR breach notifications (health data is special-category) |
| MSSP / MDR provider serving clinics | Reseller or operator | A service to add to existing contracts, multi-client management |

### Customer requirements

| Requirement | Implication for MIRAGE |
| --- | --- |
| Limited IT resources | Simple installation and management |
| Existing security investments | Complements current tools (SIEM, EDR) |
| Data confidentiality | Fake twins must contain no real values (checked by code) |
| Reliability | No disruption to care; false alerts minimised; every swap reversible |
| Compliance | Configurable logging, access control and retention; supports NIS2 24 h early warning |
| Budget limits | Price must reflect demonstrable value |

## 10. Business model and pricing

### Market pricing benchmarks

| Product | Public price data |
| --- | --- |
| Thinkst Canary | Median USD 9,900 / year; range USD 5,100–13,620; no public list price; unlimited canary tokens included (Vendr transaction data) |
| Enterprise deception (SentinelOne, Proofpoint, Zscaler, Fortinet, Acalvio) | Not published; sold inside larger platform contracts |
| Cost being avoided | Average healthcare breach USD 7.42 M (IBM 2025); average breach USD 4.44 M globally; median ransom payment USD 140,000 (Coveware, Q3 2025) |

### Pricing hypothesis *(not validated)*

| Plan | Proposed annual price | Intended customer |
| --- | ---: | --- |
| Starter | €3,000 | A single lab or imaging centre, one file server |
| Clinic | €6,000 | One clinic with several protected shares |
| Group | From €15,000 | Clinic groups and multi-site lab networks |
| MSSP | Custom | Providers managing several clinics |

These prices are preliminary assumptions, not validated willingness-to-pay figures. Optional onboarding, configuration and integration services could complement subscriptions.

## 11. Go-to-market

1. **Customer discovery:** interview IT managers of clinics, medical labs and imaging centres, and MSSPs serving healthcare, about monitoring gaps and willingness to adopt deception.
2. **Controlled pilots:** 2–3 clinics, in authorised test environments alongside existing tools; measure deployment time, detection, false positives and investigation effort.
3. **Initial adoption:** private clinics, labs and imaging centres in France, sold directly and through MSSP partnerships.
4. **Expansion:** clinic and hospital groups, other EU countries, integrations (SIEM, cloud storage APIs), multi-client features for MSSPs; other sectors only later.

## 12. Demand validation

Market research shows a relevant problem; it **does not prove customers will buy MIRAGE**.

| Hypothesis | Validation method | Initial target |
| --- | --- | --- |
| Clinics have the problem | Structured interviews | 10–15 interviews with clinic, lab and imaging IT managers and MSSPs |
| Existing tools leave a gap | Competitor and workflow assessment | 3–5 customer demos |
| MIRAGE adds operational value | Controlled technical testing | Measurable improvement over a baseline |
| Clinics will deploy it | Supervised pilot | 2–3 pilot clinics |
| Clinics will pay | Pricing interviews, pilot conversion | At least 2 serious expressions of interest |

These are proposed milestones, not completed achievements.

## 13. PESTEL and Porter's five forces

### PESTEL

| Factor | Effect on the market |
| --- | --- |
| Political | EU push for cyber sovereignty; state-linked groups use AI agents (GTG-1002) |
| Economic | Healthcare breaches cost the most (USD 7.42 M); clinics have tight budgets (46% of French private clinics in deficit in 2025) and outsource security |
| Social | Patient trust; public reporting of health-data leaks; continuity of care |
| Technological | AI attackers act in seconds; LLMs make realistic fake documents cheap to produce; shift to cloud storage |
| Environmental | Minor factor |
| Legal | NIS2 (healthcare in scope, 24 h early warning), GDPR (health data is special-category, breach notification), health-data hosting rules (HDS certification in France if health data is hosted), AI Act human oversight |

### Porter's five forces

| Force | Level | Why |
| --- | --- | --- |
| Rivalry | Medium-high | Big platforms bundle deception; many security tools compete for the same budget |
| Threat of new entrants | High | A basic swap mechanism is simple to copy; AI lowers the cost of building decoys |
| Threat of substitutes | Medium | EDR/MDR, DLP, backups and cyber insurance address parts of the same risk |
| Buyer power | Medium | Clinics are price-sensitive; MSSPs aggregate demand and negotiate |
| Supplier power | Low | Built on open-source tools; LLM providers are interchangeable (local models work) |

## 14. Barriers to entry and market risks

| Risk or barrier | Why it matters | How to address it |
| --- | --- | --- |
| Incumbents copy the idea | SentinelOne, Proofpoint, Zscaler and Fortinet already own deception tech and large customer bases | Focus on clinics, labs and imaging centres, which they serve least; sell through MSSPs |
| Trust: "you move our patient files?" | A wrong swap could disrupt care | Reversible by design, only crown jewels move, false-positive rate shown openly |
| Backups and antivirus can open traps | Risk of false alarms | Identify the process that opens the file before acting |
| Cloud storage | Much sensitive data no longer sits on file servers | Same logic via storage APIs (versioning, permissions) as a later step |
| Attacker copies data before touching a trap | That data is lost | Place traps where attackers look first; state this limit openly |
| AI reliability | Summaries and confessions can be wrong | Every claim checked against recorded evidence |
| Commercial viability | Support and infrastructure costs may exceed small subscriptions | MSSP channel; simple deployment |
| Sales cycles and certification | Clinics expect references; HDS certification needed in France if we host health data | Pilots, published test results, partnerships with known MSSPs |

## 15. Conclusion

MIRAGE addresses a real and growing problem for clinics and the medical sector: health is the EU's most attacked critical sector (309 significant incidents in 2023), healthcare breaches cost the most (USD 7.42 M), data theft is the main extortion lever, and AI attackers move faster than human response. Deception is a proven category with established competitors, which validates the approach but raises the bar.

MIRAGE's opportunity is to make data-protecting deception accessible to private clinics, medical laboratories and imaging centres, starting with France's ~1,000 private clinics, and to the MSSPs that serve them. Success depends on three things:

1. demonstrating measurable defensive effectiveness in clinic pilots;
2. delivering a simpler, more valuable experience than existing tools for a clinic's small IT team;
3. validating that clinics will adopt and pay for it.

---

## Sources

- [IMARC — Global deception technology market](https://www.imarcgroup.com/global-deception-technology-market)
- [Allied Market Research — Deception technology market](https://alliedmarketresearch.com/press-release/deception-technology-market.html)
- [Market Data Forecast — Europe managed security services market](https://www.marketdataforecast.com/market-reports/europe-managed-security-services-market)
- [Verizon — 2025 Data Breach Investigations Report](https://www.verizon.com/business/resources/T16f/reports/2025-dbir-data-breach-investigations-report.pdf)
- [The Record — Ransomware in half of all data breaches (Verizon DBIR 2025 summary)](https://therecord.media/ransomware-in-half-of-all-data-breaches-verizon)
- [European Commission action plan on health-sector cybersecurity (Help Net Security, Jan 2025)](https://www.helpnetsecurity.com/?p=321075)
- [ENISA — Threat Landscape: Health Sector (ransomware 54%)](https://www.enisa.europa.eu/node/11067)
- [Caducée — FHP: 46% of private clinics in deficit in 2025 (~1,000 clinics)](https://www.caducee.net/actualite-medicale/16852/hopitaux-prives-pourquoi-46-des-etablissements-etaient-en-deficit-en-2025.html)
- [ENISA — Threat Landscape](https://www.enisa.europa.eu/topics/cyber-threats/threat-landscape)
- [ENISA — Cybersecurity for SMEs](https://www.enisa.europa.eu/topics/awareness-and-cyber-hygiene/smes-cybersecurity)
- [BleepingComputer — Coveware Q3 2025 ransomware data](https://www.bleepingcomputer.com/news/security/ransomware-profits-drop-as-victims-stop-paying-hackers/amp)
- [HIPAA Journal — IBM Cost of a Data Breach 2025, healthcare](https://www.hipaajournal.com/average-cost-of-a-healthcare-data-breach-2025/)
- [TechTarget — Healthcare remains costliest industry for breaches at USD 7.42 M](https://www.techtarget.com/healthtechsecurity/news/366628031/Healthcare-remains-costliest-industry-for-breaches-at-742M)
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