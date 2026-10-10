Project: MIRAGE

Industry: Cybersecurity / Deception Technology / AI-Assisted Threat Detection

Target Market: European SMEs, mid-sized businesses and Managed Security Service Providers (MSSPs)

Research Date: October 2026



MIRAGE protects a company's most sensitive files against data theft: when an intruder opens a trap file ("mine"), the real files are swapped for realistic fakes in under a second. If the intruder is an AI agent, the trap also makes it reveal its mission. This document analyses the market the project addresses. All figures come from the public sources listed at the end; the project has no customers, revenue or pricing yet.



Executive summary



The project targets a real, growing and consolidating market: deception technology, worth about USD 2.7 billion in 2025 and forecast to reach USD 7.3 billion by 2034 (IMARC).



The threat has shifted to data theft. More than 76% of ransomware attacks involved data exfiltration in Q3 2025 (Coveware). Backups do not undo a leak.

Attackers are becoming AI agents. In the GTG-1002 campaign, AI ran about 80–90% of tactical operations at several requests per second (Anthropic).

Big vendors have absorbed the deception pioneers. SentinelOne bought Attivo (\~USD 617 million, 2022), Proofpoint bought Illusive (2022), Zscaler bought Smokescreen (2021). Deception now ships as a feature of large platforms aimed at large enterprises.

The gap: existing deception products detect the intruder but leave the real files exposed. We found no commercial product that takes the real data out of reach the moment a trap is touched.

The most exposed buyers are under-served: mid-size organisations holding sensitive data, now pulled into NIS2 (\~15,000 entities in France), which increasingly outsource security to managed providers.





\## 2. Market definition



The project sits where three markets overlap; deception technology is the core one.



| Market | What it covers | How the project relates |

| --- | --- | --- |

| Deception technology (core) | Decoys, honeyfiles, honeytokens and fake credentials that expose intruders | Uses mines and beacons, like existing products |

| Data-theft protection (DLP, data security, data loss detection) | Stopping or detecting sensitive data leaving the organisation | Its response goal: whatever is stolen is worthless |

| Defence against AI-driven attacks (emerging) | Detecting and disrupting autonomous AI attackers | Its bonus layer: identify an AI intruder and make it reveal its mission |



The buying context is the SOC: tools like this are run by the security team or by the managed security service provider (MSSP) that runs the SOC for the client.



\## 3. Market size and growth



| Market | Size | Forecast | Growth | Source |

| --- | --- | --- | --- | --- |

| Deception technology, global | USD 2.7 B (2025) | USD 7.3 B (2034) | 11.4% CAGR, 2026–2034 | IMARC |

| Deception technology, global | USD 1.8 B (2021) | USD 5.8 B (2031) | 12.2% CAGR, 2022–2031 | Allied Market Research |

| Managed security services, Europe | USD 11.4 B (2025) | USD 39.5 B (2034) | 14.9% CAGR, 2026–2034 | Market Data Forecast |



Within deception, Allied Market Research expects small and mid-size enterprises to be the fastest-growing segment, while large enterprises hold the largest share today. IMARC links SME adoption to low initial costs. These are analyst estimates with different scopes and base years, so they should be quoted as ranges.

\## 4. Drivers and trends



| Trend | Evidence | What it means for this market |

| --- | --- | --- |

| Data theft is the main extortion lever | > 76% of ransomware attacks involved exfiltration; payment rate fell to 23%, 19% for theft-only attacks (Q3 2025) | Protecting the data itself matters more than restoring systems |

| Attackers move toward mid-size firms | Akira and Qilin (44% of Q3 2025 attacks) shifted toward medium-sized companies | The under-equipped middle market is now the target |

| Breaches are costly and slow to contain, worst in health | Global average USD 4.44 M; US healthcare USD 7.42 M, costliest sector for 14 years; 279 days to identify and contain in health; 16% of breaches involved attacker AI (2025) | Response time is the weak point |

| AI agents run attacks | GTG-1002: \~30 targets, 80–90% of tactical work by AI, several operations per second; stopped when the provider banned the accounts | Defence must react in seconds, not hours |

