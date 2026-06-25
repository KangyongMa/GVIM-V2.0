import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";

import { MarkdownContent } from "@/components/workspace/messages/markdown-content";

test("renders standard display math without rewriting formula source", () => {
  const content = String.raw`$$n(\text{SrTiO}_3) = \frac{m}{M} = \frac{15.000\ \text{g}}{183.485\ \text{g/mol}} = \mathbf{0.08175\ \text{mol}}$$`;

  const html = renderToStaticMarkup(
    createElement(MarkdownContent, {
      content,
      isLoading: false,
    }),
  );

  expect(html).toContain("katex");
  expect(html).not.toContain("katex-error");
  expect(html).not.toContain(String.raw`($\text{SrTiO}_3$)`);
});
