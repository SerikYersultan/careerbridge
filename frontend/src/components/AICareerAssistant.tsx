import { useMemo, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input } from "./ui/input";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type AssistantResponse = {
  message: string;
};

function mockAssistantReply(userMessage: string): Promise<string> {
  return new Promise((resolve) => {
    setTimeout(() => {
      const normalized = userMessage.toLowerCase();
      if (normalized.includes("roadmap") || normalized.includes("роадмап")) {
        resolve("Based on your Roadmap, you should focus on learning FastAPI first.");
        return;
      }
      resolve(
        "Focus on one core backend stack first, then add SQL, Docker, and testing projects to become job-ready.",
      );
    }, 900);
  });
}

export function AICareerAssistant() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hi! I am your Career Assistant. Ask me about your roadmap and next learning steps.",
    },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setSending(true);
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      const res = await api<AssistantResponse>("/assistant/chat", {
        method: "POST",
        body: { message: text },
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.message }]);
    } catch (e) {
      const reply =
        e instanceof ApiError && e.status !== 404
          ? "I could not reach the assistant service. Please try again in a moment."
          : await mockAssistantReply(text);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <Card className="fixed bottom-4 right-4 z-50 w-[360px] shadow-lg">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          AI Career Assistant
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-64 overflow-y-auto rounded-md border bg-muted/20 p-3 space-y-2">
          {messages.map((m, idx) => (
            <div
              key={`${m.role}-${idx}`}
              className={`rounded-md px-3 py-2 text-sm ${
                m.role === "assistant"
                  ? "bg-background border"
                  : "bg-primary text-primary-foreground ml-6"
              }`}
            >
              {m.content}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about roadmap or skills..."
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void sendMessage();
              }
            }}
          />
          <Button onClick={() => void sendMessage()} disabled={!canSend} size="icon" aria-label="Send">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
