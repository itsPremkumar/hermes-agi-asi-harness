import { useStore, useStoreContext } from '../store/StoreProvider';
import { useStore as useStudioStore } from '../store/studioStore';
import type { ChatMessage, ChatCommand, AgentStatus } from '../types/trace';
import { AGENT_STATUS_COLOR } from '../types/trace';
import { clsx } from 'clsx';
import { useState, useRef, useEffect, FormEvent } from 'react';

/**
 * Chat Interface — Direct control channel.
 * Send goals to agents, view responses + self-critique output,
 * escalate stuck agents.
 */
export default function ChatInterface() {
  const { messages, chatEvents, activeAgentId, agents, sendChat } =
    useStore();
  const { api } = useStoreContext();
  const [inputValue, setInputValue] = useState('');

  // Auto-scroll to bottom
  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const message = parseCommand(inputValue);
    sendChat(
      api,
      message,
    );
    setInputValue('');
  };

  const quickActions = [
    { label: 'Status', cmd: 'status' },
    { label: 'Cancel', cmd: 'cancel' },
    { label: 'Escalate', cmd: 'escalate' },
  ];

  const targetAgentName = activeAgentId
    ? agents[activeAgentId]?.name ?? activeAgentId
    : 'all agents';

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-avo-border p-3">
        <h2 className="text-lg font-semibold text-avo-text">Control Channel</h2>
        <p className="text-sm text-avo-text-muted">
          Target: {targetAgentName}
        </p>
      </div>

      <div
        className="flex-1 space-y-2 overflow-y-auto p-3"
        data-testid="chat-messages"
      >
        {messages.map((msg) => (
          <MessageRow key={msg.id} message={msg} />
        ))}

        {chatEvents.map((event, i) => (
          <ChatEventRow key={`event-${i}`} event={event} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-avo-border p-3">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            className="flex-1 bg-avo-bg border border-avo-border rounded px-3 py-2 text-sm text-avo-text placeholder-avo-text-muted focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="Type a command (e.g. 'avio_execute analyze codebase X') or /status"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            data-testid="chat-input"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium"
            data-testid="send-button"
          >
            Send
          </button>
        </form>

        <div className="mt-2 flex flex-wrap gap-1">
          {quickActions.map((action) => (
            <button
              key={action.cmd}
              onClick={() => {
                const cmd = `/${action.cmd}`;
                const message = parseCommand(cmd);
                sendChat(api, message);
              }}
              className="px-2 py-1 text-xs text-avo-text-muted hover:text-avo-text hover:bg-avo-bg rounded border border-avo-border"
              data-testid={`quick-${action.cmd}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MessageRow({ message }: { message: ChatMessage }) {
  const isOwn = message.role === 'user';
  const isSystem = message.role === 'system';

  return (
    <div
      className={clsx(
        'max-w-[80%] rounded-lg px-3 py-2 text-sm',
        isOwn && 'ml-auto bg-blue-900/30 text-avo-text',
        !isOwn && !isSystem && 'bg-avo-surface text-avo-text',
        isSystem && 'mx-auto text-xs text-avo-text-muted',
      )}
      data-testid="message-row"
    >
      {message.content}
      {message.command && (
        <span className="block text-xs opacity-60">
          Command: {message.command}
        </span>
      )}
    </div>
  );
}

function ChatEventRow({ event }: { event: { type: string; message: string } }) {
  return (
    <div
      className="max-w-[85%] rounded-lg bg-amber-900/20 px-3 py-2 text-xs text-amber-300"
      data-testid="chat-event"
    >
      <span className="font-medium">[{event.type}]</span> {event.message}
    </div>
  );
}

/**
 * Parse a chat string into a ChatMessage.
 * Recognizes slash commands: /execute, /status, /cancel, /escalate
 * Plain text → treated as a goal command for the active agent.
 */
function parseCommand(input: string): Omit<ChatMessage, 'id'> {
  const now = new Date().toISOString();
  const trimmed = input.trim();

  // Slash commands
  if (trimmed.startsWith('/')) {
    const parts = trimmed.slice(1).split(' ');
    const command = parts[0].toLowerCase() as ChatCommand;
    const args = parts.slice(1).join(' ');
    return {
      role: 'user',
      content: trimmed,
      timestamp: now,
      command,
      args,
    };
  }

  // "avio_execute '...'" shorthand
  if (trimmed.toLowerCase().startsWith('avio_execute')) {
    return {
      role: 'user',
      content: trimmed,
      timestamp: now,
      command: 'execute',
      args: trimmed.replace(/^avio_execute\s*/, ''),
    };
  }

  // Plain text → execute as goal
  return {
    role: 'user',
    content: trimmed,
    timestamp: now,
    command: 'execute',
    args: trimmed,
  };
}
