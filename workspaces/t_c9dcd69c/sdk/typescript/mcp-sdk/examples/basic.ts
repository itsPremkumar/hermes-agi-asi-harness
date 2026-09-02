import { MCPServer, createServer } from "../src";

// Create a server using the factory function
const server = createServer({
  name: "example-server",
  version: "1.0.0",
  description: "An example MCP server",
  author: "MCPHub",
  transport: "stdio",
});

// Register tools
server.registerTool({
  name: "greet",
  description: "Greet a user",
  inputSchema: {
    type: "object",
    properties: {
      name: { type: "string", description: "Name to greet" },
    },
    required: ["name"],
  },
  handler: (args: any) => `Hello, ${args.name}!`,
});

server.registerTool({
  name: "add",
  description: "Add two numbers",
  inputSchema: {
    type: "object",
    properties: {
      a: { type: "number" },
      b: { type: "number" },
    },
    required: ["a", "b"],
  },
  handler: (args: any) => String(args.a + args.b),
});

// List tools
console.log("Tools:", server.listTools());

// Generate manifest
console.log("Manifest:", server.generateManifest());
