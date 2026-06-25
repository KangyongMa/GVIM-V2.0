# GVIM 2.0 System Architecture

## Scope and Evidence Boundary

This architecture note is derived strictly from the current repository under `E:\Demo of GVIM\deer-flow-mainnew\deer-flow-main` and its active local configuration files. The description therefore includes:

- The deployment topology declared in `docker/docker-compose.yaml` and `docker/docker-compose-dev.yaml`.
- The frontend routing and workspace logic in `frontend/`.
- The FastAPI gateway and embedded LangGraph runtime in `backend/app/gateway/`.
- The lead-agent middleware chain and tool orchestration in `backend/packages/harness/deerflow/agents/`.
- The chemistry and materials computation modules in `backend/packages/harness/gvim_v2/`.
- The enabled external MCP science server declared in `extensions_config.json`.

No component is introduced unless it is explicitly present in the code or configuration.

## SCI-Style Architectural Description

GVIM 2.0 adopts a layered intelligent-agent architecture in which a unified web entry point fronts a general-purpose agent runtime and a domain-specialized scientific augmentation path. At the deployment layer, Nginx serves as the single reverse-proxy boundary on port 2026, forwarding browser traffic to the Next.js frontend and routing `/api` and `/api/langgraph` requests to the FastAPI gateway. The frontend is implemented as a Next.js 16 and React 19 application and acts not merely as a chat interface, but as a structured scientific workspace containing chat, artifact, settings, model, tool, and documentation surfaces.

At the computation layer, the gateway hosts an embedded LangGraph runtime and a lead-agent execution stack. This stack integrates model selection, prompt assembly, skills, memory injection, token accounting, subagent control, and a set of middleware modules that govern runtime behavior. The current code shows that the lead agent is not a chemistry-only service; instead, GVIM preserves a general DeerFlow-style agent substrate and overlays scientific behavior through tool routing, middleware constraints, and native artifact contracts. Persistent thread-local state is maintained under `.deer-flow`, while the current storage backend is configured as SQLite in `config.yaml`. Gateway routers expose operational APIs for models, MCP servers, skills, memory, uploads, threads, artifacts, runs, suggestions, channels, authentication, and feedback.

The chemistry and materials specialization is realized through a verified scientific augmentation path rather than a separate monolithic backend. First, `extensions_config.json` enables an external stdio MCP server named `gvim-science`, which constitutes the runtime bridge from the core agent to scientific tools. Second, the repository includes a package-level scientific execution substrate under `backend/packages/harness/gvim_v2/`, partitioned into `chemistry` and `materials` modules. The chemistry branch contains Ketcher command preparation, structure resolution, RDKit descriptor analysis, similarity computation, reaction quality control, fragmentation, standardization, and three-dimensional conformer generation. The materials branch contains formula and composition analysis, crystal structure parsing and quality control, structure transformation, local environment analysis, Materials Project querying, OPTIMADE querying, precursor planning, XRD simulation and matching, and spectrum baseline and peak analysis. The code in `science_executor.py` further indicates that language models are used only for whitelisted tool planning, whereas scientific calculations are executed by deterministic Python backends.

At the presentation layer, GVIM provides domain-native artifact rendering rather than flattening scientific outputs into plain text. The workspace message renderer consumes `science_artifacts` payloads and maps them to three verified visualization channels: Ketcher-based 2D chemical structure rendering, 3Dmol.js-based three-dimensional molecular visualization, and structured materials-result tables. The middleware `ScienceArtifactCompletionMiddleware` enforces an important architectural invariant: when the user requests native chemistry or materials deliverables, the agent loop is prevented from terminating early until the corresponding scientific artifact has been produced. Consequently, the system architecture is best characterized as a general agent harness with a chemistry-and-materials-specific scientific toolchain, native artifact contract, and visualization path layered on top of the core conversational runtime.

## Files Produced

- Diagram: `docs/gvim2-system-architecture.svg`
- Description: `docs/gvim2-system-architecture.md`
