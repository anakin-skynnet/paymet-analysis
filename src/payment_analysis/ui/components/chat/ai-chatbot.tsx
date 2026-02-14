import { useCallback, useRef, useState } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { postOrchestratorChat } from "@/lib/api";
import { Bot, X } from "lucide-react";

export interface AIChatbotMessage {
  role: "user" | "assistant";
  content: string;
  runPageUrl?: string | null;
  agentsUsed?: string[];
}

const TITLE = "Approval Rate Accelerator";
const PLACEHOLDER = "Ask about recommendations, routing, retries, declines, risk…";

/**
 * AI Chat — always uses the Orchestrator Agent (Model Serving / Job 6).
 * Purpose: semantic search, recommendations, and intelligence to accelerate approval rates.
 * No Genie fallback — the orchestrator is the single source of intelligence.
 */
async function sendToOrchestrator(message: string): Promise<{
  reply: string;
  run_page_url?: string | null;
  agents_used?: string[];
}> {
  const body = { message: message.trim() };
  const opts = { credentials: "include" as RequestCredentials };
  const { data } = await postOrchestratorChat(body, opts);
  return {
    reply: data.reply ?? "",
    run_page_url: data.run_page_url ?? null,
    agents_used: data.agents_used ?? [],
  };
}

export interface AIChatbotProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Position: "left" | "right" for floating panel placement */
  position?: "left" | "right";
}

export function AIChatbot({
  open: controlledOpen,
  onOpenChange,
  position = "right",
}: AIChatbotProps = {}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const isControlled = controlledOpen !== undefined && onOpenChange !== undefined;
  const open = isControlled ? controlledOpen : internalOpen;
  const setOpen = isControlled ? onOpenChange! : setInternalOpen;
  const [messages, setMessages] = useState<AIChatbotMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, []);

  const submit = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const out = await sendToOrchestrator(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: out.reply,
          runPageUrl: out.run_page_url ?? undefined,
          agentsUsed: out.agents_used,
        },
      ]);
      setTimeout(scrollToBottom, 50);
    } catch (e) {
      const err = e instanceof Error ? e.message : "Orchestrator agent unavailable. Ensure Job 6 (Deploy Agents) has been run.";
      setError(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Sorry, I couldn't reach the orchestrator. ${err}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, scrollToBottom]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submit();
      }
    },
    [submit]
  );

  if (!open) return null;

  return (
    <div
      className={cn(
        "fixed bottom-6 z-[100] flex w-[min(420px,calc(100vw-2rem))] flex-col rounded-xl border border-border bg-card text-card-foreground shadow-xl",
        position === "right" && "right-6",
        position === "left" && "left-6"
      )}
      role="dialog"
      aria-label={TITLE}
    >
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-primary/20 text-primary">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <span className="flex-1 font-semibold text-sm">{TITLE}</span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          aria-label="Close"
          onClick={() => setOpen(false)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div
        ref={scrollRef}
        className="flex max-h-[320px] min-h-[200px] flex-1 flex-col gap-3 overflow-y-auto p-4"
      >
        {messages.length === 0 && (
          <p className="text-muted-foreground text-sm">
            Powered by the Orchestrator Agent. Ask about decline trends, routing optimizations, retry strategies, risk assessments, and actionable recommendations to accelerate approval rates.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn("flex gap-2", m.role === "user" ? "justify-end" : "justify-start")}
          >
            {m.role === "assistant" && (
              <Avatar className="h-6 w-6 shrink-0">
                <AvatarFallback className="bg-muted text-muted-foreground text-xs">
                  <Bot className="h-3 w-3" />
                </AvatarFallback>
              </Avatar>
            )}
            <div
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                m.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.role === "assistant" && m.runPageUrl && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="link"
                    size="sm"
                    className="h-auto p-0 text-primary underline"
                    onClick={() => window.open(m.runPageUrl!, "_blank", "noopener,noreferrer")}
                  >
                    View run in Databricks
                  </Button>
                </div>
              )}
              {m.role === "assistant" && m.agentsUsed && m.agentsUsed.length > 0 && (
                <p className="mt-1 text-xs opacity-60">
                  Agents: {m.agentsUsed.join(", ")}
                </p>
              )}
            </div>
            {m.role === "user" && <span className="h-6 w-6 shrink-0" />}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start gap-2">
            <Avatar className="h-6 w-6 shrink-0">
              <AvatarFallback className="bg-muted text-muted-foreground text-xs">
                <Bot className="h-3 w-3" />
              </AvatarFallback>
            </Avatar>
            <div className="rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
              Thinking…
            </div>
          </div>
        )}
        {error && (
          <p className="text-destructive text-sm" role="alert">
            {error}
          </p>
        )}
      </div>
      <div className="flex gap-2 border-t border-border p-3">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={PLACEHOLDER}
          disabled={loading}
          className="min-w-0 flex-1"
          aria-label="Message"
        />
        <Button type="button" onClick={submit} disabled={loading || !input.trim()}>
          Send
        </Button>
      </div>
    </div>
  );
}
