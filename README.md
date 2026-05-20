# SAMSAMCO JARVIS AI — Main Brain Node (CT108 / AI-24-7-Main)

> The central intelligence hub of the SAMSAMCO AIMediaOS ecosystem. A 300 GB Proxmox LXC container running 24/7 with 26 Docker containers, 90+ live network services, 11 parallel AI agent scripts, 20 MITOS site overlay instances, full Wyoming voice stack, MQTT cluster coordinator, and a custom LLM pipeline framework powering 15+ AI workflows across the entire production network.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Infrastructure Specifications](#infrastructure-specifications)
3. [JARVIS Hub — Core AI Orchestration](#jarvis-hub--core-ai-orchestration)
4. [JARVIS Pipeline Engine](#jarvis-pipeline-engine)
5. [Docker Container Stack](#docker-container-stack)
6. [Custom Systemd Services](#custom-systemd-services)
7. [MITOS Overlay System](#mitos-overlay-system)
8. [Voice Architecture — Wyoming Stack](#voice-architecture--wyoming-stack)
9. [MQTT Cluster Coordination](#mqtt-cluster-coordination)
10. [Master OS v7.5 — Unified Backend](#master-os-v75--unified-backend)
11. [Batch Queue — AI Content Generation](#batch-queue--ai-content-generation)
12. [App Portal & MCP API Manager](#app-portal--mcp-api-manager)
13. [AI Toolchain Deep Dive](#ai-toolchain-deep-dive)
14. [NocoDB Integration — Staff & Jobs Registry](#nocodb-integration--staff--jobs-registry)
15. [Storage & Data Layout](#storage--data-layout)
16. [Network Services — Full Port Reference](#network-services--full-port-reference)
17. [Scheduled Tasks & Automation](#scheduled-tasks--automation)
18. [Nginx Reverse Proxy Configuration](#nginx-reverse-proxy-configuration)
19. [Startup & Recovery](#startup--recovery)
20. [Monitoring & Observability](#monitoring--observability)
21. [Security Model](#security-model)
22. [Disaster Recovery](#disaster-recovery)
23. [Related Repositories](#related-repositories)

---

## Architecture Overview

CT108 (AI-24-7-Main) is the command brain of the SAMSAMCO AIMediaOS stack. Every other node in the network — from the VRM renderer to the TikTok scraper to the live stream broadcaster — ultimately receives instructions from, reports back to, or relies on services hosted inside this container.

The container's philosophy is **centralised intelligence, distributed execution**. CT108 itself rarely performs heavy GPU computation; instead it:

- **Routes LLM calls** through a multi-key Gemini pool to 15 site groups across the WAN
- **Coordinates MQTT worker nodes** (192.168.0.4–192.168.0.13) that handle CPU-heavy batch tasks
- **Manages the voice network** for 10 Wyoming endpoints across 3 people-servers and 7 room-specific voice servers
- **Runs 11 parallel JARVIS agent scripts** (ports 5001–5011) that handle autonomous AI tasks 24 hours a day
- **Persists all memory** via Neo4j graph DB + MeiliSearch + ChromaDB + PostgreSQL + Redis
- **Triggers n8n workflows** that publish content, monitor streams, and sync data across all repos

This is the node that never sleeps. It was rebuilt from **samsamcos/CasaOS-AI** (CT109) and extended dramatically — growing from a simple Docker management layer into a full AI operating system with custom scheduling, LLM proxy load balancing, a per-room voice architecture, and an agentic pipeline capable of autonomous multi-step task execution.

---

## Infrastructure Specifications

| Property | Value |
|---|---|
| **Container ID** | CT108 |
| **Hostname** | AI-24-7-Main |
| **Proxmox Host** | 192.168.0.10 (promxx) |
| **Container IP** | 192.168.0.33 |
| **Storage Volume** | `/dev/TBSD/vm-108-disk-0` (LVM thin) |
| **Total Disk** | 300 GB allocated |
| **Used Disk** | 126 GB (45%) |
| **Available** | 154 GB |
| **CPU Allocation** | 4 vCPU |
| **RAM Allocation** | ~10 GB |
| **OS** | Ubuntu (Proxmox LXC) |
| **Container Type** | Privileged LXC (Docker inside LXC) |
| **Docker** | Containerd runtime |
| **Uptime target** | 24/7 (auto-restart at boot via `@reboot` cron) |
| **Startup script** | `/DATA/Documents/all screens/start_jarvis.sh` |

The container is privileged to allow nested Docker + overlay networking. The 300 GB thin-provisioned LVM volume is on the `TBSD` volume group of the Proxmox host, shared with other high-storage VMs but thin-allocated so unused blocks are not pre-occupied.

---

## JARVIS Hub — Core AI Orchestration

**Path:** `/root/jarvis-hub/`  
**Port:** `8080`  
**Database:** `/root/jarvis-hub/hub.db` (SQLite, WAL mode)  
**Frontend:** `/root/jarvis-hub/public/js/jarvis-ui.js` (~12,900 lines)

The JARVIS Hub is the central control panel for the entire AI operation. It is a Node.js/Express server with a large single-page frontend covering every aspect of the SAMSAMCO AI stack.

### Gemini Key Pool Manager

The hub maintains a round-robin LLM key routing system across multiple API keys and 15 site groups:

**Simple Pool** — 4 key slots (A/B/C/D) with round-robin via LRU ordering (`ORDER BY last_used_at ASC`). A 60-second cooldown applies to each key after use. External services call a single master endpoint using a `sk-jarvis-xxxx` bearer token; the hub selects the next available real Gemini key internally without exposing it to callers.

**Master Keys Table** — The `gemini_master_keys` SQLite table stores keys tied to site groups. Site groups control which Gemini key slots a group of nodes can access:

| Site Group | Nodes | Column |
|---|---|---|
| Num 1–5 | 1–15 (3 nodes per group) | A (shared pool) |
| Num 6–10 | 1–15 | B (shared pool) |
| Num 11–15 | 1–15 | C (site-only, purple badge) |
| 0 | All | Global fallback |

**15-Node Grid** — The hub manages 15 named nodes across the 192.168.0.230–192.168.0.244 range:

| IP | Name | Site Group |
|---|---|---|
| 192.168.0.230 | Jarvis | 1 |
| 192.168.0.231 | SAM Main | 1 |
| 192.168.0.232 | PTNR | 1 |
| 192.168.0.233 | HOUSE | 2 |
| 192.168.0.234 | AI | 2 |
| 192.168.0.235 | Personal | 2 |
| 192.168.0.236 | Personal 2 | 3 |
| 192.168.0.237 | Sole Trader | 3 |
| 192.168.0.238 | Sole Trader 2 | 3 |
| 192.168.0.239 | LTD | 4 |
| 192.168.0.240 | LTD 2 | 4 |
| 192.168.0.241 | PIA | 4 |
| 192.168.0.242 | Spare | 5 |
| 192.168.0.243 | House | 5 |
| 192.168.0.244 | House 2 | 5 |

**WAN Lock** — Each key can be locked to route calls through its node's own WAN IP via a relay at `http://{node_ip}:3080/api/gemini-relay`. This allows separating LLM traffic across different ISP connections.

**Key Routing Logic (`gemini-pool.js`):**
```
getNextKeyForSite(siteGroup)
  → picks LRU key from 3 nodes in that Num group
  → falls back to global pool if all 3 keys are in 60s cooldown
  → if slave_site set → relay via POST /api/gemini-relay on that node
  → if proxy_url set → route via HTTP proxy (WireGuard tunnel)
```

### Hub Tabs

- **Settings** — LiteLLM proxy URL/key, Telegram bot token, ElevenLabs API key (pushed to `/DATA/AppData/assistant-manager/data/config.json`)
- **Gemini Keys** — Full key grid, master keys, cooldown status, test buttons, sync-from-nodes
- **Finder** — Fleet search via SSH status checks, Gemini key assignment per PC
- **TTS Manager** — Wyoming TTS model selection per room, wake word assignments
- **Wake Word** — OpenWakeWord model management across the 10-machine voice network

---

## JARVIS Pipeline Engine

**Config:** `/root/jarvis-hub/pipeline-config.yaml`  
**Examples:** `/root/jarvis-hub/pipeline-examples.md`

The pipeline engine processes voice and text queries through a series of AI stages running across 5 parallel lanes (Lane A through Lane E). Each lane is independent and can process a separate conversation simultaneously.

### Pipeline Stages

| Stage | Name | Input | Processing |
|---|---|---|---|
| ROW_0 | Intent Filter | Voice In | AWK×3 + Gemini name scan |
| ROW_1 | Group Finder | n8n Webhook In | LLM group classification |
| ROW_2+ | Task Execution | Pipeline state | Per-stage LLM + tool calls |

The pipeline's `centralized_master_api` mode means all 5 lanes submit their API calls through the hub's own Gemini pool, preventing any single lane from monopolising key quota. Pipeline state is persisted to SQLite so lanes survive restarts.

### JARVIS Agent Scripts (ports 5001–5011)

11 Python scripts run as systemd template services (`jarvis@5001.py.service` through `jarvis@5011.py.service`). Each is an autonomous AI worker that:

- Listens on its assigned port for task assignments
- Maintains its own conversation context and tool call history
- Reports results back to the hub via internal API
- Handles specific domains: content generation, data enrichment, web research, media processing, scheduling

**JARVIS MemPalace Ingest** (port 5000) is managed by `jarvis-ingest.service`, running `/root/ai-browser/ingest.py`. This process reads NocoDB data (staff, jobs tables) and indexes it into the vector stores (ChromaDB + MeiliSearch) nightly, keeping all 11 agents' semantic memory current.

**JARVIS Agent** service (`jarvis-agent.service`) is described as a "clone of 192.168.0.8" — a worker-node clone that runs locally inside CT108, allowing the hub to assign itself tasks in the same way it delegates to external MQTT workers.

---

## Docker Container Stack

26 Docker containers run inside CT108, divided into functional layers:

### AI / LLM Layer

| Container | Image | Port | Purpose |
|---|---|---|---|
| `openwebui` | `ghcr.io/open-webui/open-webui:main` | 3000 | UI for all LLM models, healthy |
| `litellm` | `ghcr.io/berriai/litellm:main-latest` | 4000 | LLM proxy — Gemini, Ollama, Groq |
| `litellm-db` | `postgres:15` | — | LiteLLM's dedicated PostgreSQL |
| `flowise` | `flowiseai/flowise:latest` | 3001 | Visual AI flow builder (LangChain) |
| `chromadb` | `chromadb/chroma:latest` | 8090 | Vector DB for semantic memory |
| `searxng` | `searxng/searxng:latest` | 8080 | Self-hosted meta search engine |
| `tesseract-webui` | `ghcr.io/santhoshtr/tesseract-ocr-web:latest` | — | OCR REST API |

### Voice Stack (Wyoming Protocol)

| Container | Image | Port | Purpose |
|---|---|---|---|
| `wyoming-piper` | `rhasspy/wyoming-piper` | 10200 | Text-to-speech (TTS) |
| `wyoming-whisper` | `rhasspy/wyoming-whisper` | 10300 | Speech-to-text (STT) |
| `wyoming-openwakeword` | `rhasspy/wyoming-openwakeword` | 10400 | Wake word detection |
| `wyoming-tts-router` | `python:3.11-slim` | 10450 | Routes TTS requests per room/model |
| `assistant-manager` | `python:3.11-slim` | 80 (internal) | AI assistant orchestrator |

### Data & Storage Layer

| Container | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | `postgres:15-alpine` | 5432 | Main production PostgreSQL |
| `neo4j` | `neo4j:5.20` | 7474 / 7687 | Graph database for knowledge graph |
| `redis` | `redis:alpine` | 6379 | Cache + session store |
| `meilisearch` | `getmeili/meilisearch:latest` | 7700 | Full-text search engine |
| `n8n` | `n8nio/n8n:latest` | 5678 | Workflow automation (healthy) |
| `langfuse` | `ghcr.io/langfuse/langfuse:2` | 3090 | LLM call tracing + observability |

### Monitoring & Management Layer

| Container | Image | Port | Purpose |
|---|---|---|---|
| `uptime-kuma` | `louislam/uptime-kuma:latest` | 3001 | Service uptime monitoring (healthy) |
| `portainer` | `portainer/portainer-ce:latest` | 9443 | Docker container management UI |
| `grafana` | `grafana/grafana:latest` | 3000 | Metrics dashboards |
| `prometheus` | `prom/prometheus:latest` | 9090 | Metrics scraping + storage |
| `big-bear-dashdot-app-1` | `mauricenino/dashdot:latest` | 3100 | System load dashboard |

### Notifications Layer

| Container | Image | Port | Purpose |
|---|---|---|---|
| `gotify` | `gotify/server` | 8080 | Push notification server (healthy) |
| `ntfy` | `binwiederhier/ntfy` | 8200 | HTTP-based push notifications |
| `mcp-api-manager` | `mcp-api-manager-mcp-api-manager` | — | MCP protocol API bridge |

All containers are configured to restart automatically (`restart: unless-stopped`). CasaOS app management service (`casaos-app-management.service`) supervises them via the CasaOS gateway on port 9000.

---

## Custom Systemd Services

Beyond Docker, CT108 runs a suite of custom Python and Node.js services as systemd units:

### Core Intelligence Services

**`master-os.service`** — Master OS v7.5 at port 8383. A unified Node.js backend that absorbs ports 2000, 3080, and 8500 into a single Express server. Connects to NocoDB at `192.168.0.107:8080` to read the `ALL_STAFF` table (361 rows) and `all_jobs` table (5000 rows). Manages worker registries, group prompts, and masterclass content. Also handles TTS model assignment per room via `/etc/wyoming/active.tfile` and serves a WebSocket-based monitoring interface.

**`jarvis-ingest.service`** — Runs `/root/ai-browser/ingest.py` in a virtualenv. Reads NocoDB staff and jobs data, builds embeddings, and writes to ChromaDB + MeiliSearch. Depends on `jarvis-agent.service` being healthy.

**`jarvis-agent.service`** — Local JARVIS worker clone. Mirrors the architecture of external MQTT worker nodes (192.168.0.4–.13) so the hub can assign work to itself.

**`jarvis@{port}.py.service`** (×11) — Template service running 11 parallel Python agents on ports 5001–5011. Each agent maintains independent context and tooling; they communicate back to the hub API at `localhost:8080`.

### Content & Media Services

**`batch-queue.service`** — Node.js server on port 2300 ("Brain CSV Generator"). Uses Groq SDK to process batch content requests — generating scripts, descriptions, and metadata for AI content at scale. Reads Groq API key from `/root/.env`. Supports auto-trigger mode via `auto_trigger.json` state file, dash-safe filename sanitisation, and upsert of `.env` keys.

**`cctv.service`** — Runs `/root/cctv.py`. Monitors CCTV camera feeds and processes motion events, likely feeding alerts to the ntfy/Gotify push notification containers.

**`app-portal.service`** — Node.js app at port 3015. Manages Composio app integrations (API refresh via `POST /api/refresh-apps`). Updated daily at 07:00 by a cron task using Gemini CLI.

### Communication & Control Services

**`claude-dashboard.service`** — Node.js server on port 3050 ("IT Manager Remote" / "Claude Dashboard"). Provides a remote web terminal for Claude Code–based system management tasks.

**`claude-mcp-bridge.service`** — Claude CLI MCP Bridge exposing SSE stream on port 9000. Bridges Claude Code's MCP protocol to HTTP Server-Sent Events for browser-based consumption.

**`claude-webhook.service`** — Receives Claude Code webhook events. Integrates with automation workflows that trigger on AI task completion.

**`monitor-it.service`** — System monitoring dashboard via web interface.

**`mosquitto.service`** — Mosquitto MQTT broker on port 1883. Enabled at boot. Requires password authentication (`/etc/mosquitto/passwd`). This is the cluster message bus for all 10 MQTT worker nodes.

**`nginx.service`** — Nginx reverse proxy. Serves 6 virtual host configurations: `2fauth-ssl`, `audit_ports`, `jarvis-mini`, `monitor-it`, `samsamco`, `vm102-sites`.

**`ollama.service`** — Ollama local LLM runtime (port 11434, localhost only). Provides local model inference when Gemini API keys are in cooldown or for privacy-sensitive tasks.

**`nmbd.service`** — Samba NMB daemon. CT108 shares files to the LAN via SMB (ports 139, 445).

---

## MITOS Overlay System

**Service template:** `overlay@{port}.service`  
**Script path:** `/root/site_overlay/main.py`  
**Config:** `/root/site_overlay/config.yaml`  
**Static assets:** `/root/site_overlay/static/`

MITOS Overlays are Python web services that inject live AI-generated content into website overlays. Each instance listens on its own port and serves a different site persona or content stream. 20 instances run simultaneously:

| Port Range | Instances | Description |
|---|---|---|
| 9050–9052 | 3 | First overlay group (Group A) |
| 9060–9076 | 17 | Main overlay group (Group B) |

Each `overlay@{port}.service` unit launches `main.py` with the port number as a parameter. The `config.yaml` controls which Gemini model, system prompt, and content template each instance uses. Overlays receive live data from the MQTT cluster (job status, performance metrics, AI-generated text) and inject it into web pages in real time.

The systemd template pattern (`overlay@.service`) allows all 20 instances to be managed with a single service file: `systemctl start overlay@9060` spins up a new instance without any additional configuration.

---

## Voice Architecture — Wyoming Stack

CT108 hosts the core Wyoming services (Piper, Whisper, OpenWakeWord, TTS Router) in Docker, and orchestrates a 10-machine distributed voice network spanning every room in the SAMSAMCO environment.

### The 11-Machine Voice Network

The full voice architecture — documented in `/root/jarvis-hub/VOICE_ARCHITECTURE.md` — covers 3 categories of machines:

**People + Voice Servers (3 machines)**

| IP | Person | Role | Services |
|---|---|---|---|
| 192.168.0.38 | Sam | MASTER — controls all staff/TTS/WW state | assistant-manager :80, Wyoming TTS :10200, STT :10300, WW :10450, Piper |
| 192.168.0.39 | GF | Clone of 0.38 | Same stack |
| 192.168.0.40 | House | Clone of 0.38 | Same stack |

`192.168.0.38` is the master voice coordinator. All TTS models, wake word assignments, and staff configurations live here and are synced out to clones.

**Room-Specific Voice Servers (7 machines)**

Dedicated Wyoming-only nodes — no assistant-manager. Each handles one physical room with its own STT/TTS/WakeWord pipeline:

| IP | Room | Tablet Port | Wyoming Ports |
|---|---|---|---|
| 192.168.0.70 | Room 0 | 5000 | TTS :10200, STT :10300, WW :10450 |
| 192.168.0.71 | Room 1 | 5001 | TTS :10200, STT :10300, WW :10450 |
| 192.168.0.72 | Room 2 | 5002 | TTS :10200, STT :10300, WW :10450 |
| 192.168.0.73 | Room 3 | 5003 | TTS :10200, STT :10300, WW :10450 |
| 192.168.0.74–77 | Rooms 4–7 | 5004–5007 | Same Wyoming stack |

CT108 acts as the **routing brain** for this voice network. The `wyoming-tts-router` container (port 10450) receives TTS requests from any room node and routes them to the correct Piper voice model. The `assistant-manager` container handles the full response pipeline: wake word trigger → STT → LLM (via JARVIS hub) → TTS → play.

### TTS Model Management

The JARVIS Hub's TTS Manager tab controls which Piper voice model each room uses. Models are stored locally and synced to room servers on demand. The `active.tfile` at `/etc/wyoming/active.tfile` is read by Master OS to determine the current active voice per room.

---

## MQTT Cluster Coordination

**Broker:** `mosquitto.service` on port 1883  
**Auth:** Password-file based (`/etc/mosquitto/passwd`)  
**Config dir:** `/etc/mosquitto/conf.d/`

CT108's Mosquitto broker coordinates 10 MQTT worker nodes at 192.168.0.4–192.168.0.13. This cluster handles distributed processing tasks that would be too heavy for a single container:

- **Batch AI generation** — Large-scale content production (scripts, descriptions, thumbnails) distributed across workers
- **Health reporting** — Each worker publishes its CPU/RAM/load metrics every 30 seconds
- **Task dispatch** — The hub publishes job payloads; workers claim them and publish results
- **MITOS data feeds** — Workers publish live performance data consumed by overlay instances

The `jarvis-agent.service` inside CT108 also subscribes to the MQTT bus, allowing the main container to participate as a worker when external nodes are saturated.

---

## Master OS v7.5 — Unified Backend

**Path:** `/root/master-os/`  
**Port:** `8383`  
**Service:** `master-os.service`

Master OS v7.5 is the unified API backend that replaced three separate services (ports 2000, 3080, 8500). Key responsibilities:

### NocoDB Integration

Connects to NocoDB at `192.168.0.107:8080` with:
- **ALL_STAFF table** (`mwlzz4gu995kjlv`) — 361 rows, each representing a staff persona with name, role, personality, voice model, and Telegram ID
- **all_jobs table** (`m4zdnuveh3gy3xv`) — 5000 rows, the job execution history and queue

Column names were auto-generated by NocoDB's CSV importer (generic format) and remapped internally in `server.js`.

### Worker Registry & Group Prompts

`worker-registry.json` tracks which MQTT worker nodes are online, their last heartbeat, and current task assignment. `group-prompts.json` stores system prompts for each of the 15 site groups — controlling how each group's AI persona behaves. `masterclasses.json` holds structured learning content distributed to room nodes.

### Room Management

Reads `rooms.json` to map room IDs to Wyoming endpoints and active voice models. Changes to room TTS/wake-word configuration flow through this backend.

---

## Batch Queue — AI Content Generation

**Path:** `/root/batch-queue/`  
**Port:** `2300`  
**Service:** `batch-queue.service`

The Batch Queue is a Node.js server backed by Groq SDK for high-throughput content generation. It processes CSV-driven job queues to produce AI-written content at scale:

- **Brain CSV Generator** — Given a job CSV (character, topic, platform, style), generates complete video scripts, hooks, CTAs, and descriptions
- **Auto-trigger mode** — `auto_trigger.json` controls whether the queue runs automatically on new input or waits for manual dispatch
- **Groq key resolution** — Reads `GROQ_API_KEY` from body → environment → `/root/.env` in that priority order
- **Filename sanitisation** — `san()` function converts spaces to underscores, strips special characters for safe filesystem names
- **Template system** — `brain_template.txt` defines the content structure that Groq fills in per job row

---

## App Portal & MCP API Manager

### App Portal (port 3015)

**Path:** `/root/app-portal/`  
**Service:** `app-portal.service`

Provides a catalogue of Composio integrations available to the AI agents. Updated automatically at 07:00 daily via a cron job that calls Gemini CLI to trigger `POST /api/refresh-apps`. Composio provides 200+ pre-built API connectors (GitHub, Slack, Gmail, Notion, etc.) that JARVIS agents can invoke as tools.

### MCP API Manager

**Container:** `mcp-api-manager`  
**Service:** `claude-mcp-bridge.service` (port 9000)

The MCP (Model Context Protocol) API Manager bridges Claude Code's tool-calling protocol to the JARVIS agent network. The bridge exposes an SSE stream on port 9000 that Claude Code connects to as an MCP server, giving it access to:

- JARVIS hub tools (LLM key management, pipeline dispatch)
- NocoDB staff/jobs queries
- MQTT cluster job submission
- File system operations on shared volumes

---

## AI Toolchain Deep Dive

### OpenWebUI + LiteLLM Proxy

OpenWebUI (port 3000) provides a ChatGPT-style interface for all models available through LiteLLM. LiteLLM acts as a universal proxy, presenting a single OpenAI-compatible endpoint at port 4000 while routing to:
- Gemini (via the JARVIS key pool)
- Ollama (local, port 11434)
- Groq (via API key)
- Any other model added to `litellm_config.yaml`

### FloWise — Visual AI Pipelines

FloWise (port 3001) provides a drag-and-drop interface for building LangChain-based AI pipelines. Used for prototyping new agent workflows before they are hardened into JARVIS scripts. Connects to ChromaDB for RAG (retrieval-augmented generation) and to the main PostgreSQL for persistent flow data.

### Neo4j — Knowledge Graph

Neo4j 5.20 (HTTP port 7474, Bolt port 7687) stores the SAMSAMCO knowledge graph:
- People, roles, and relationships between staff personas
- Content topics and their connections to site groups
- Task dependencies between pipeline stages
- Historical job execution graph

### SearXNG — Privacy-First Search

SearXNG (running internally) provides the JARVIS agents with a self-hosted meta-search engine. Agents use it for web research without exposing queries to commercial search providers. Results are aggregated from Google, Bing, DuckDuckGo, and niche sources.

### Tesseract OCR

The Tesseract WebUI container provides an HTTP API for document and image OCR. Used by agents that process business documents, screenshots, or physical mail images before feeding the text into LLM workflows.

### LangFuse — LLM Observability

LangFuse (port 3090) traces every LLM call made through the system — recording prompt, response, token count, latency, and model. Grafana dashboards pull from LangFuse's API to visualise AI usage patterns and catch regressions when prompts are changed.

---

## NocoDB Integration — Staff & Jobs Registry

**Host:** `192.168.0.107:8080`  
**Base:** `p5tk8xrpifcbp6r`  
**Tables:**
- `ALL_STAFF` (ID: `mwlzz4gu995kjlv`) — 361 rows
- `all_jobs` (ID: `m4zdnuveh3gy3xv`) — 5000 rows

NocoDB serves as the source-of-truth registry for all AI staff personas and the jobs they are assigned. Each staff row includes:
- Name, role, personality description
- Voice model preference (maps to Piper model name)
- Telegram chat ID for notifications
- Site group assignment
- Active status flag

The `all_jobs` table tracks every task sent to the JARVIS pipeline, with columns for: job ID, staff ID, task type, input, output, token count, duration, and status. This provides a complete audit trail of all AI work done across the network.

The MemPalace ingest (`jarvis-ingest.service`) runs at 06:05 every morning to sync NocoDB → ChromaDB + MeiliSearch, ensuring agents have semantically searchable memory of all staff and job history.

---

## Storage & Data Layout

CT108's 295 GB root volume (on `/dev/mapper/TBSD-vm--108--disk--0`) is organised as follows:

```
/root/
  jarvis-hub/         JARVIS Hub Node.js server + SQLite DB
  ai-browser/         Python AI browser agents + ingest scripts
  batch-queue/        Batch content generation server
  master-os/          Master OS v7.5 unified backend
  site_overlay/       MITOS overlay Python service + config
  app-portal/         Composio app integration portal
  cctv.py             CCTV monitoring script
  voice-factory/      Docker Compose for voice stack extras
  .env                API keys (never committed)

/DATA/
  AppData/            Docker container persistent volumes
    n8n/              n8n workflow data
    assistant-manager/ Voice assistant config + TTS models
    openclaw/         OpenClaw WebSocket gateway config
    chefbot-studio/   Chef bot Docker stack
  Documents/          Operational documents + scripts
    Master/           JARVIS master scripts (gemini_key.py, pcs.csv, Sites/)
    "all screens"/    Startup scripts + JARVIS zip archive
    Audit-site/       System audit results
    Jobs/             Job queue archives
    Jobs-Master/      Master job definitions
    samsamco_command/ Shell command library
  Backups/            Backup snapshots of CasaOS config + AppData
  Downloads/          Temporary downloads + JARVIS builder scripts

/etc/
  nginx/sites-enabled/  6 nginx virtual host configs
  mosquitto/            MQTT broker config + password file
  wyoming/              Wyoming TTS active model config
  systemd/system/       All custom service unit files

/opt/
  audits/scripts/     System audit scripts (update_system_overview.sh, junk_manager.sh)
  duckdns/            DuckDNS dynamic DNS update script
```

Docker container data lives in `/var/lib/docker` with overlayfs mounts, and all persistent volumes are bind-mounted from `/DATA/AppData/{container-name}/`.

---

## Network Services — Full Port Reference

CT108 exposes the following ports on `192.168.0.33`:

| Port | Protocol | Service | Notes |
|---|---|---|---|
| 22 | TCP | SSH | Root access, key + password auth |
| 25 | TCP | SMTP | localhost only (mail relay) |
| 80 | TCP | nginx / shell-command-center | Main HTTP, reverse proxy |
| 85 | TCP | nginx alt | Secondary HTTP virtual host |
| 100 | TCP | Service | Internal |
| 139 | TCP | Samba | SMB file sharing (NetBIOS) |
| 204 | TCP | Service | Internal |
| 300 | TCP | Service | Internal |
| 350 | TCP | Service | Internal |
| 445 | TCP | Samba | SMB file sharing (TCP) |
| 1000 | TCP | Service | Internal |
| 1883 | TCP | Mosquitto MQTT | Cluster message bus |
| 2000 | TCP | Legacy port | Now absorbed by Master OS |
| 2050 | TCP | TTS Manager / Wake Word | Wyoming coordinator |
| 2300 | TCP | Batch Queue | Brain CSV Generator |
| 2580 | TCP | Service | Internal |
| 2586 | TCP | Service | Internal |
| 2587 | TCP | Service | Internal |
| 3000 | TCP | OpenWebUI / Grafana | LLM chat + dashboards |
| 3001 | TCP | FloWise / Uptime Kuma | AI flows + uptime monitor |
| 3015 | TCP | App Portal | Composio integration hub |
| 3050 | TCP | Claude Dashboard | IT Manager Remote |
| 3060 | TCP | Service | Internal |
| 3080 | TCP | LibreChat / JARVIS Hub | LLM chat + orchestration |
| 3090 | TCP | LangFuse | LLM observability |
| 3099 | TCP | Service | Internal |
| 3100 | TCP | DashDot | System load dashboard |
| 3210 | TCP | Service | Internal |
| 3333 | TCP | Service | Internal |
| 3400 | TCP | Service | Internal |
| 3500 | TCP | Service | Internal |
| 4000 | TCP | LiteLLM Proxy | OpenAI-compatible LLM endpoint |
| 4040 | TCP | Service | Internal |
| 4050 | TCP | Service | Internal |
| 4200 | TCP | Service | Internal |
| 5000 | TCP | JARVIS MemPalace Ingest | Vector memory indexer |
| 5001–5011 | TCP | JARVIS Agents ×11 | Autonomous AI worker scripts |
| 5050 | TCP | Service | Internal |
| 5051 | TCP | Service | Internal |
| 5432 | TCP | PostgreSQL | Main production database |
| 5678 | TCP | n8n | Workflow automation |
| 6379 | TCP | Redis | Cache + pub/sub |
| 7474 | TCP | Neo4j HTTP | Graph database browser |
| 7681 | TCP | Service | Internal |
| 7687 | TCP | Neo4j Bolt | Graph database protocol |
| 7700 | TCP | MeiliSearch | Full-text search |
| 8080 | TCP | JARVIS Hub / CasaOS | AI control panel |
| 8081 | TCP | Service | Internal |
| 8090 | TCP | ChromaDB | Vector database |
| 8200 | TCP | ntfy | Push notification HTTP |
| 8291 | TCP | Service | Internal |
| 8383 | TCP | Master OS v7.5 | Unified SAMSAMCO backend |
| 8888 | TCP | Jupyter / Service | Internal |
| 9000 | TCP | Claude MCP Bridge | SSE-based MCP server |
| 9005 | TCP | Service | Internal |
| 9050–9076 | TCP | MITOS Overlays ×20 | AI site overlay instances |
| 9090 | TCP | Prometheus | Metrics scraping |
| 9443 | TCP | Portainer | Docker management HTTPS |
| 10200 | TCP | Wyoming Piper | TTS — voice synthesis |
| 10300 | TCP | Wyoming Whisper | STT — speech recognition |
| 10400 | TCP | Wyoming OpenWakeWord | Wake word detection |
| 10450 | TCP | Wyoming TTS Router | Per-room TTS routing |
| 11434 | TCP | Ollama | Local LLM (localhost only) |

Total public ports: **90+**

---

## Scheduled Tasks & Automation

CT108's crontab runs the following automated tasks:

| Schedule | Task |
|---|---|
| `@reboot` | Launch full JARVIS stack via `start_jarvis.sh` |
| `*/5 * * * *` | DuckDNS dynamic DNS update |
| `0 3 * * *` | RAG index rebuild (`run_rag.sh`) |
| `0 6 * * *` | Nightly health check (`health_check_night.py`) |
| `5 6 * * *` | NocoDB → MemPalace sync (`noco_mempalace_sync.py`) |
| `0 7 * * *` | Morning briefing dispatch to JARVIS Hub |
| `0 7 * * *` | Composio app list refresh (Gemini CLI) |
| `0 7 * * *` | System overview update (`update_system_overview.sh`) |
| `0 8 * * *` | Junk manager cleanup (`junk_manager.sh`) |
| `0 11 * * 6` | Saturday full health scan (`health_check.py`) |
| `30 11 * * 2` | JARVIS update scan (POST to hub API) |
| `0 2 * * 0` | Weekly site backup (`backup_sites.sh`) |
| `0 2 * * 3` | Mid-week CLI site backup |

The `@reboot` entry is the most critical — `start_jarvis.sh` starts all 26 Docker containers, all 11 JARVIS agent scripts, and all 20 MITOS overlay instances in the correct dependency order.

---

## Nginx Reverse Proxy Configuration

CT108's nginx serves 6 virtual host configurations from `/etc/nginx/sites-enabled/`:

- **`2fauth-ssl`** — Two-factor authentication service with HTTPS
- **`audit_ports`** — Internal port audit dashboard (maps service names to ports)
- **`jarvis-mini`** — Lightweight JARVIS control panel (mobile-friendly)
- **`monitor-it`** — Monitor-It system dashboard proxy
- **`samsamco`** — Main SAMSAMCO landing page and portal
- **`vm102-sites`** — Reverse proxy to sites hosted on VM102

All HTTPS virtual hosts terminate SSL at nginx, with certificates managed by the `2fauth-ssl` configuration (likely Let's Encrypt via DuckDNS).

---

## Startup & Recovery

### Normal Boot Sequence

On reboot, the following startup order is enforced:

1. **systemd services start** — Mosquitto, Nginx, Samba, Ollama, CasaOS
2. **Docker daemon starts** — All 26 containers restart automatically
3. **`@reboot` cron fires** — `start_jarvis.sh` launches remaining services:
   - JARVIS Hub (via Node.js)
   - All 11 JARVIS agent scripts (systemd via `jarvis@{port}.service`)
   - All 20 MITOS overlay instances (systemd via `overlay@{port}.service`)
   - Master OS v7.5 (`master-os.service`)
   - Batch Queue (`batch-queue.service`)
   - Claude Dashboard (`claude-dashboard.service`)
   - Claude MCP Bridge (`claude-mcp-bridge.service`)

### Offline Recovery via LVM Mount

If CT108 fails to boot and SSH is unavailable, the filesystem can be read from the Proxmox host directly:

```bash
# On Proxmox host (192.168.0.10)
mount /dev/TBSD/vm-108-disk-0 /tmp/ct108_scan
ls /tmp/ct108_scan/root/
umount /tmp/ct108_scan
```

This allows reading config files, recovering keys from `.env`, and diagnosing startup failures without starting the container.

### Service Recovery Commands

```bash
# Check all JARVIS agents
systemctl status 'jarvis@*.service'

# Restart all overlay instances
systemctl restart 'overlay@*.service'

# Check Docker container health
docker ps --format '{{.Names}}: {{.Status}}'

# Restart failed containers
docker compose -f /root/voice-factory/docker-compose.yml restart

# Rebuild MQTT worker connections
systemctl restart mosquitto
systemctl restart jarvis-agent

# Force NocoDB sync
/root/ai-browser/.venv/bin/python3 /root/ai-browser/noco_mempalace_sync.py
```

---

## Monitoring & Observability

CT108 has a multi-layer monitoring stack:

### Internal Monitoring

- **Uptime Kuma** — Monitors all 90+ internal services with HTTP/TCP checks, sends alerts via Gotify and ntfy when any service goes offline
- **Prometheus + Grafana** — Scrapes system metrics from all Docker containers and systemd services; dashboards show CPU, RAM, network, LLM token usage, MQTT message throughput
- **LangFuse** — Traces every LLM API call through LiteLLM, recording model, tokens, latency, and cost
- **DashDot** — Real-time system load display for quick hardware overview

### External Monitoring

- **n8n workflows** in CT109 (CasaOS, 192.168.0.173) poll CT108's Uptime Kuma API to detect cross-container failures
- **Telegram notifications** — Master OS sends morning briefings and critical alerts via Telegram bot
- **Gotify + ntfy** — Push notifications to mobile devices for immediate incident response

### Health Check Scripts

- `health_check_night.py` — Nightly lightweight check: verifies all 11 JARVIS agents respond, all Docker containers are healthy, and MQTT broker accepts connections
- `health_check.py` — Saturday comprehensive scan: full service audit, LLM key rotation check, NocoDB data integrity, disk usage alert if > 80%

---

## Security Model

CT108 handles sensitive data including API keys, staff persona data, and LLM credentials. Security is enforced at multiple layers:

### Credential Management

- All API keys stored in `/root/.env` — never committed to git
- `.env.example` in the repo contains dummy placeholders only
- JARVIS Hub's Gemini key pool means external services never see real API keys
- LiteLLM proxy adds another abstraction layer — callers use `sk-jarvis-xxxx` master keys

### Network Security

- Mosquitto MQTT requires password authentication (no anonymous connections)
- Portainer exposed only on HTTPS (port 9443)
- Ollama bound to `127.0.0.1` only — not accessible from outside the container
- Nginx terminates TLS for all public-facing services

### Access Control

- SSH access requires root credentials
- CasaOS gateway manages Docker API access
- Portainer CE enforces container-level access control

### Secrets Never to Expose

- `/root/.env` — contains Gemini, Groq, ElevenLabs, NocoDB, PostgreSQL, Neo4j, Telegram credentials
- `/root/jarvis-hub/hub.db` — contains LLM key data (though keys are stored encrypted)
- `/etc/mosquitto/passwd` — MQTT broker password file
- Any `.env` file under `/DATA/AppData/*/` — Docker container environment files

---

## Disaster Recovery

### Backup Strategy

- **Sunday 02:00** — Full site backup via `backup_sites.sh`
- **Wednesday 02:00** — CLI site backup (`cli-site-backup.sh`)
- `/DATA/Backups/casaos/` — Snapshot of CasaOS AppData, including Docker configs

### Full Rebuild from Scratch

If the entire container is destroyed:

1. **Create new LXC** on Proxmox with 300 GB thin-provisioned storage, 4 vCPU, 10 GB RAM
2. **Clone from CasaOS-AI** (samsamcos/CasaOS-AI) for the base Docker stack
3. **Restore `/DATA/AppData`** from backup snapshot
4. **Restore `/root`** directories from backup
5. **Restore `.env`** from secure password manager
6. **Run start_jarvis.sh** to bring up all services
7. **Verify MQTT cluster** reconnects (workers at 192.168.0.4–.13 auto-reconnect on broker restart)
8. **Trigger manual NocoDB sync** to rebuild vector memory

Total estimated recovery time from backup: 45–90 minutes depending on Docker image pull speeds.

---

## AI Browser Agent Framework

**Path:** `/root/ai-browser/`  
**Runtime:** Python 3.11 virtualenv at `/root/ai-browser/.venv`

The `ai-browser` directory contains the core Python intelligence layer that powers JARVIS's autonomous capabilities. Unlike the Docker containers (which handle infrastructure services) and the Node.js hub (which handles orchestration), the AI browser framework provides the actual intelligent agent behaviour:

### Key Scripts

**`ingest.py`** — The nightly MemPalace ingest process. Reads all staff and job records from NocoDB, generates embeddings using a local embedding model, and writes them to both ChromaDB (for semantic similarity search) and MeiliSearch (for keyword + faceted search). Run by `jarvis-ingest.service` and by the `5 6 * * *` cron job.

**`noco_mempalace_sync.py`** — Lightweight sync script that detects incremental changes in NocoDB since the last run. Only re-embeds records that were created or modified, making the daily 06:05 cron fast even with 5000+ job records.

**`health_check_night.py`** — Nightly quick health check. Pings all 11 JARVIS agent HTTP endpoints, verifies Docker container health status, checks MQTT broker connectivity, and sends a summary to Telegram.

**`health_check.py`** — Saturday full scan. Iterates all 90+ services, validates response codes, checks disk usage thresholds, rotates logs, and produces a health report stored to `/root/ai-browser/logs/weekly-health.log`.

**`jarvis_config_pusher.py`** — Pushes configuration updates (system prompts, voice models, site group assignments) from the hub out to all 15 node endpoints simultaneously using asyncio. Called when settings are saved in the JARVIS Hub UI.

**`jarvis_tools.py`** — Tool library for JARVIS agents. Provides callable functions for: web search via SearXNG, NocoDB CRUD, file system read/write, MQTT publish, n8n webhook trigger, and Composio app calls.

**`jarvis-cli.py`** — Command-line JARVIS interface. Accepts natural language commands and routes them through the hub pipeline, printing responses to terminal. Used for quick one-off tasks without opening the web UI.

**`run_rag.sh`** — Shell wrapper that rebuilds the full RAG (retrieval-augmented generation) index at 03:00 nightly. Clears stale ChromaDB collections and rebuilds from the current NocoDB state.

### Logs

All AI browser scripts write to `/root/ai-browser/logs/` with structured JSON log entries. Log rotation is managed by `junk_manager.sh` which runs at 08:00 each morning.

---

## Related Repositories

This repository is part of the SAMSAMCO AIMediaOS ecosystem. All production nodes are managed via the AI-Creator fleet dashboard:

| Repository | Node | Role |
|---|---|---|
| [samsamcos/CasaOS-AI](https://github.com/samsamcos/CasaOS-AI) | CT109 (192.168.0.173) | Docker automation hub, n8n, NocoDB, Grafana |
| [samsamcos/AI-Creator](https://github.com/samsamcos/AI-Creator) | CT107 (192.168.0.173:7083) | Fleet provisioning + management dashboard |
| [samsamcos/vtube-ai-brain-1](https://github.com/samsamcos/vtube-ai-brain-1) | VM301 | Groq LLM brain, WebSocket AI responses |
| [samsamcos/vrm-live-stream](https://github.com/samsamcos/vrm-live-stream) | CT401 | FFmpeg NVENC 8-stream broadcaster |
| [samsamcos/app](https://github.com/samsamcos/app) | CT501 | VRM 3D renderer, React + Three.js |
| [samsamcos/brower-remote](https://github.com/samsamcos/brower-remote) | VM701 | TikTok chat scraper, Camoufox |

---

*Built by SAMSAMCO. The AI that runs 24/7 so you don't have to.*
