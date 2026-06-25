import type { Message } from "@langchain/langgraph-sdk";

import { extractTextFromMessage } from "@/core/messages/utils";

export type ScienceArtifactKind = "ketcher" | "three-d" | "materials";

export interface ScienceArtifact {
  id: string;
  kind: ScienceArtifactKind;
  title: string;
  toolName?: string;
  toolKey?: string;
  payload: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function firstNonEmpty(...values: string[]) {
  return values.find((value) => value.length > 0) ?? "";
}

function parseToolPayload(message: Message): Record<string, unknown> | null {
  if (message.type !== "tool") {
    return null;
  }
  const text = extractTextFromMessage(message);
  if (!text) {
    return null;
  }
  try {
    const parsed = JSON.parse(text);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function unwrapToolResult(payload: Record<string, unknown>) {
  const result = payload.tool_result;
  return isRecord(result) ? result : payload;
}

function isScienceArtifactKind(value: string): value is ScienceArtifactKind {
  return value === "ketcher" || value === "three-d" || value === "materials";
}

function artifactsFromDeclaredPayload(
  payload: Record<string, unknown>,
  message: Message,
  baseId: string,
): ScienceArtifact[] {
  const declared = payload.science_artifacts;
  if (!Array.isArray(declared)) {
    return [];
  }
  const artifacts: ScienceArtifact[] = [];
  for (const [index, rawArtifact] of declared.entries()) {
    if (!isRecord(rawArtifact)) {
      continue;
    }
    const kind = asString(rawArtifact.kind) as ScienceArtifactKind;
    if (!isScienceArtifactKind(kind)) {
      continue;
    }
    const artifactPayload = isRecord(rawArtifact.payload)
      ? rawArtifact.payload
      : unwrapToolResult(payload);
    artifacts.push({
      id: `${baseId}:${kind}:${index}`,
      kind,
      title:
        asString(rawArtifact.title) ||
        titleForPayload(kind, payload, artifactPayload),
      toolName: typeof message.name === "string" ? message.name : undefined,
      toolKey: firstNonEmpty(
        asString(rawArtifact.tool_key),
        asString(payload.tool_key),
      ),
      payload: artifactPayload,
    });
  }
  return artifacts;
}

function titleForPayload(
  kind: ScienceArtifactKind,
  payload: Record<string, unknown>,
  result: Record<string, unknown>,
) {
  const toolKey = asString(payload.tool_key);
  const formula = firstNonEmpty(
    asString(result.reduced_formula),
    asString(result.formula),
    asString(result.formula_pretty),
  );
  const smiles = firstNonEmpty(
    asString(result.canonical_smiles),
    isRecord(result.current_structure)
      ? asString(result.current_structure.canonical_smiles)
      : "",
  );
  if (kind === "ketcher") {
    return smiles ? `Ketcher: ${smiles}` : "Ketcher structure";
  }
  if (kind === "three-d") {
    return formula || smiles ? `3D structure: ${formula || smiles}` : "3D structure";
  }
  return formula || toolKey ? `Materials: ${formula || toolKey}` : "Materials result";
}

export function extractScienceArtifactsFromMessages(
  messages: Message[],
): ScienceArtifact[] {
  const artifacts: ScienceArtifact[] = [];

  for (const [index, message] of messages.entries()) {
    if (message.type !== "tool") {
      continue;
    }
    const payload = parseToolPayload(message);
    if (!payload) {
      continue;
    }
    const baseId = message.id ?? message.tool_call_id ?? String(index);
    const declaredArtifacts = artifactsFromDeclaredPayload(
      payload,
      message,
      baseId,
    );
    if (declaredArtifacts.length > 0) {
      artifacts.push(...declaredArtifacts);
    }
  }

  return artifacts;
}
