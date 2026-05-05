import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ChevronDown } from "lucide-react";
import { useAuthStore } from "@/lib/store";

const MODEL_OPTIONS = [
  { group: "Ollama (Local)", models: [
    { id: "", label: "Default (Server Setting)" },
    { id: "qwen2.5:3b", label: "Qwen 2.5 3B" },
    { id: "qwen2.5:7b", label: "Qwen 2.5 7B" },
    { id: "llama3.1:8b", label: "Llama 3.1 8B" },
    { id: "gemma2:9b", label: "Gemma 2 9B" },
  ]},
  { group: "Google", models: [
    { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
    { id: "gemini-2.5-pro-preview-05-06", label: "Gemini 2.5 Pro" },
  ]},
  { group: "Anthropic", models: [
    { id: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
    { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5" },
  ]},
  { group: "OpenAI", models: [
    { id: "gpt-4o", label: "GPT-4o" },
    { id: "gpt-4o-mini", label: "GPT-4o Mini" },
  ]},
];

interface Source {
  filename: string;
  score: number;
  content_preview?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isError?: boolean;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const token = useAuthStore((s) => s.token);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      sources: [],
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const res = await fetch("/api/v1/qa/query/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userMsg.content, ...(selectedModel ? { model: selectedModel } : {}) }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const data = line.replace(/^data: /, "").trim();
            if (!data || data === "[DONE]") continue;

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "sources") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsg.id
                      ? { ...m, sources: parsed.data }
                      : m
                  )
                );
              } else if (parsed.type === "token") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsg.id
                      ? { ...m, content: m.content + parsed.data }
                      : m
                  )
                );
              } else if (parsed.type === "error") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsg.id
                      ? { ...m, content: `Error: ${parsed.data}`, isError: true }
                      : m
                  )
                );
              }
            } catch {
              // skip malformed chunks
            }
          }
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to get response.";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? { ...m, content: `Error: ${message}`, isError: true }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Chat</h2>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-20 space-y-2">
            <Bot size={48} className="mx-auto opacity-50" />
            <p className="text-lg">Ask a question about your documents</p>
            <p className="text-sm">Your uploaded documents will be searched for relevant answers.</p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center shrink-0 mt-1">
                <Bot size={16} className="text-blue-600" />
              </div>
            )}
            <div
              className={`max-w-2xl px-4 py-3 rounded-2xl text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : msg.isError
                  ? "bg-red-50 border border-red-200 text-red-700"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
              <div className="whitespace-pre-wrap leading-relaxed">
                {msg.content || (loading ? "Thinking..." : "")}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100 space-y-1">
                  <p className="text-xs font-semibold text-gray-500">Sources:</p>
                  {msg.sources.map((s, i) => (
                    <p key={i} className="text-xs text-gray-400">
                      {s.filename} (relevance: {(s.score * 100).toFixed(1)}%)
                    </p>
                  ))}
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center shrink-0 mt-1">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="pt-4 border-t border-gray-200 space-y-2">
        <div className="flex items-center gap-2">
          <ChevronDown size={14} className="text-gray-400" />
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="text-xs border border-gray-200 rounded-lg px-2 py-1 text-gray-600 bg-white focus:ring-1 focus:ring-blue-500 outline-none"
            disabled={loading}
          >
            {MODEL_OPTIONS.map((group) => (
              <optgroup key={group.group} label={group.group}>
                {group.models.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
          {selectedModel && (
            <span className="text-xs text-gray-400">Model: {selectedModel}</span>
          )}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
