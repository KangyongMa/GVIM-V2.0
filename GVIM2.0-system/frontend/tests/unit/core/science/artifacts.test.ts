import type { Message } from "@langchain/langgraph-sdk";
import { expect, test } from "vitest";

import { extractScienceArtifactsFromMessages } from "@/core/science";

function toolMessage(
  content: Record<string, unknown>,
  extra: Partial<Message> = {},
): Message {
  return {
    id: "tool-result",
    type: "tool",
    name: "web_search",
    tool_call_id: "tool-call",
    content: JSON.stringify(content),
    ...extra,
  } as Message;
}

test("does not infer a materials artifact from generic web search results", () => {
  const artifacts = extractScienceArtifactsFromMessages([
    toolMessage({
      query: "金华 今天 天气",
      results: [
        {
          title: "金华天气",
          url: "https://www.tianqi.com/jinhua/",
          snippet: "中雨，28~33°C",
        },
      ],
    }),
  ]);

  expect(artifacts).toEqual([]);
});

test("does not infer science artifacts from non-science tools even when rows look material-like", () => {
  const artifacts = extractScienceArtifactsFromMessages([
    toolMessage({
      results: [{ material_id: "mp-149", formula_pretty: "Si" }],
    }),
  ]);

  expect(artifacts).toEqual([]);
});

test("extracts materials artifacts from native GVIM science tool results", () => {
  const artifacts = extractScienceArtifactsFromMessages([
    toolMessage(
      {
        success: true,
        version: "1.0",
        product_surface: "science_copilot",
        domain: "materials",
        tool_key: "materials_project_search",
        tool_result: {
          success: true,
          source: "Materials Project",
          count: 1,
          results: [
            {
              material_id: "mp-149",
              formula_pretty: "Si",
              band_gap: 1.1,
              energy_above_hull_ev_atom: 0,
            },
          ],
        },
        science_artifacts: [
          {
            kind: "materials",
            tool_key: "materials_project_search",
            payload: {
              success: true,
              source: "Materials Project",
              count: 1,
              results: [
                {
                  material_id: "mp-149",
                  formula_pretty: "Si",
                  band_gap: 1.1,
                  energy_above_hull_ev_atom: 0,
                },
              ],
            },
          },
        ],
      },
      {
        id: "materials-result",
        name: "gvim-science_gvim_materials_project_search",
      },
    ),
  ]);

  expect(artifacts).toHaveLength(1);
  expect(artifacts[0]).toMatchObject({
    kind: "materials",
    title: "Materials: materials_project_search",
    toolName: "gvim-science_gvim_materials_project_search",
    toolKey: "materials_project_search",
  });
});
