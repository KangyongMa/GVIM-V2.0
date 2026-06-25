export type KetcherMode = "molecules" | "macromolecules";

export type KetcherCommandType =
  | "open_editor"
  | "load_molecule"
  | "load_reaction"
  | "load_ket"
  | "add_text"
  | "layout"
  | "set_zoom"
  | "set_settings"
  | "switch_mode"
  | "clear";

export type KetcherCommand = Record<string, unknown> & {
  type: KetcherCommandType;
  mode?: KetcherMode;
};

export type KetcherPayloadSource = {
  smiles: string;
  molfile: string;
  rxnblock: string;
  ket: string;
  source: string;
};

const KETCHER_COMMAND_TYPES = new Set<string>([
  "open_editor",
  "load_molecule",
  "load_reaction",
  "load_ket",
  "add_text",
  "layout",
  "set_zoom",
  "set_settings",
  "switch_mode",
  "clear",
]);

const KETCHER_STRUCTURE_COMMAND_TYPES = new Set<KetcherCommandType>([
  "load_molecule",
  "load_reaction",
  "load_ket",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function firstNonEmpty(...values: string[]) {
  return values.find((value) => value.length > 0) ?? "";
}

function normalizeMode(value: unknown): KetcherMode | null {
  const mode = asString(value).toLowerCase();
  if (mode === "molecules" || mode === "molecule") {
    return "molecules";
  }
  if (
    mode === "macromolecules" ||
    mode === "macromolecule" ||
    mode === "sequence"
  ) {
    return "macromolecules";
  }
  return null;
}

export function normalizeKetcherCommand(raw: unknown): KetcherCommand | null {
  if (!isRecord(raw)) {
    return null;
  }
  const rawType = asString(raw.type);
  if (!rawType) {
    return null;
  }

  if (!KETCHER_COMMAND_TYPES.has(rawType)) {
    return null;
  }
  if (rawType === "switch_mode") {
    const mode = normalizeMode(raw.mode);
    return mode ? { ...raw, type: "switch_mode", mode } : null;
  }
  return { ...raw, type: rawType as KetcherCommandType };
}

function normalizedCommandList(value: unknown): KetcherCommand[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => normalizeKetcherCommand(item))
    .filter((item): item is KetcherCommand => item !== null);
}

export function ketcherCommandsFromPayload(
  payload: Record<string, unknown>,
): KetcherCommand[] {
  return normalizedCommandList(payload.ketcher_commands);
}

export function isKetcherStructureCommand(command: KetcherCommand) {
  return KETCHER_STRUCTURE_COMMAND_TYPES.has(command.type);
}

export function firstKetcherStructureCommand(
  payload: Record<string, unknown>,
): KetcherCommand | null {
  return (
    ketcherCommandsFromPayload(payload).find((command) =>
      isKetcherStructureCommand(command),
    ) ?? null
  );
}

export function sourceFromKetcherCommand(command: KetcherCommand | null) {
  if (!command) {
    return "";
  }
  if (command.type === "load_reaction") {
    return firstNonEmpty(
      asString(command.rxnblock),
      asString(command.rxnfile),
      asString(command.reaction),
      asString(command.reaction_smiles),
      asString(command.value),
    );
  }
  if (command.type === "load_ket") {
    return firstNonEmpty(
      asString(command.ket),
      asString(command.source),
      asString(command.value),
    );
  }
  if (command.type === "load_molecule") {
    return firstNonEmpty(
      asString(command.source),
      asString(command.smiles),
      asString(command.canonical_smiles),
      asString(command.molfile),
      asString(command.molblock),
      asString(command.value),
    );
  }
  return "";
}

export function ketcherCommandExpectsStructure(command: KetcherCommand) {
  return isKetcherStructureCommand(command) || command.type === "add_text";
}

export function ketcherCommandMode(command: KetcherCommand) {
  return command.type === "switch_mode" ? normalizeMode(command.mode) : null;
}

export function ketcherPayloadSource(
  payload: Record<string, unknown>,
): KetcherPayloadSource {
  const current = isRecord(payload.current_structure)
    ? payload.current_structure
    : {};
  const command = firstKetcherStructureCommand(payload);
  const commandSource = sourceFromKetcherCommand(command);
  const smiles = firstNonEmpty(
    asString(payload.smiles),
    asString(payload.canonical_smiles),
    asString(current.canonical_smiles),
    asString(current.smiles),
    asString(command?.smiles),
    asString(command?.canonical_smiles),
  );
  const molfile = firstNonEmpty(
    asString(payload.molfile),
    asString(payload.molblock),
    asString(current.molfile),
    asString(current.molblock),
    asString(command?.molfile),
    asString(command?.molblock),
  );
  const rxnblock = firstNonEmpty(
    asString(payload.rxnblock),
    asString(payload.rxnfile),
    asString(command?.rxnblock),
    asString(command?.rxnfile),
  );
  const ket = firstNonEmpty(
    asString(payload.ket),
    asString(current.ket),
    asString(command?.ket),
    command?.type === "load_ket" ? asString(command.value) : "",
  );
  return {
    smiles,
    molfile,
    rxnblock,
    ket,
    source: firstNonEmpty(commandSource, rxnblock, ket, smiles, molfile),
  };
}
