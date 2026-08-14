<div align="center">

<img src="https://raw.githubusercontent.com/nabrahma/nabrahma/main/assets/header.svg" width="100%" alt="nabaskar brahma — backend, distributed systems, infrastructure security" />

<br/>

[![Portfolio](https://img.shields.io/badge/portfolio-0d1117?style=flat-square&logo=vercel&logoColor=white&labelColor=0d1117)](https://nabaskarbrahma.vercel.app/)
[![LinkedIn](https://img.shields.io/badge/linkedin-0d1117?style=flat-square&logo=linkedin&logoColor=white&labelColor=0d1117)](https://www.linkedin.com/in/nabaskar/)
[![Email](https://img.shields.io/badge/email-0d1117?style=flat-square&logo=maildotru&logoColor=white&labelColor=0d1117)](mailto:nabaskarforcode99@gmail.com)
[![itch.io](https://img.shields.io/badge/itch.io-0d1117?style=flat-square&logo=itchdotio&logoColor=white&labelColor=0d1117)](https://nabaskarbrahma.itch.io/)

</div>

<br/>

I work on the parts of a system that fail quietly — lock contention, event loops, isolation boundaries, and the measurements that are supposed to tell you when something is wrong.

Mostly **Go** and **Python**. Kubernetes operators, container sandboxing, and a live trading engine that places real orders. I test hard, and I publish my false-positive rates.

<br/>

## Open source

<div align="center">

<img src="https://raw.githubusercontent.com/nabrahma/nabrahma/main/assets/oss.svg" width="72%" alt="open source contribution stats" />

</div>

<br/>

The four upstream fixes I'd defend in an interview — each one a bug that was invisible until it wasn't.

<table>
<tr>
<td width="34%"><b><a href="https://github.com/volcano-sh/kthena/pull/1297">kthena #1297</a></b><br/><sub>lock convoy in the fairness queue</sub></td>
<td>The sliding-window token tracker dropped its <code>RLock</code> and took an <b>exclusive</b> lock on the <i>read</i> path, to lazily GC expired buckets. Under concurrency, every reader stampeded the same mutex the moment a bucket expired — periodic P99 spikes with no obvious cause. Moved GC to the write path and made reads advance a local <code>startIdx</code> past the cutoff, so reads never mutate the slice and never need the exclusive lock.</td>
</tr>
<tr>
<td><b><a href="https://github.com/volcano-sh/kthena/pull/1255">kthena #1255</a></b><br/><sub>O(N) blocking scrape → bounded parallel</sub></td>
<td>The background metrics scraper did one blocking HTTP GET per pod, sequentially. A handful of unresponsive pods stalled the entire loop and staled metrics for <i>every</i> pod in the cluster. Rewrote it with a <code>sync.WaitGroup</code> and a 100-slot semaphore channel, with context cancellation checked inside the <code>Range</code>.</td>
</tr>
<tr>
<td><b><a href="https://github.com/volcano-sh/kthena/pull/1530">kthena #1530</a></b><br/><sub>regex recompiled on every request</sub></td>
<td><code>matchString</code> called <code>regexp.MatchString</code>, recompiling the pattern on <b>every request</b> — once per header matcher, plus once for the URI. Memoised compiled patterns in a <code>sync.Map</code> keyed by pattern, bounded by CR count rather than traffic, caching compile failures too. <b>~50,000 ns/op → ~820 ns/op; 250 allocs/op → near zero.</b></td>
</tr>
<tr>
<td><b><a href="https://github.com/volcano-sh/kthena/pull/1243">kthena #1243</a></b><br/><sub>1,000+ goroutines from one request</sub></td>
<td>The LRU eviction callback spawned a goroutine per evicted hash — a single 8k-token request spawned over a thousand instantly. The <code>go</code> was a legacy deadlock workaround; it stopped being necessary once <code>podLRU.Add()</code> moved after <code>shard.mu.Unlock()</code>. Two-line fix, but only after verifying the lock ordering that made it safe.</td>
</tr>
</table>

<sub>Also merged: a repo-wide Go 1.26 upgrade in kthena, a <a href="https://github.com/kubernetes-sigs/headlamp/pull/6066">rules-of-hooks fix in kubernetes-sigs/headlamp</a> that removed four eslint suppressions hiding it, and <a href="https://github.com/openfoodfacts/openfoodfacts-explorer/pulls?q=is%3Apr+author%3Anabrahma+is%3Amerged">8 a11y and responsive fixes</a> in Open Food Facts. → <a href="https://github.com/pulls?q=is%3Apr+author%3Anabrahma+is%3Amerged">all merged PRs</a></sub>

<br/>

## Projects

<details>
<summary><b>ShortCircuit</b> — live algorithmic trading engine &nbsp;·&nbsp; <code>python · asyncio · postgres</code></summary>

<br/>

Places real orders on NSE equities through Fyers API v3. 14.8K LOC across 42 modules.

- One asyncio event loop supervising five concurrent tasks, with crash-loop cutoff and ordered shutdown
- Three-tier data pipeline behind a sliding-window limiter enforcing 10/sec, 200/min and 100K/day simultaneously, with a reserved priority lane so stop-loss never queues behind scanner traffic
- Found a WebSocket payload-nesting defect that had silently prevented *every* order fill from being confirmed — recovered 89 order IDs from logs that previously yielded zero
- 248 tests, 100% branch coverage on order decisions, plus an AST test that fails the build if a strategy module imports anything with I/O

</details>

<details>
<summary><b>Driftwatch</b> — distributed consistency auditor &nbsp;·&nbsp; <code>go · kubernetes · redis · zeromq</code></summary>

<br/>

Detects silent divergence between an event stream and its derived Redis store by rebuilding expected state as an independent third consumer.

- Cut an 8% false-positive rate at 2,000 events/sec using a settlement window derived from measured propagation lag, two-phase confirmation with version fencing, and trust states that classify self-inflicted loss as *suspect* rather than *drift*
- Kubernetes operator on controller-runtime: CRD, validating and defaulting webhooks, leader election, finalizers; Helm chart, Grafana dashboard, 10 alert rules over 48 metrics
- 1M Redis keys swept in 5.68s · 5.3M events with zero drops across a 60-minute soak · flat 13 goroutines
- 91.6% coverage across 10 test levels — property-based, fuzzing, a 60-row fault matrix, Kind-based e2e

</details>

<details>
<summary><b>MCP Zero-Trust Gateway</b> — kernel confinement for AI agent tools &nbsp;·&nbsp; <code>python · seccomp · docker</code> &nbsp;·&nbsp; <a href="https://pypi.org/project/mcp-ztgateway/">PyPI</a></summary>

<br/>

Treats a tool server's self-description as untrusted. Declare, verify, confine.

- Profiles each server under `strace` in a `--cap-drop ALL --read-only` container, maps observed syscalls to a capability vocabulary, and denies anything the declaration doesn't cover
- Compiles per-tool seccomp-BPF filters by subtraction from the verified verdict, enforced alongside network namespaces, bind mounts and a CONNECT allow-list proxy
- 84.6% detection at a measured 25–50% false-positive rate, 87.5% containment, 503/503 identical verdicts across five clean runs
- An earlier build reported 100%. It was two measurement bugs cancelling out. Rebuilding the methodology so that class of error can't hide again is the part I'd defend hardest.

</details>

<details>
<summary><b>GameCode</b> — sandboxed judge for game developers &nbsp;·&nbsp; <code>go · echo · postgres · nextjs</code></summary>

<br/>

Competitive-programming platform running C++, C#, Lua and GDScript in throwaway containers.

- No network, read-only rootfs, hard CPU / 256 MB / 128-PID caps; eight verdict states from exit codes, runtime and peak memory read from the cgroup
- 44 endpoints in a 9-package handler → service → repository layering; JWT with rotating SHA-256-hashed refresh tokens over httpOnly cookies
- A validator CLI runs 75 reference solutions against 136 test cases on every build — caught 6 latent defects including an int64 overflow

</details>

<br/>

## Stack

<div align="center">

![Go](https://img.shields.io/badge/Go-0d1117?style=flat-square&logo=go&logoColor=white&labelColor=0d1117)
![Python](https://img.shields.io/badge/Python-0d1117?style=flat-square&logo=python&logoColor=white&labelColor=0d1117)
![C++](https://img.shields.io/badge/C++-0d1117?style=flat-square&logo=cplusplus&logoColor=white&labelColor=0d1117)
![TypeScript](https://img.shields.io/badge/TypeScript-0d1117?style=flat-square&logo=typescript&logoColor=white&labelColor=0d1117)
![Bash](https://img.shields.io/badge/Bash-0d1117?style=flat-square&logo=gnubash&logoColor=white&labelColor=0d1117)

![Kubernetes](https://img.shields.io/badge/Kubernetes-0d1117?style=flat-square&logo=kubernetes&logoColor=white&labelColor=0d1117)
![Docker](https://img.shields.io/badge/Docker-0d1117?style=flat-square&logo=docker&logoColor=white&labelColor=0d1117)
![Linux](https://img.shields.io/badge/Linux-0d1117?style=flat-square&logo=linux&logoColor=white&labelColor=0d1117)
![Prometheus](https://img.shields.io/badge/Prometheus-0d1117?style=flat-square&logo=prometheus&logoColor=white&labelColor=0d1117)
![Grafana](https://img.shields.io/badge/Grafana-0d1117?style=flat-square&logo=grafana&logoColor=white&labelColor=0d1117)
![GitHub Actions](https://img.shields.io/badge/Actions-0d1117?style=flat-square&logo=githubactions&logoColor=white&labelColor=0d1117)

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-0d1117?style=flat-square&logo=postgresql&logoColor=white&labelColor=0d1117)
![Redis](https://img.shields.io/badge/Redis-0d1117?style=flat-square&logo=redis&logoColor=white&labelColor=0d1117)
![FastAPI](https://img.shields.io/badge/FastAPI-0d1117?style=flat-square&logo=fastapi&logoColor=white&labelColor=0d1117)
![React](https://img.shields.io/badge/React-0d1117?style=flat-square&logo=react&logoColor=white&labelColor=0d1117)
![Next.js](https://img.shields.io/badge/Next.js-0d1117?style=flat-square&logo=nextdotjs&logoColor=white&labelColor=0d1117)

<sub>started in game dev — <code>unity</code> · <code>c#</code> · <code>blender</code> — still where I go to play</sub>

</div>

<br/>

## Activity

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/nabrahma/nabrahma/output/snake.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/nabrahma/nabrahma/output/snake-light.svg" />
  <img src="https://raw.githubusercontent.com/nabrahma/nabrahma/output/snake.svg" width="100%" alt="contribution graph" />
</picture>

</div>

<br/>

<div align="center">
<sub>building the parts nobody sees until they break</sub>
</div>
