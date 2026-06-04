export type McpTransport = "stdio" | "streamable_http" | "sse";

export type McpServiceScope = "global" | "project";

export type McpServiceStatus = "connected" | "idle" | "attention";

export type McpService = {
  id: string;
  name: string;
  description: string;
  transport: McpTransport;
  scope: McpServiceScope;
  status: McpServiceStatus;
  enabled: boolean;
  command?: string;
  args?: string[];
  endpoint?: string;
  env?: Array<{ key: string; value: string }>;
};

export const mockMcpServices: McpService[] = [
  {
    id: "context7",
    name: "context7",
    description: "面向文档检索与上下文增强的全局 MCP 服务。",
    transport: "stdio",
    scope: "global",
    status: "connected",
    enabled: true,
    command: "cmd /c npx",
    args: ["-y", "@upstash/context7-mcp@latest"],
    env: []
  },
  {
    id: "exa",
    name: "exa",
    description: "连接实时网页搜索和摘要能力，适合检索外部资料。",
    transport: "stdio",
    scope: "global",
    status: "connected",
    enabled: true,
    command: "cmd /c npx",
    args: ["-y", "exa-mcp-server@latest"],
    env: [{ key: "EXA_API_KEY", value: "••••••••" }]
  },
  {
    id: "mcp-deepwiki",
    name: "mcp-deepwiki",
    description: "提供结构化知识检索与深链阅读能力。",
    transport: "stdio",
    scope: "global",
    status: "connected",
    enabled: true,
    command: "cmd /c npx",
    args: ["-y", "mcp-deepwiki@latest"],
    env: []
  },
  {
    id: "open-websearch",
    name: "open-websearch",
    description: "聚合公开搜索结果，适合轻量外部事实查询。",
    transport: "stdio",
    scope: "global",
    status: "connected",
    enabled: true,
    command: "cmd /c npx",
    args: ["-y", "open-websearch@latest"],
    env: []
  },
  {
    id: "chrome-devtools",
    name: "chrome-devtools",
    description: "浏览器调试类工具，当前需要补充本机依赖。",
    transport: "stdio",
    scope: "global",
    status: "attention",
    enabled: false,
    command: "npx",
    args: ["chrome-devtools-mcp@latest"],
    env: []
  },
  {
    id: "docs-gateway",
    name: "docs-gateway",
    description: "通过 HTTP 暴露企业内部文档接口。",
    transport: "streamable_http",
    scope: "project",
    status: "idle",
    enabled: false,
    endpoint: "https://docs.internal.example/mcp",
    env: [{ key: "AUTH_MODE", value: "bearer" }]
  }
];
