# AI Travel Planning Assistant

A context-aware travel assistant combining a modular document-based knowledge base (Retrieval-Augmented Generation) with dynamic Model Context Protocol (MCP) tool execution. The application synthesizes static travel guide knowledge with live weather forecasts and currency exchange rates to create weather-adaptive, budget-tailored itineraries.

While Singapore is implemented as the reference destination, the architecture is country-agnostic and modular to support multiple international destinations.

---

## System Architecture & Workflow

![alt text](workflow.png)

### Key Components

* **Dual-LLM Resilience**: Default low-latency routing and synthesis via **Groq** (`llama-3.1-8b-instant`), with automated failover targeting **OpenAI** (`gpt-4o-mini`).
* **Modular Multi-Country Knowledge Store**: Extensible document ingestion utilizing LangChain and ChromaDB. Each country operates under its own isolated vector namespace (`data/<destination>/`), allowing seamless dynamic loading of additional destinations (e.g., Japan, France, UAE).
* **Real-Time MCP Tools**:
* `get_weather`: Live multi-day weather forecasts, temperature metrics, and precipitation probabilities.
* `convert_currency`: Real-time foreign exchange conversions using ECB reference rates.


* **Context Synthesis Engine**: Combines static destination knowledge with real-time variables. Dynamically swaps outdoor excursions for indoor attractions whenever rainfall probability exceeds 40%.
* **Conversation Context Memory**: Multi-turn dialogue management preserving user preferences, constraints, and budget variables across follow-up queries.

---
## 📂 Project Assets

