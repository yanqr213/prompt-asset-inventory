export const toolSchema = {
  owner: "tooling",
  purpose: "describe a local file search tool",
  version: "0.2.0",
  privacy: "local filesystem paths only",
  source: "examples/code/toolSchema.js",
  citations: "docs/tool-contract.md",
  name: "search_files",
  description: "Tool schema for searching prompt-like files by pattern.",
  parameters: {
    type: "object",
    properties: {
      query: { type: "string" }
    }
  }
};