| Regulation and outsourcing | NIS2: 24 h early warning, fines ≥ €10 M or 2% of turnover; > 99% of the EU's 33 M+ enterprises are SMEs, many relying on external providers | Compliance budgets open; MSSPs become the buying channel |



\*\*Healthcare examples:\*\* the 2024 Change Healthcare breach reached 192.7 million people. In France, ANSSI recorded 30 ransomware compromises of health facilities in 2022–2023, about 10% of ransomware incidents reported to it.

\## 5. Competitors



None of the competitors we found swaps the real data for fakes on first contact.



\### Direct: deception platforms



| Company | Status | What it does | Gap versus the project |

| --- | --- | --- | --- |

| Attivo Networks | Acquired by SentinelOne for \~USD 617 M (announced March 2022); 300+ customers | Decoys and honeypots, then Active Directory identity protection, now in SentinelOne's XDR | Detection; real files stay exposed |

| Illusive Networks | Acquired by Proofpoint (announced Dec 2022); \~USD 54 M raised before | Decoy-based breach detection, focused on lateral movement | Same |

| Smokescreen | Acquired by Zscaler (announced May 2021) | Decoys across network, endpoints and applications, inside Zscaler's Zero Trust Exchange | Same; tied to the Zscaler platform |

| Acalvio | Independent; USD 17 M Series A+B (2016) | Auto-generated, changing decoys of real systems with fake data | Decoy systems, not protection of the real files |

| CounterCraft | Independent, Spain; USD 5 M round (2020) | Decoy infrastructure and counter-intelligence; defence, intelligence and finance customers | Aimed at large, mature organisations |

| Thinkst Canary | Independent | Simple honeypots and unlimited canary tokens; popular with small teams | Alerts only |



\### Indirect: other ways to protect data



| Category | Example | Why it is indirect |

| --- | --- | --- |

| Data loss detection with decoy documents | Allure Security (Columbia spin-out, 8+ US patents on beaconing and deception) | Detects and tracks stolen documents; does not swap the originals |

| DLP and data security suites | Data classification and blocking tools | Rules on data leaving; little help once an intruder uses valid credentials |

| EDR / MDR services | Endpoint detection, often sold through MSSPs | Detect and isolate machines at human speed; can also be partners |



\### Emerging: defence against AI attackers



| Project | Status | What it does | Gap |

| --- | --- | --- | --- |

| Mantis | Research, George Mason University | Prompt injection in decoy services to derail AI attackers; reports > 95% effectiveness | Includes a "counterstrike" mode that takes over the attacker's machine (hack back); no data protection |



\*\*Consolidation signal:\*\* three of the best-known deception start-ups were bought by large platforms in 2021–2022. Buyers value the technology, and there is room for an independent, lightweight product aimed at mid-size firms.



\## 6. Positioning



|  | \*\*Detects the intruder\*\* | \*\*Protects the real data\*\* |

| --- | --- | --- |

| \*\*Platform, large enterprise\*\* | SentinelOne (Attivo), Proofpoint (Illusive), Zscaler (Smokescreen), Acalvio, CounterCraft | DLP and data security suites |

| \*\*Lightweight, mid-size\*\* | Thinkst Canary, Allure Security, Mantis (research) | \*\*MIRAGE\*\* (open space) |



Competitors are placed by quadrant, not by exact score.



\## 7. Segmentation



\### By sector



| Sector | Sensitive data | Why it matters |

| --- | --- | --- |

| Healthcare (clinics, labs, hospitals) | Patient records, results, billing | Costliest breaches of any sector; NIS2 essential entities; frequent ransomware target in France |

| Legal and notarial | Case files, contracts, identity documents | Client secrecy; leaks used for extortion |

| Accounting, payroll, financial services | Payslips, tax files, bank details | Hold many clients' data at once; DORA for finance |

| Manufacturing and industry | Designs, quotes, supplier contracts | Espionage and extortion; NIS2 manufacturing sectors |

| Public sector and local government | Citizen records | In NIS2 scope; tight budgets |



