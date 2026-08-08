"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, Plus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useOutlet } from "@/context/OutletContext";
import { AI_MESSAGES_BY_OUTLET } from "@/data/mock";
import type { AIMessage } from "@/types";

const QUICK_ACTIONS = ["📊 Show revenue risk", "🚨 Initiate surge protocol", "📈 View signals"];

export default function AIOperationsLead() {
  const { activeOutlet } = useOutlet();
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load outlet-specific messages
  useEffect(() => {
    setMessages(AI_MESSAGES_BY_OUTLET[activeOutlet.outlet_id]);
  }, [activeOutlet.outlet_id]);

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function sendMessage(text: string) {
    if (!text.trim()) return;
    const userMsg: AIMessage = { role: "user", text };
    const agentReply: AIMessage = {
      role: "agent",
      text: `Processing your request for ${activeOutlet.name}… Deterministic analysis complete. All metrics are synthetic data for demonstration.`,
    };
    setMessages((prev) => [...prev, userMsg, agentReply]);
    setInput("");
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={activeOutlet.outlet_id}
        className="bento-card ai-card"
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <div className="ai-header">
          <h2 className="ai-title">AI OPERATIONS LEAD</h2>
          <button className="ai-expand" aria-label="Expand AI panel">↗</button>
        </div>

        {/* Message thread */}
        <div className="ai-messages" role="log" aria-live="polite">
          {messages.map((msg, i) => (
            <div key={i} className={`ai-bubble ai-bubble--${msg.role}`}>
              {msg.role === "agent" && (
                <div className="ai-avatar">
                  <span>🤖</span>
                </div>
              )}
              <p className="ai-bubble-text">{msg.text}</p>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Quick actions */}
        <div className="ai-quick-actions">
          {QUICK_ACTIONS.map((a) => (
            <button
              key={a}
              className="ai-chip"
              onClick={() => sendMessage(a)}
            >
              {a}
            </button>
          ))}
        </div>

        {/* Input row */}
        <form
          className="ai-input-row"
          onSubmit={(e) => { e.preventDefault(); sendMessage(input); }}
        >
          <button type="button" className="ai-input-btn" aria-label="Add attachment">
            <Plus size={16} />
          </button>
          <input
            className="ai-input"
            placeholder="Ask something or choose to start"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            aria-label="Message input"
          />
          <button type="button" className="ai-input-btn" aria-label="Voice input">
            <Mic size={16} />
          </button>
          <button type="submit" className="ai-send" aria-label="Send message">
            <Send size={14} />
          </button>
        </form>
      </motion.div>
    </AnimatePresence>
  );
}
