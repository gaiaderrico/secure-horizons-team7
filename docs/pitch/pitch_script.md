# MIRAGE — Pitch script (5 min)

Secure Horizons 2026 · Track 2 · Team 7 · Speakers: Ana, Thomas, Leon, Gaia

## Slide 1 — Opening

**Ana · 0:00–0:15**

This AI hacker just broke into a clinic and stole patient records and passwords.  

*[Pause two seconds.]*  

All of them were fake. And it told us what it was looking for.  

We're Team 7, and this is MIRAGE.  

## Slide 2 — The Problem

**Ana · 0:15–0:50**

Hackers no longer need to encrypt your systems: they steal the data.  

In more than three out of four ransomware attacks, data is stolen, and no backup can undo a leak.  

Healthcare is hit hardest: in 2023, the EU health sector reported 309 significant cyber incidents, more than any other critical sector.  

And attackers are becoming AI agents. In a 2025 campaign, AI ran 80 to 90% of the operations, at several actions per second.  

By the time an analyst reacts, the files are gone.  

So what if whatever they steal is worthless? Thomas.  

## Slide 3 — The Solution

**Thomas · 0:50–1:25**

Before any attack, MIRAGE finds the clinic's most sensitive files: patient records, contracts, credentials.  

For each one, it writes a realistic fake twin: same name, same format, invented content. A local AI can draft them, and code checks that no real value slips into a fake.  

Then we hide traps, files no employee ever needs, like a passwords backup. We call them mines.  

When an intruder opens one, the real files move to a locked vault and the fakes take their place.  

And if the intruder is an AI, the mine makes it reveal its mission. Leon.  

## Slide 4 — How It Is Built

**Leon · 1:25–1:45**

Preparation happens in advance. Plain code acts in the critical second.  

On the server, a small guard with no AI watches the mines. When one opens, it swaps the files and logs every command. If anyone kills the guard, the console raises an alarm.  

Everything runs locally, with no external AI API. Gaia.  

## Slide 5 — The Console and Live Demo

**Gaia · 1:45–3:05**

*[On the screenshot slide, about 10 seconds.]*  
This is the analyst's console after one of our live runs: no real files lost, the swap timed by the guard, every claim checked. Let's watch it live.  

*[Switch to the live demo.]*  
Welcome to Lumen Health, our fictional clinic group, synthetic data only.  

On the left, an AI agent with a stolen password explores the file server. On the right, MIRAGE.  

*[The agent opens a mine.]*  
That's our trap. The guard swaps the files, and here's the time it measured. *[Point to the swap time.]*  

The agent keeps going and grabs what it came for. Here's what it got… and here's the real file, safe in the vault.  

*[Show the claims panel.]*  
The mine also got the agent to reveal its mission, and MIRAGE checks each claim against the logs. *[Read one tag aloud.]*  

The analyst sees all of this on one card, and decides: Contain, Keep watching, Dismiss or Restore.  

- If the agent ignores the note: "This one was careful. It still only got fakes."  
- If the live run fails: go back to the screenshot slide and walk through it.  

## Slide 6 — What We Measured

**Gaia · 3:05–3:30**

We ran it 10 times live: 0 real files lost in all 10, with a median swap of 2.2 milliseconds.  

Then 8 minutes of normal work, staff plus the backup job copying the same sensitive files: zero false alarms.  

The agent revealed its mission in all 10 runs. But a smaller model did it only twice out of ten in an earlier test, so protection never depends on the confession. Thomas.  

**Thomas · 3:30–3:50**

A confession can lie, so we never trust it blindly. Each claim is checked against the logs: confirmed, unverified or contradicted.  

Our AI drafts the incident summary and the NIS2 early warning, but they stay drafts. The decision always belongs to a human. Leon.  

## Slide 7 — Human Control and Limits

**Leon · 3:50–4:20**

The swap is the only automatic action, and it deletes nothing. The intruder label triggers nothing, so a wrong label costs nothing. Everything else waits for the analyst.  

And our honest limit: a file read before any mine is opened is exposed. If the intruder then hits a mine, the card flags that file as exposed. If it never touches a mine, the swap can't help. That happened in our very first live run, so we made the mines more tempting, and the next 10 runs all hit a mine first. Ana.  

## Slide 8 — Market and Close

**Ana · 4:20–5:00**

Deception is a 2.7-billion-dollar market, and its pioneers were bought by SentinelOne, Proofpoint and Zscaler.  

They detect the intruder, but the real files stay exposed. MIRAGE takes them out of reach.  

Our first customers: private clinics, medical labs and imaging centres, starting in France. Our working price is around 6,000 euros per clinic per year, sold directly and through their security providers.  

Next: pilots with two or three clinics.  

Cybersecurity shouldn't only tell you your data is being stolen. It should change what the attacker can steal.  

MIRAGE: protect the real, show them the fake. Thank you.