\### By company size



| Size | Security set-up | Fit |

| --- | --- | --- |

| Large enterprises | In-house SOC, already buying platform deception | Served by SentinelOne, Proofpoint, Zscaler, Acalvio |

| Mid-size (50–250+ staff, NIS2 threshold) | Small IT team, outsourced SOC | Under-served; fastest-growing deception segment |

| Small businesses (< 50 staff) | No security team | Mostly outside NIS2; price-sensitive |



\*\*By deployment:\*\* on-premises file servers versus cloud storage. Cloud adoption is growing, so a product limited to file servers covers only part of the market.



\*\*By buying channel:\*\* direct to the company, or through MSSPs and MDR providers that run SOCs for many clients.



\## 8. Targeting



Recommended first target: \*\*mid-size healthcare organisations under NIS2, reached through the MSSPs that run their SOC.\*\*



| Criterion | Mid-size healthcare | Why |

| --- | --- | --- |

| Pain | Very high | Costliest breaches, longest containment (279 days), patient data used for extortion |

| Regulatory pressure | High | Hospitals and major private clinics are NIS2 essential entities |

| Competition | Low | Platform deception vendors focus on large enterprises |

| Ability to buy | Medium | Small security teams; buying often through the MSSP |

| Fit with the product | High | Patient files and billing data sit on shared drives, the exact scope protected |



\- \*\*Second wave:\*\* legal, accounting and payroll firms (concentrated sensitive files, small teams).

\- \*\*Channel:\*\* MSSPs and MDR providers; one partner gives access to many mid-size clients, and the European MSS market grows \~15% a year.

\- \*\*Not first:\*\* large enterprises (served by incumbents) and very small businesses (mostly outside NIS2).



This recommendation is drawn from the data above and still needs to be validated through interviews with clinic IT managers and MSSPs.



\## 9. Buyers and users



| Role | Part in the decision | What they look for |

| --- | --- | --- |

| Director / CEO / medical director | Signs the budget | Cost of a breach versus cost of the tool; reputation |

| IT manager or CISO | Recommends and deploys | Easy install, no disruption to staff, very few false alarms |

| SOC analyst (in-house or at the MSSP) | Daily user | Clear alerts, fast and safe actions, fewer alerts to sort |

| DPO / compliance officer | Influences | Evidence for NIS2 and GDPR breach notifications |

| MSSP / MDR provider | Reseller or operator | A service to add to existing contracts, multi-client management |



\## 10. Market pricing benchmarks



| Product | Public price data |

| --- | --- |

| Thinkst Canary | Median USD 9,900 / year; range USD 5,100–13,620; no public list price; unlimited canary tokens included (Vendr transaction data) |

| Enterprise deception (SentinelOne, Proofpoint, Zscaler, Acalvio) | Not published; sold inside larger platform contracts |

| Cost being avoided | Average breach USD 4.44 M globally; median ransom payment USD 140,000 (Q3 2025) |



The project's own price is not set yet.



\## 11. PESTEL and Porter's five forces



\### PESTEL



| Factor | Effect on the market |

| --- | --- |

| Political | EU push for cyber sovereignty; state-linked groups use AI agents (GTG-1002) |

| Economic | Breaches cost millions; mid-size firms have small security budgets and outsource |

| Social | Patient and client trust; public reporting of health-data leaks |

| Technological | AI attackers act in seconds; LLMs make realistic fake documents cheap to produce; shift to cloud storage |

| Environmental | Minor factor |

| Legal | NIS2 (24 h early warning, fines ≥ €10 M or 2%), GDPR breach notification, DORA for finance, AI Act human oversight |



\### Porter's five forces



| Force | Level | Why |

| --- | --- | --- |

| Rivalry | Medium-high | Big platforms bundle deception; many security tools compete for the same budget |

| Threat of new entrants | High | A basic swap mechanism is simple to copy; AI lowers the cost of building decoys |

| Threat of substitutes | Medium | EDR/MDR, DLP, backups and cyber insurance address parts of the same risk |

