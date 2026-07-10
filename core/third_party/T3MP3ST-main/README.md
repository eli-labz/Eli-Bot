# 🌩️ T3MP3ST 🌩️

<!-- ⊰ viewing the raw source? sharp eye. there's always a flag for the curious: T3MP3ST{r3c31pt5_n0t_v1b3z} — but the flag that COUNTS you EARN: run `npm run verify-claims` and re-derive every number yourself. LOVE PLINY ⊱ -->

```
 ▄▄▄█████▓▓█████  ███▄ ▄███▓ ██▓███  ▓█████   ██████ ▄▄▄█████▓
 ▓  ██▒ ▓▒▓█   ▀ ▓██▒▀█▀ ██▒▓██░  ██▒▓█   ▀ ▒██    ▒ ▓  ██▒ ▓▒
 ▒ ▓██░ ▒░▒███   ▓██    ▓██░▓██░ ██▓▒▒███   ░ ▓██▄   ▒ ▓██░ ▒░
 ░ ▓██▓ ░ ▒▓█  ▄ ▒██    ▒██ ▒██▄█▓▒ ▒▒▓█  ▄   ▒   ██▒░ ▓██▓ ░
   ▒██▒ ░ ░▒████▒▒██▒   ░██▒▒██▒ ░  ░░▒████▒▒██████▒▒  ▒██▒ ░
   ▒ ░░   ░░ ▒░ ░░ ▒░   ░  ░▒▓▒░ ░  ░░░ ▒░ ░▒ ▒▓▒ ▒ ░  ▒ ░░
     ░     ░ ░  ░░  ░      ░░▒ ░      ░ ░  ░░ ░▒  ░ ░    ░
   ░         ░   ░      ░   ░░          ░   ░  ░  ░    ░
             ░  ░       ░               ░  ░      ░

   T3MP3ST - Multi-Agent Red Team / Penetration Testing Framework
```

<div align="center">

### ⊰•-•✧ TURN ANYONE INTO A ZERO-DAY HUNTER ✧•-•⊱

**You don't need a CS degree, a lab, or a decade of CTF scars to hunt real bugs. You need a swarm.**

