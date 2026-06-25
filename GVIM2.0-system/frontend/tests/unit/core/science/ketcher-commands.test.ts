import { expect, test } from "vitest";

import {
  firstKetcherStructureCommand,
  ketcherCommandsFromPayload,
  ketcherPayloadSource,
  normalizeKetcherCommand,
} from "@/core/science/ketcher-commands";

test("rejects unknown editor commands", () => {
  expect(ketcherCommandsFromPayload({ unknown_commands: [{ type: "load_ket" }] })).toEqual([]);
  expect(normalizeKetcherCommand({ type: "toolbar_click", id: "atom-carbon" })).toBeNull();
  expect(normalizeKetcherCommand({ type: "browser_coordinate_click", x: 1, y: 2 })).toBeNull();
});

test("reads canonical ketcher commands", () => {
  const payload = {
    ketcher_commands: [{ type: "load_molecule", smiles: "CCO" }],
  };

  expect(ketcherCommandsFromPayload(payload)).toEqual([
    { type: "load_molecule", smiles: "CCO" },
  ]);
  expect(firstKetcherStructureCommand(payload)).toEqual({
    type: "load_molecule",
    smiles: "CCO",
  });
});

test("drops unknown commands and invalid mode switches", () => {
  expect(normalizeKetcherCommand({ type: "switch_mode", mode: "bad" })).toBeNull();
  expect(normalizeKetcherCommand({ type: "toolbar_click", id: "atom-carbon" })).toBeNull();
});

test("resolves artifact load source from canonical commands and current structure", () => {
  expect(
    ketcherPayloadSource({
      ketcher_commands: [{ type: "load_reaction", rxnblock: "$RXN\n..." }],
    }),
  ).toMatchObject({ source: "$RXN\n...", rxnblock: "$RXN\n..." });

  expect(
    ketcherPayloadSource({
      current_structure: { canonical_smiles: "c1ccccc1" },
    }),
  ).toMatchObject({ source: "c1ccccc1", smiles: "c1ccccc1" });
});
