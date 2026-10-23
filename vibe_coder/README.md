# 🏥 MediCore AI — 24/7 Autonomous Vibe Coding Engine

An autonomous pair-programming loop engine built to continuously analyze, prompt, upgrade, and test **MediCore AI** into a mission-critical hospital operating system.

---

## ⚡ Key Highlights

1. **Continuous 24-Hour Loop**: Runs non-stop for 24 hours (or configurable duration), advancing through clinical roadmap milestones.
2. **Persistent Single Chat Thread**: Keeps the conversation context continuous without restarting or losing previous progress.
3. **Dynamic Model Routing & Automatic Failover**:
   - Primary: **Claude Sonnet 3.7 / 3.5 / next-gen**
   - Secondary: **Gemini 3.8 Flash**
   - Tertiary: **Gemini 3.8 Medium**
   - Fallback: **OpenAI ChatGPT 4o / o3-mini**
4. **Intelligent Rate Limit & Quota Handling**:
   - Detects HTTP 429 / quota exhaustion.
   - Automatically pauses, applies exponential backoff, and shifts to the next available model.
   - Resumes automatically when quota is available.
5. **Dual Modes**:
   - **Headless API Mode** (Recommended for stability): Direct multi-model orchestration via REST APIs.
   - **ChatGPT Web Browser Mode**: Uses Playwright to interact directly with `chatgpt.com`, uploading the latest code zip, maintaining the active chat URL, and catching rate limit banners.
6. **Automated Testing & Snapshots**:
   - Extracts generated code, compiles Python syntax, runs unit test verification, and outputs timestamped packages into `./upgrades/medicore_latest.zip`.

---

## 🚀 Quickstart

### 1. Configure Credentials (API Mode)
Export any or all of your API keys:
```bash
export GEMINI_API_KEY="your-gemini-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
```

### 2. Launch the 24-Hour Vibe Coding Loop
```bash
# Foreground execution (24 hours loop):
./run_vibe_bot.sh

# Or in background daemon mode (continuous):
./run_vibe_bot.sh daemon
```

### 3. Check Live Status & Completed Milestones
```bash
./run_vibe_bot.sh status
```

### 4. ChatGPT Web UI Mode (Playwright)
To automate the web interface of ChatGPT directly:
```bash
./run_vibe_bot.sh browser
```

---

## 🏥 Hospital Upgrade Roadmap

The bot methodically executes the following clinical enterprise milestones:
1. **Emergency Triage & NEWS2 Deterioration Engine**: ESI (1-5) triage AI and vital sign deterioration alerts.
2. **Medication Safety & Drug-Drug / Allergy Checker**: Real-time cross-checks for contraindications and interactions.
3. **Ambient Clinical SOAP Scribe**: Speech/transcript-to-SOAP note generator with ICD-10 diagnostic coding suggestions.
4. **HL7 FHIR R4 Interoperability**: Bidirectional FHIR exchange (Patient, Encounter, Observation, DiagnosticReport).
5. **Tamper-Evident SHA-256 Audit Vault**: Immutable hash-chained audit trails and break-glass emergency protocols.
6. **ICU Telemetry & Predictive Bed Allocation**: Real-time ward telemetry and capacity optimization.