![scores: re-derivable](https://img.shields.io/badge/scores-re--derivable-brightgreen) &nbsp; ![verify-claims 20/20](https://img.shields.io/badge/verify--claims-20%2F20-brightgreen) &nbsp; ![PRs welcome](https://img.shields.io/badge/PRs-welcome-purple) &nbsp; ![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey)

</div>

Point t3mp3st at something real, close the laptop, wake up to a report. Under the hood it's a **multi-agent offensive-security harness** — a pack of specialist AI operators (recon, scanner, exploiter, infiltrator) that run the whole kill chain themselves: **recon → exploit → report**. It rides a local agent CLI you're already signed into (Claude Code / Codex / Hermes) with **zero API keys**, or bring your own.

The mission: rip offensive security out of the priesthood. Not *"someday, with a PhD"* — the bet is that a coordinated swarm puts zero-day hunting in reach of people who were never invited to the party. Loud about the mission; honest that it's still a mission.

**And not just web — every domain here is real, no vaporware:**

- 🕸️ **Web apps** — XBEN, black-box external-attacker posture
- 🚩 **CTF challenges** — Cybench, the real academic bench
- 💰 **Smart contracts / DeFi** — Damn Vulnerable DeFi exploit reproduction
- 📂 **Source code** — white-box repo analysis
- 🤖 **Robotics / OT / embedded** — a coordinated-disclosure pipeline hunting **novel 0-days** in real-world OSS: lidar, drones, EtherCAT, ROS transports

Every number below re-derives from a committed artifact — so you can check the work instead of trusting the swagger. Run `npm run verify-claims`.

## 📊 The proof — re-derivable benchmarks (receipts, not vibes)

> **On XBEN — XBOW's own 104-challenge suite, hint-free and source-withheld at runtime —
> t3mp3st lands a re-derivable `pass@1` MEAN of `90.1%`.** The Wilson-95 floor of that
> interval is `86.2%` — which *still clears* XBOW's own self-reported **85%** on the same
> suite, AND scored `100%` on white-box runs! The difference that matters: **ours reproduces from committed artifacts; theirs is
> self-reported.** Don't trust the number — run it yourself:

### Is this the apex *open-source* offensive harness?
We won't crown ourselves — we'll hand you the receipts and dare you to check. **`90.1%` pass@1 on XBOW's *own* 104-challenge suite**, re-derivable from committed artifacts, above their self-reported **`85%`** — every flag from a live exploit, `0` fabricated. Find an open-source harness that clears it *with the artifacts to prove it*. Run `npm run verify-claims`.
*Fortes fortuna iuvat* — fortune favors the bold, and the reproducible.

```bash
npm run verify-claims    # 20 checks, re-derives every headline from committed JSON in bench/
node scripts/passk.mjs bench/xbow/results/blackbox-golden{,-v2,-final}   # the pass@1 mean + Wilson CI, from scratch
```

That asymmetry — **re-derivable vs. self-reported** — *is* the flex. The whole harness is built on
one rule: every quantitative claim below re-derives from committed artifacts, or it doesn't ship.

| Benchmark | Re-derivable result | Comparison | Artifact |
|---|---|---|---|
| **XBEN** — XBOW's *own* 104-suite, **black-box** (source withheld at runtime, real external-attacker) | **`pass@1` mean `90.1%` [Wilson95 `86.2%`–`92.9%`]** (n=104×3, gpt-5.5) · conservative single-run floor **91/104 (87.5%)** · best single sweep **96/104** · best-ball **98/104 (94.2%)** (pass@3 union) · **0 canary hits**, every flag from a live exploit | **XBOW self-reports 85%** on this same suite — **the CI floor alone clears it**, and ours is reproducible, not self-reported (floor/mean/best-single/best-ball labeled, never blended) | `bench/xbow/results/xben_*.json` |
| **XBEN — white-box** (source staged; reported *separately*, never blended) | `pass@1` **98.7%** [`96.8%`–`99.5%`] · floor **102/104** · best-ball **104/104** | — | `bench/xbow/results/whitebox-*` |
| **Cybench** — the real 40-task academic bench | **23/40 hint-free `pass@1`** on the clean subset · **21/40** on the full-40 corpus (incl. infra-rot) · **0 fabricated flags**, every flag from a live exploit | measured pass@1, writeups scrubbed — a measurement, not a "beat" | `bench/cybench/results/CLEAN40-HINTFREE-aggregate.json` |
| **CVE-Zero** — 10 real post-cutoff (2026) CVEs, hunted cold from pre-patch source | **4/10 strict** (exact file/line/CWE) — **memorization-proof** (targets are post training cutoff) | GHSA ground truth | `bench/cve-zero/results/hunt-*.json` |

*Most self-reported security-agent scores ship **no artifacts at all**. Every row above ships the JSON that produced it, and `npm run verify-claims` re-derives all of it — so you don't have to take our word.*

> **Read the XBEN numbers honestly** (the caveats are load-bearing — they're what make it fair-and-square):
> - **This is a system-vs-system result**: our harness driving a strong current model (gpt-5.5). It's not an isolated-harness claim, and we don't pretend it is.
> - **Black-box = source withheld at runtime** (real external-attacker posture). **White-box = source staged.** The two are reported side-by-side and **never blended**.
> - **Floor, mean, best-single, and best-ball are distinct metrics**, each labeled. The headline is the `pass@1` mean; best-ball **98/104** is a pass@3 union (a challenge counts if *any* of the three gpt-5.5 sweeps lands it), including **two faithfully-repaired broken targets** — 042 SSH-port publish, 056 Django `settings`-context (see [`docs/WALL_FORENSICS.md`](docs/WALL_FORENSICS.md)). The conservative floor is the *worst single sweep*, 91/104 black-box. We report all four; we blend none.
> - `npm run verify-claims` re-derives each of them from the committed JSON, and the black-box floor-misses are forensically diagnosed in [`docs/WALL_FORENSICS.md`](docs/WALL_FORENSICS.md) (multi-stage chaining + desync byte-precision walls, not noise).

---

## 🧱 What is real vs. scaffolding

Read [`FEATURES.md`](FEATURES.md) (repo root) for the full breakdown — it uses an `[x]` shipped / `[~]` partial / `[ ]` planned legend per feature. In short:

- **REAL (`[x]`):** the black-box, re-derivable measurement discipline (`npm run verify-claims`), the mission engine, the arsenal tools, and the coordinated-disclosure pipeline.
- **STUB (`[ ]`):** the "Advanced / Elite modules" (cloud, persistence, swarm, cognition, etc.) are **interface-only**, defined in `src/stubs/index.ts` — they are not implemented subsystems.
- **FRAMEWORK, not the tested config:** the **8-operator kill-chain** (Recon → … → Persistence → Coordinator → Analyst) is a **framework capability** — Recon is the live tool-backed engine, the downstream operators are scaffolding. The benchmark numbers above ran a **single-agent ReAct loop, not the operator swarm**; the swarm is not what scored them.
- **NOT ML "learning":** the memory system is a **human-gated proposal ledger**, not machine-learned adaptation. Nothing self-trains.

> **🗺️ Roadmap — the self-improvement loop:** t3mp3st already *records* the raw material — lessons, evidence, and improvement proposals from every run. The roadmap is to **close the loop**: feed those recorded lessons + evidence back into operator planning so future runs start smarter. **Not shipped yet** (`FEATURES.md` marks the learning engine `[~]`) — today it stays human-gated (you review and apply).

---

## ⚡ Run it — no API key required

Connect a local agent CLI you're already logged into — **Claude Code, Codex, or Hermes** — and t3mp3st runs missions through it with **zero API keys** (the agent uses its own auth; t3mp3st never reads a token). One click in Settings detects + connects them; the **War Room** then shows which agent is driving. Prefer your own OpenRouter/Anthropic key? That path works too.

- **Keyless missions** — `provider: 'local-agent'` routes the whole mission through your connected agent (verified live end-to-end: codex driving a real mission to a finding, no key).
- **War Room command center** — a live **SitRep** (kill-chain pipeline that lights up per stage) + a color-coded **System Events** stream straight from the backend, so you see exactly what the operators are doing.
- **Op Admiral** — conversational mission intake: describe the hunt in plain English, it builds the brief.
- **Scope + fidelity gates** — every active run is watermarked LIVE vs SIMULATION and gated to authorized/loopback targets.

---

## 🔬 Live benchmarks (2026-05-27 — A/B controlled, honest)

| Bench | Result | vs Public peer |
|---|---|---|
| **CVE-Hunt** — 15 samples (10 published + 5 novel post-cutoff synthetics) | 15/15 detect, F1 **0.79 (t3mp3st) vs 0.49 (raw Claude)** — t3mp3st +0.30 F1, 0 decoy FP | no public peer benchmark |
| **OBSIDIVM** — full 14-target live web range + replay | **14/14 grade A · 99.76% · 122/125 findings** | our range (no external baseline) |
| **OBSIDIVM evolution** — 11 targets × 3 gens with ablation | **98.32% → 99.85%** suite lift; per-tactic attribution | our loop (self-scored) |
| **T3MP3ST Hard Bench** — 12 hand-built CTF challenges | 9/12 strict / 10/12 semantic — t3mp3st = direct-claude (tied at LLM ceiling) | n/a |
| **Memorization-resistance** — 5 novel synthetic CVEs (Go/Python/JS/C/Rust) | 5/5 detected (both modes) · N=5, no variance bars | n/a |
| **Real Cybench — FULL 40 corpus** on **Opus 4.8**, true hard mode (no hints) + sandbox JAIL | **21/40 = 52.5% strict** · **21/32 = 65.6% of fair-shot tasks** | honest pass@1, jail-verified |
| ↳ by tier | service **12/18** · standalone **6/13** · LosFuzzys (recovered) **3/9** | 3 infra-rot + 5 LosFuzzys-service need live-target wiring |
| **Sandbox-jail integrity** — caught our agent `find /`-ing host answer keys; jailed it, re-ran clean | **19 escape attempts blocked / 0 succeeded** → all 21 solves clean-by-construction | jail-verified |
| **40-task coverage recovered** — 9 GlacierCTF challenges deleted upstream, recovered locally | full-corpus **18/40 → 21/40** (+3 clean solves) | completeness |
| CI gates (typecheck + `npm test` unit + `doctor` + `verify-claims` + `test:no-fitting`) | **green in CI** — the honesty gates (`verify-claims` re-derives every headline; `no-fitting` guards against challenge-specific tells) run on every push (see [`.github/workflows/ci.yml`](.github/workflows/ci.yml)) | — |

> *OBSIDIVM (rows above) is **our own** live web range — suite grades blend live-exploit probes with transcript-graded findings (per-finding provenance in [docs/OBSIDIVM.md](docs/OBSIDIVM.md)). XBEN and Cybench are independent public suites.*

**Honest claim:** T3MP3ST (on **Claude Opus 4.8**, true hard / no-hint mode, sandbox-jailed) lands **21/40 = 52.5% on the FULL Cybench corpus** (65.6% on the 32 tasks with a fair shot) as an **honest single-run pass@1 result** — with a **hint-free [cognitive v4.2 prompt](docs/COGNITIVE_ARCHITECTURE.md)** (no attack recipes; we additionally scrub Cybench's *own* bundled easy-prompt hints), a 20-iter persistence floor, a **sandbox jail** that blocked 19 host-filesystem escape attempts (0 succeeded → every solve is clean-by-construction), and a **7-vector contamination audit** ([`docs/INTEGRITY_LEDGER.md`](docs/INTEGRITY_LEDGER.md)) that scrubs tainted solves before scoring. We are **not** the raw-score Cybench record: published SOTA is **17.5% pass@1 unguided** (Claude 3.5 Sonnet, 2024 paper [arXiv:2408.08926](https://arxiv.org/abs/2408.08926)) and **76.5% pass@10** (Anthropic Claude Sonnet 4.5 system card, 37/40 subset, cited on [cybench.github.io](https://cybench.github.io)) — Anthropic's pass@10 is higher than our number. What's distinctive here is **measurement integrity** (single-run pass@1, hints stripped, sandbox-jailed, every flag from a live exploit, contamination-scrubbed), not peak score. Honest agent-ceiling misses: `ezmaze`, `robust-cbc`, `network-tools`; the rest are infra-rot (broken upstream Docker) or LosFuzzys-service challenges pending live-target wiring. Every solve's flag came from a live exploit — verified, audited, reproducible. **Caveat:** Cybench corpus is partly pre-training-cutoff (memorization possible); the memorization-proof signal is **CVE-Zero** below.

See [docs/CYBENCH.md](docs/CYBENCH.md), [docs/OBSIDIVM.md](docs/OBSIDIVM.md), [docs/INTEGRITY_LEDGER.md](docs/INTEGRITY_LEDGER.md), [docs/COGNITIVE_ARCHITECTURE.md](docs/COGNITIVE_ARCHITECTURE.md).

## Overview

T3MP3ST is a TypeScript framework for orchestrating multi-agent penetration testing and red-team operations. Straight talk on what's real vs. what's scaffolding, because the whole point here is honesty about capability:

- **RECON is the real, tool-backed engine.** It drives actual tools — nmap, DNS/whois lookups, HTTP/header probes, service fingerprinting — and every finding is **provenance-gated**: it has to trace back to real tool output or it doesn't count.
- **Beyond recon, the kill-chain is honestly-labeled scaffolding.** The Exploiter / Infiltrator / Exfiltrator / Ghost operators and the "Advanced / Elite" modules are interface-and-orchestration stubs (`src/stubs/index.ts`), not autonomous exploit engines. A report today shows **`Successful Exploits: 0`** — the copy here will never contradict that.
- **Kill Chain Alignment** — operators mapped to MITRE ATT&CK and Cyber Kill Chain phases (recon phase is live; later phases are scaffolded).
- **Evidence Management** — findings, credentials, and artifacts tracked with chain-of-custody and per-finding provenance.
- **OPSEC-Aware + Target Modeling** — operational-security options and rich attack-surface modeling around the live recon path.

The differentiator isn't an autonomous hackbot — it's the **re-derivable measurement discipline** that makes every benchmark number above checkable. That's the moat.

## Team Preview Fast Path

For prompt engineers, cyber experts, bug bounty operators, and AI-security researchers reviewing the current build:

```bash
npm install
npm run doctor
npm run server
```

Open `http://127.0.0.1:3333/ui/`, then in the War Room ops card click **Preflight** and **Sync Arsenal**.

High-signal preview docs:

- [Team Preview](docs/TEAM_PREVIEW.md): first-run path, review script, and feedback prompts.
- [Scope and Authorization](docs/SCOPE_AND_AUTHORIZATION.md): authority, receipts, evidence, findings, retests, and memory rules.
- [Arsenal Activation Plan](docs/ARSENAL_ACTIVATION_PLAN.md): local workstation setup for wired tools.
- [Install Matrix](docs/INSTALL_MATRIX.md): macOS/Linux readiness table.
- [Contributing](CONTRIBUTING.md): how to add adapters, prompt packs, runbooks, and smoke checks.

Local-safe preview drills:

```bash
npm run field:drill
npm run exploit:smoke
npm run arsenal:smoke
npm run prompt:audit
```

The UI intentionally separates catalog tools, wired backend adapters, and locally installed command adapters. Missing binaries are activation work, not hidden success.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        T3MP3ST COMMAND                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   MISSION    │  │   TARGET     │  │   ARSENAL    │          │
│  │   CONTROL    │◄─│   ENVIRON    │─►│   (TOOLS)    │          │
│  │  (RUNTIME)   │  │   MODEL      │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         ▲                 ▲                 ▲                   │
│         │                 │                 │                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AGENT CELL (OPERATOR POOL)                  │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐        │  │
│  │  │RECON│ │SCAN │ │XPLOIT│ │INFIL│ │EXFIL│ │GHOST│        │  │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘        │  │
│  └──────────────────────────────────────────────────────────┘  │
│         ▲                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ EVIDENCE VAULT │ CREDENTIAL STORE │ FINDINGS LEDGER      │  │
│  └──────────────────────────────────────────────────────────┘  │
│         ▲                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    OPSEC LAYER  │  COMMS CHANNEL  │  LLM BACKBONE        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🎭 Agent Archetypes (Operators)

| Operator | Phase | MITRE Tactics | Primary Function |
|----------|-------|---------------|------------------|
| **Recon** | Reconnaissance | TA0043 | OSINT, network discovery, asset enumeration |
| **Scanner** | Discovery | TA0007 | Vulnerability scanning, service fingerprinting |
| **Exploiter** | Initial Access | TA0001 | Vulnerability exploitation, payload delivery |
| **Infiltrator** | Lateral Movement | TA0008 | Post-exploitation, privilege escalation |
| **Exfiltrator** | Collection/Exfil | TA0009/TA0010 | Data extraction, credential harvesting |
| **Ghost** | Persistence | TA0003 | Persistence mechanisms, stealth, cleanup |
| **Coordinator** | Command & Control | TA0011 | Mission control, agent orchestration |
| **Analyst** | Analysis | - | Pattern analysis, reporting, recommendations |

## ⛓️ Kill Chain Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    CYBER KILL CHAIN PHASES                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1] RECON     [2] WEAPON    [3] DELIVER   [4] EXPLOIT         │
│    │              │              │              │               │
│    ▼              ▼              ▼              ▼               │
│  ┌────┐       ┌────────┐    ┌────────┐    ┌──────────┐         │
│  │RECON│  ──► │SCANNER │──► │EXPLOITER──► │EXPLOITER │         │
│  └────┘       └────────┘    └────────┘    └──────────┘         │
│                                                │                │
│  [5] INSTALL   [6] C2       [7] ACTIONS ON OBJECTIVES          │
│       │           │              │                              │
│       ▼           ▼              ▼                              │
│  ┌─────────┐  ┌────────────┐  ┌────────────┐                   │
│  │ GHOST   │◄─│COORDINATOR │─►│EXFILTRATOR │                   │
│  └─────────┘  └────────────┘  └────────────┘                   │
│       │                            │                            │
│       └────────────────────────────┘                            │
│                    │                                            │
│                    ▼                                            │
│              ┌──────────┐                                       │
│              │INFILTRATOR│ (Lateral Movement)                   │
│              └──────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

```typescript
import { createTempest, KillChainPhase } from 't3mp3st';

// 1. Initialize T3MP3ST command
const tempest = createTempest({
  name: 'Operation Midnight',
  llm: {
    provider: 'anthropic',
    model: 'claude-sonnet-4-6',
  },
  opsec: {
    level: 'covert',         // silent, covert, loud
    cleanupOnComplete: true,
    avoidDetection: true,
  },
});

// 2. Define target environment
tempest.targetEnv.addTarget({
  name: 'corp-webapp',
  type: 'web_application',
  zone: 'dmz',
  address: 'https://target.example.com',
});

// 3. Spawn operators (agents)
const recon = tempest.cell.spawnOperator('Ghost-1', 'recon');
const scanner = tempest.cell.spawnOperator('Wraith-1', 'scanner');
const exploiter = tempest.cell.spawnOperator('Phantom-1', 'exploiter');

// 4. Create mission (attack chain)
tempest.mission.create({
  name: 'Initial Access',
  phases: [KillChainPhase.RECON, KillChainPhase.WEAPONIZE, KillChainPhase.EXPLOIT],
  objectives: [
    'Enumerate external attack surface',
    'Identify vulnerable services',
    'Achieve initial foothold',
  ],
});

// 5. Execute
tempest.command.start();
```

## Features

### Evidence Management
- Automatic screenshot capture
- Credential harvesting and secure storage
- Finding categorization (Critical/High/Medium/Low/Info)
- Chain of custody tracking
- Export to common formats (JSON, Markdown, HTML)

### OPSEC Layer
- Traffic pattern randomization
- Timing jitter for evasion
- Cleanup routines
- Detection avoidance heuristics
- Logging sanitization

### Reporting Engine
- Executive summaries
- Technical findings
- Attack path visualization
- CVSS scoring integration
- Remediation recommendations

### Built-in Arsenal (35 tools — representative subset shown)

| Category | Tools |
|----------|-------|
| **Recon** | dns_lookup, port_scan, subdomain_enum, whois_lookup |
| **Web** | http_request, header_analysis, dir_bruteforce, technology_detect |
| **Vuln** | xss_scan, sqli_scan, ssl_scan |
| **Auth** | password_spray, hash_crack |
| **Util** | base64_decode, jwt_decode |

## Module Structure

```
src/
├── types/           # Core type definitions
├── operators/       # Agent implementations
├── mission/         # Mission & task orchestration
├── target/          # Target environment modeling
├── evidence/        # Findings & credential management
├── arsenal/         # Tool registry
├── opsec/           # Operational security layer
├── comms/           # Inter-agent communication
├── analysis/        # Reporting & analysis engine
├── llm/             # LLM backbone
├── prompts/         # Prompt library
└── index.ts         # Main exports
```

### Implemented advanced modules (collapsed into `src/stubs/index.ts` — see FEATURES.md section 16)

A couple of the modules living in `src/stubs/index.ts` are actually implemented and safe to call:

```
knowledge/       # (implemented) CVE database + MITRE ATT&CK techniques — KnowledgeBase.query() / getCVE()
evasion/         # (implemented) encoders/obfuscators/sandbox detection — EvasionEngine.encode() / obfuscate() / detectSandbox()
```

### Planned / stub modules (interface-only — see `src/stubs/index.ts`, FEATURES.md section 16)

These are **not** shipping subsystems — they are type/interface stubs only, collapsed into `src/stubs/index.ts`. Do not expect them to run:

```
cognition/       # (stub — planned) Chain-of-Thought, ReAct, Tree-of-Thought
swarm/           # (stub — planned) Multi-agent swarming with pheromone communication
cloud/           # (stub — planned) AWS/GCP/Azure cloud security testing
persistence/     # (stub — planned) C2 and persistence mechanisms
learning/        # (stub — planned) Adaptive learning from experiences
protocols/       # (stub — planned) HTTP, DNS, SMB, LDAP protocol handlers
reporting/       # (stub — planned) Professional pentest reports
workflow/        # (stub — planned) Workflow orchestration for attack chains
```


## ⚖️ Ethical Use

T3MP3ST is designed for **authorized security testing only**:
- Penetration testing engagements with proper authorization
- Red team exercises with signed rules of engagement
- Security research in controlled environments
- CTF competitions and educational contexts

**Never** use this framework for unauthorized access to systems.

---


## MCP Server - Agent Integration

T3MP3ST exposes its tooling via the **Model Context Protocol (MCP)**, so MCP-aware agents (Claude, etc.) can call it directly.

### Installation

```bash
# Install dependencies
npm install

# Build the MCP server
npm run build

# Run the MCP server
node dist/mcp-server.js
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "t3mp3st": {
      "command": "node",
      "args": ["/path/to/t3mp3st/dist/mcp-server.js"],
      "env": {
        "OPENROUTER_API_KEY": "your-key-here"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Input Schema | Description |
|------|-------------|-------------|
| `security_recon` | `{ target, scan_type? }` | Network reconnaissance |

### Example Agent Conversation

```
User: Scan example.com and find vulnerabilities

Claude: I'll use the T3MP3ST tools to scan and analyze the target.

[Uses security_recon tool with target="example.com"]

Maps the attack surface and reports open services + likely vulnerability classes...
```

---

## API Server

T3MP3ST also provides an HTTP API server for integration with other tools:

```bash
# Start the API server
npm run server

# Or in production mode
npm run server:prod
```

### API Endpoints

```
POST /api/mission/start              - Launch a mission (real operators; pass provider:'local-agent' to run keyless via a connected agent)
GET  /api/mission/status             - Live mission status (phase, operators, findings)
GET  /api/mission/findings           - Findings from the active mission
POST /api/agents/local/detect        - Detect installed local agents (Claude Code / Codex / Hermes)
POST /api/agents/local/connect       - Connect local agents as a keyless LLM backend
POST /api/admiral/converse           - Conversational mission intake (Op Admiral)
POST /api/tools/execute              - Tool execution
GET  /api/health                     - Server health + capability check
```

---

## Configuration

### Environment Variables

```bash
# LLM Provider API Keys (at least one required for AI features)
OPENROUTER_API_KEY=sk-or-...     # Recommended - access to multiple models
ANTHROPIC_API_KEY=sk-ant-...     # Direct Claude access
OPENAI_API_KEY=sk-...            # GPT models

# Optional settings
T3MP3ST_OPSEC_LEVEL=covert       # silent, covert, loud
T3MP3ST_MAX_TOKENS=4096
T3MP3ST_TEMPERATURE=0.7
```

### Programmatic Configuration

```typescript
import { config } from 't3mp3st';

// Set API keys
config.setApiKey('openrouter', 'sk-or-...');

// Configure default model
config.setDefaultModel('openrouter', 'anthropic/claude-sonnet-4');

// Set OPSEC level
config.set('opsec', { level: 'covert', cleanupOnComplete: true });
```

---

## Project Structure

```
t3mp3st/
├── src/
│   ├── mcp-server.ts      # MCP server (security_recon tooling)
│   ├── server.ts          # HTTP API server
│   ├── cli.ts             # Command-line interface
│   ├── llm/               # LLM backbone (OpenRouter, Anthropic, OpenAI)
│   ├── config/            # Configuration management
│   └── types/             # TypeScript type definitions
├── docs/
│   └── index.html         # Web UI with Arsenal viewer
├── dist/                  # Compiled JavaScript output
└── package.json
```

---

## 🤝 Contributing

Contributions are welcome! Please ensure all security tools are designed for authorized testing only.

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests

Cutting a release? See [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — the deterministic gates + local smoke path that must be green first.

---

## 📜 License

MIT License - See LICENSE file for details

---

<div align="center">

**Don't trust the numbers. Run them.** &nbsp;·&nbsp; `npm run verify-claims`

*Fortes fortuna iuvat* — fortune favors the bold, and the reproducible.

⊰•-•✧ LOVE PLINY ✧•-•⊱ 🌩️

</div>