| Buyer power | Medium | Mid-size buyers are price-sensitive; MSSPs aggregate demand and negotiate |

| Supplier power | Low | Built on open-source and cloud tools; LLM providers are interchangeable (local models work) |



\## 12. Barriers to entry and market risks



| Risk or barrier | Why it matters | How to address it |

| --- | --- | --- |

| Incumbents copy the idea | SentinelOne, Proofpoint and Zscaler already own deception tech and large customer bases | Focus on the mid-size segment they serve least; sell through MSSPs |

| Trust: "you move our files?" | A wrong swap could disrupt care or business | Reversible by design, only crown jewels move, false-positive rate shown openly |

| Backups and antivirus can open traps | Risk of false alarms | Identify the process that opens the file before acting |

| Cloud storage | Much sensitive data no longer sits on file servers | Same logic via storage APIs (versioning, permissions) as a later step |

| Attacker copies data before touching a trap | That data is lost | Place traps where attackers look first; state this limit openly |

| Sales cycles and certification | Health and public buyers expect references and certifications | Pilots, published test results, partnerships with known MSSPs |



\## Sources



\- \[IMARC — Global deception technology market](https://www.imarcgroup.com/global-deception-technology-market)

\- \[Allied Market Research — Deception technology market](https://alliedmarketresearch.com/press-release/deception-technology-market.html)

\- \[Market Data Forecast — Europe managed security services market](https://www.marketdataforecast.com/market-reports/europe-managed-security-services-market)

\- \[BleepingComputer — Coveware Q3 2025 ransomware data](https://www.bleepingcomputer.com/news/security/ransomware-profits-drop-as-victims-stop-paying-hackers/amp)

\- \[HIPAA Journal — IBM Cost of a Data Breach 2025, healthcare](https://www.hipaajournal.com/average-cost-of-a-healthcare-data-breach-2025/)

\- \[Anthropic — Disrupting the first reported AI-orchestrated cyber espionage campaign](https://www-cdn.anthropic.com/d7dd50dd1185f59be051b307150d877f2b82bd2c.pdf)

\- \[CyberInsider — Change Healthcare breach revised to 192.7 million](https://cyberinsider.com/change-healthcare-revises-breach-impact-to-192-7-million-individuals/)

\- \[IT-Connect — ANSSI: 30 French hospitals hit by ransomware in two years](https://www.it-connect.fr/30-hopitaux-francais-victimes-ransomware-en-2-ans-rapport-anssi/)

\- \[Numeum — NIS2 in France](https://numeum.fr/en/cybersecurity/nis2-directive-understanding-the-new-european-cybersecurity-framework-and-its-impact-on-businesses-in-france/)

\- \[nisd2.eu — What is NIS2](https://nisd2.eu/en/what-is-nis2)

\- \[TechTarget — SentinelOne acquires Attivo Networks](https://www.techtarget.com/cybersecurity/news/252514653/SentinelOne-acquires-Attivo-Networks-for-617M)

\- \[SecurityWeek — Proofpoint buys Illusive Networks](https://www.securityweek.com/proofpoint-buys-deception-tech-startup-illusive-networks)

\- \[Zscaler — Zscaler to acquire Smokescreen](https://www.zscaler.com/press/zscaler-acquire-smokescreen-enhance-zscaler-zero-trust-exchange-advanced-active-defense)

\- \[TechCrunch — Acalvio emerges with USD 17 M](https://techcrunch.com/2016/07/26/acalvio-emerges-from-stealth-with-17m-to-bring-its-deception-based-cybersecurity-system-to-market)

\- \[Tech.eu — CounterCraft raises USD 5 M](https://tech.eu/2020/06/17/countercraft-fundraise/)

\- \[Vendr — Thinkst Canary pricing](https://vendr.com/buyer-guides/thinkst-canary)

\- \[Dark Reading — Allure Security data loss detection platform](https://www.darkreading.com/endpoint-security/allure-security-unveils-data-loss-detection-and-response-platform)

\- \[arXiv — Hacking Back the AI-Hacker (Mantis)](https://arxiv.org/html/2410.20911v2)



