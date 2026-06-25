/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially useful
 * for Docker builds.
 */
import "./src/env.js";
import { fileURLToPath } from "node:url";

function getInternalServiceURL(envKey, fallbackURL) {
  const configured = process.env[envKey]?.trim();
  return configured && configured.length > 0
    ? configured.replace(/\/+$/, "")
    : fallbackURL;
}
import nextra from "nextra";

const withNextra = nextra({});

const editorSingletonPackages = [
  "@codemirror/autocomplete",
  "@codemirror/commands",
  "@codemirror/language",
  "@codemirror/lint",
  "@codemirror/search",
  "@codemirror/state",
  "@codemirror/theme-one-dark",
  "@codemirror/view",
  "@lezer/common",
  "@lezer/css",
  "@lezer/highlight",
  "@lezer/html",
  "@lezer/javascript",
  "@lezer/json",
  "@lezer/lr",
  "@lezer/markdown",
  "@lezer/python",
];

const editorTurbopackAliases = Object.fromEntries(
  editorSingletonPackages.map((pkg) => [pkg, `./node_modules/${pkg}`]),
);

const editorWebpackAliases = Object.fromEntries(
  editorSingletonPackages.map((pkg) => [
    pkg,
    fileURLToPath(new URL(`./node_modules/${pkg}`, import.meta.url)),
  ]),
);

/** @type {import("next").NextConfig} */
const config = {
  allowedDevOrigins: ["192.168.31.179"],
  transpilePackages: editorSingletonPackages,
  turbopack: {
    resolveAlias: editorTurbopackAliases,
  },
  webpack(config) {
    config.resolve ??= {};
    config.resolve.alias ??= {};
    Object.assign(config.resolve.alias, editorWebpackAliases);
    return config;
  },
  output:
    process.env.NEXT_CONFIG_BUILD_OUTPUT === "standalone"
      ? "standalone"
      : undefined,
  i18n: {
    locales: ["en", "zh"],
    defaultLocale: "en",
  },
  devIndicators: false,
  async redirects() {
    return [
      {
        source: "/docs/introduction",
        destination: "/docs/introduction/why-gvim",
        permanent: false,
      },
      {
        source: "/docs/tutorials",
        destination: "/docs/tutorials/first-conversation",
        permanent: false,
      },
      {
        source: "/docs/reference",
        destination: "/docs/reference/model-providers/ark",
        permanent: false,
      },
      {
        source: "/docs/app",
        destination: "/docs/application",
        permanent: false,
      },
      {
        source: "/docs/app/:path*",
        destination: "/docs/application/:path*",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const rewrites = [];
    const gatewayURL = getInternalServiceURL(
      "GVIM_INTERNAL_GATEWAY_BASE_URL",
      "http://127.0.0.1:8001",
    );

    rewrites.push({
      source: "/api/v1/auth/:path*",
      destination: `${gatewayURL}/api/v1/auth/:path*`,
    });

    if (!process.env.NEXT_PUBLIC_LANGGRAPH_BASE_URL) {
      rewrites.push({
        source: "/api/langgraph",
        destination: `${gatewayURL}/api`,
      });
      rewrites.push({
        source: "/api/langgraph/:path*",
        destination: `${gatewayURL}/api/:path*`,
      });
    }

    if (!process.env.NEXT_PUBLIC_BACKEND_BASE_URL) {
      rewrites.push({
        source: "/api/agents",
        destination: `${gatewayURL}/api/agents`,
      });
      rewrites.push({
        source: "/api/agents/:path*",
        destination: `${gatewayURL}/api/agents/:path*`,
      });
      rewrites.push({
        source: "/api/skills",
        destination: `${gatewayURL}/api/skills`,
      });
      rewrites.push({
        source: "/api/skills/:path*",
        destination: `${gatewayURL}/api/skills/:path*`,
      });

      // Catch-all for remaining gateway API routes (models, threads, memory,
      // mcp, artifacts, uploads, suggestions, runs, etc.) that don't have
      // their own NEXT_PUBLIC_* env var toggle.
      //
      // NOTE: this must come AFTER the /api/langgraph rewrite above so that
      // LangGraph-compatible routes keep their public prefix while Gateway
      // receives its native /api/* paths.
      rewrites.push({
        source: "/api/:path*",
        destination: `${gatewayURL}/api/:path*`,
      });
    }

    return rewrites;
  },
};

export default withNextra(config);