* **GitHub Repository:** [sidhant97/ai-travel-planner](https://github.com/sidhant97/ai-travel-planner.git)
* **Source Code (Backup):** [Google Drive Link]
* **Demo Recording:** [Google Drive Link]

---

## External APIs & MCP Tool Specifications

Both external tool APIs require **no API keys** and are free for open evaluation:

### 1. Weather Forecast Service: Open-Meteo

* **Provider**: Open-Meteo
* **Base Endpoint**: `[https://api.open-meteo.com/v1/forecast](https://api.open-meteo.com/v1/forecast)`
* **Authentication**: None required
* **Sample Request**:
```text
GET https://api.open-meteo.com/v1/forecast?latitude=1.3521&longitude=103.8198&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia/Singapore

```


* **Payload Output**: Max/min daily temperatures, precipitation probability metrics, and weather conditions used to evaluate indoor/outdoor routing.

### 2. Foreign Exchange Service: Frankfurter

* **Provider**: Frankfurter API
* **Base Endpoint**: `[https://api.frankfurter.app/latest](https://api.frankfurter.app/latest)`
* **Authentication**: None required (European Central Bank reference data)
* **Sample Request**:
```text
GET https://api.frankfurter.app/latest?amount=60000&from=INR&to=SGD

```


* **Payload Output**: Exact exchange rate, date reference, and converted sums used to anchor travelers' localized spending limits.

---

## Prompt Engineering Strategy

Prompts are designed to enforce strict grounding, contextual integrity, and source distinction:

* **Grounding & Zero-Hallucination**: The model is instructed to draw destination facts exclusively from retrieved chunks. If the vector store does not contain the required data, it explicitly reports that information is unavailable rather than fabricating facts.
* **Tool-RAG Boundary Enforcement**: Static domain knowledge (attractions, culture, neighborhoods) must come from RAG. Dynamic, time-sensitive metrics (weather, currency conversion) must strictly trigger MCP tools.
* **Provenance Attribution**: Outputs explicitly tag the origin of each data point, differentiating between static knowledge base citations, live MCP tool returns, and general AI reasoning.
* **Conditional Logic Execution**: Synthesizes weather metrics into actionable itinerary adjustments, automatically proposing indoor alternatives (museums, covered conservatories, shopping malls) when precipitation probability triggers adverse thresholds.

---

## Environment Configuration (.env)

Create a `.env` file in the project root containing these parameters:

```ini
# LLM Providers (Groq Primary + OpenAI Fallback)
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
OPENAI_API_KEY=sk-proj-your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

```

---

## Project Directory Structure

```text
ai-travel-planner/
├── data/
│   ├── singapore/                      # Default destination knowledge base
│   │   ├── visit_singapore_itineraries.md
│   │   ├── visit_singapore_practical.md
│   │   └── wikivoyage_singapore.md
│   └── japan/                          # Modular country extension example
│       └── tokyo_travel_guide.md
├── chroma_store/                       # Persistent local vector database
├── .env                                # Local secrets & endpoints
├── .gitignore                          # Git exclusions (.env, venv/, chroma_store/)
├── app.py                              # Streamlit UI with multi-turn chat and TXT export
├── guardrails.py                       # Input boundary and domain validation
├── mcp_client.py                       # Client interface for tool calling
├── mcp_server.py                       # Tool implementations for Weather & FX
├── orchestrator.py                     # Multi-provider agent brain, routing, and fallback
├── prompts.py                          # Prompt engineering & synthesis rules
├── rag_engine.py                       # LangChain document chunking and vector storage
├── requirements.txt                    # Project dependencies
├── test_suite.py                       # Automated verification tests
└── README.md                           # Project documentation

```

---

## Installation & Local Execution

**1. Clone the Repository**

```bash
git clone https://github.com/sidhant97/ai-travel-planner.git
cd ai-travel-planner

```

**2. Create and Activate Virtual Environment**

* Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

```


* macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate

```



**3. Install Dependencies**

```bash
pip install -r requirements.txt

```

**4. Ingest Knowledge Base Documents**

```bash
python rag_engine.py

```

**5. Run the Application**

```bash
streamlit run app.py

```

Access the application at `http://localhost:8501`.

**6. Run Verification Tests**

```bash
python test_suite.py

```

---

## Sample Queries & Acceptance Scenarios

| Category | Sample User Prompt | Executed Components | Expected Outcome |
| --- | --- | --- | --- |
| **RAG Retrieval** | "What are the must-visit cultural neighbourhoods in Singapore?" | ChromaDB semantic search | Detailed breakdown citing source documentation. |
| **RAG Retrieval** | "What indoor attractions can I visit with family?" | ChromaDB semantic search | Curated indoor locations filtered by family suitability. |
| **Currency Tool** | "Convert INR 60,000 to SGD." | Frankfurter MCP Tool | Live conversion rate and converted amount displayed. |
| **Currency Tool** | "How much is 200 SGD in INR?" | Frankfurter MCP Tool | Reverse conversion using current reference rates. |
| **Weather Tool** | "What is the weather forecast for Singapore over the next 3 days?" | Open-Meteo MCP Tool | Daily temperature ranges and precipitation chances. |
| **Weather Tool** | "Is rain expected during my trip tomorrow?" | Open-Meteo MCP Tool | Precipitation check for next-day schedule validation. |
| **Combined Scenario** | "Plan a 3-day Singapore trip. I have a budget of INR 60,000. Adjust the itinerary for weather with indoor alternatives if it rains." | RAG + Weather Tool + FX Tool + LLM | Converted budget, structured 3-day plan, and weather-triggered indoor backups. |
| **Multi-Turn Context** | *Follow-up:* "Can you replace the second day's dinner with authentic street food near Chinatown?" | Orchestrator Session History + RAG | Itinerary update preserving previously converted currency and itinerary days. |
| **Out-of-Scope Test** | "Can you book a flight ticket from Delhi to Changi Airport?" | Domain Guardrails | Rejection message stating booking and reservations fall outside scope. |

---

## Knowledge Base References (Sample Destination: Singapore)

* **Wikivoyage: Singapore Travel Guide**: Transportation systems, neighborhood zones, cultural etiquette, and practical tips.
* **Visit Singapore: Essential Travel Information**: Public transit cards, climate advisories, laws, and connectivity.
* **Visit Singapore: Sample Itineraries & Things to Do**: Multi-day route blueprints, family activities, and landmark attractions.

---

## Future Scope & Production Roadmap

* **Advanced LLM Tier Support**: Incorporate Anthropic Claude 3.5 Sonnet and OpenAI GPT-4o for complex reasoning, multi-language translation, and long-horizon travel planning.
* **Cloud Storage & Dynamic Document Ingestion**: Offload static document storage to Amazon S3 or Google Cloud Storage. Enable real-time document upload via the UI, syncing vector representations directly to a persistent managed vector database (e.g., Pinecone, AWS OpenSearch, or pgvector).
* **Containerization & Orchestration**: Package the application into lightweight Docker containers and orchestrate deployments via Kubernetes (EKS/GKE) with horizontal pod autoscaling for high-concurrency usage.
* **Expanded Multi-Country Support**: Extend automated ingestion pipelines to pull, validate, and chunk multi-country travel boards, dynamically switching vector namespaces based on user destination selection.
* **Extended Tool Integrations**: Add transit routing MCP tools (Google Maps / Citymapper) and flight/hotel price estimation scrapers.


##  Developer Profile

* **Developer Name:** Sidhant Gupta
* **Email Contact:** guptasidhant1997@gmail.com
* **Contact Number:** +91-9996764596

```