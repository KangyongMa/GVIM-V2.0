# About GVIM AI

GVIM AI is an enterprise-grade super agent workspace for research, coding, data analysis, chemistry, materials, artifacts, uploads, memory, skills, custom agents, and external channel integrations.

## Native Science Capabilities

- Chemistry workspace: molecule/reaction understanding, RDKit-backed descriptors, standardization, similarity, screening, fragments, and 3D conformers.
- Materials workspace: formula triage, crystal structure parsing, XRD simulation and matching, precursor planning, and deliverable artifacts.
- Domain command routing: chemistry and materials requests can open the correct studio tab without replacing the base GVIM AI conversation flow.

## Current Upgrade Scope

- Feedback is stored locally for assistant responses.
- Telegram, Feishu/Lark, Slack, Discord, DingTalk, WeChat, and WeCom can map platform chats to GVIM AI threads through the native channel layer.
- LangGraph threads, runs, and streams use the native LangGraph service entrypoint; Gateway owns GVIM-specific REST APIs.
- Upload validation is part of the native thread upload path so chemistry and materials data files remain first-class inputs while unsafe executable uploads are blocked.
