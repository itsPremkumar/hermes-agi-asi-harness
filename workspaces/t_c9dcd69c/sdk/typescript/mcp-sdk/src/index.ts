export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  handler: (...args: any[]) => Promise<string> | string;
}

export interface MCPServerConfig {
  name: string;
  version?: string;
  description?: string;
  author?: string;
  transport?: "stdio" | "http" | "sse";
  tools?: MCPTool[];
  metadata?: Record<string, unknown>;
}

export class MCPServer {
  private config: MCPServerConfig;
  private tools: Map<string, MCPTool> = new Map();

  constructor(config: MCPServerConfig) {
    this.config = {
      version: "1.0.0",
      description: "",
      author: "",
      transport: "stdio",
      tools: [],
      metadata: {},
      ...config,
    };
    for (const tool of this.config.tools || []) {
      this.tools.set(tool.name, tool);
    }
  }

  /**
   * Register a tool on this server.
   */
  registerTool(tool: MCPTool): void {
    this.tools.set(tool.name, tool);
  }

  /**
   * List all registered tools.
   */
  listTools(): Array<{
    name: string;
    description: string;
    inputSchema: Record<string, unknown>;
  }> {
    return Array.from(this.tools.values()).map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: t.inputSchema,
    }));
  }

  /**
   * Call a registered tool by name.
   */
  async callTool(
    name: string,
    args: Record<string, unknown>
  ): Promise<{ content?: Array<{ type: string; text: string }>; error?: string }> {
    const tool = this.tools.get(name);
    if (!tool) {
      return { error: `Tool '${name}' not found` };
    }
    try {
      const result = await tool.handler(args);
      return { content: [{ type: "text", text: result }] };
    } catch (e: any) {
      return { error: e?.message || String(e) };
    }
  }

  /**
   * Generate MCP client configuration.
   */
  toMCPConfig(): Record<string, unknown> {
    return {
      mcpServers: {
        [this.config.name]: {
          command: "npx",
          args: ["-y", this.config.name],
        },
      },
    };
  }

  /**
   * Generate server manifest for MCPHub registry.
   */
  generateManifest(): Record<string, unknown> {
    return {
      name: this.config.name,
      version: this.config.version,
      description: this.config.description,
      author: this.config.author,
      transport: this.config.transport,
      tools: this.listTools(),
      metadata: this.config.metadata,
    };
  }
}

/**
 * Factory function to create an MCP server.
 */
export function createServer(config: MCPServerConfig): MCPServer {
  return new MCPServer(config);
}
