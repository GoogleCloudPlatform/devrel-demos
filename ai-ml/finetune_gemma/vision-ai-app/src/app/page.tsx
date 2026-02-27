"use client";

import { useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { ChatInterface } from "@/components/chat-interface";
import { SettingsDialog } from "@/components/settings-dialog";
import { NewChatDialog } from "@/components/new-chat-dialog";
import { Conversation, Message, BackendService } from "@/lib/types";
import { useLocalStorage } from "@/hooks/use-local-storage";
import { v4 as uuidv4 } from "uuid";
import { Loader2, PawPrint } from "lucide-react";

export default function Home() {
  const [conversations, setConversations, isConversationsLoaded] = useLocalStorage<Conversation[]>("conversations", []);
  const [settings, setSettings, isSettingsLoaded] = useLocalStorage<{ selectedBackends: BackendService[] }>("settings", {
    selectedBackends: [],
  });
  
  const [activeId, setActiveId] = useState<string | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);

  if (!isConversationsLoaded || !isSettingsLoaded) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-gray-50">
        <Loader2 className="animate-spin text-[#1a73e8]" size={32} />
      </div>
    );
  }

  const activeConversation = conversations.find((c) => c.id === activeId) || null;

  const handleStartNewChat = () => {
    if (settings.selectedBackends.length === 0) {
      setIsSettingsOpen(true);
    } else {
      setIsNewChatOpen(true);
    }
  };

  const handleCreateChat = (backendUrl: string, modelId: string) => {
    const newChat: Conversation = {
      id: uuidv4(),
      title: "New Analysis",
      messages: [],
      modelId: modelId,
      backendUrl: backendUrl,
      createdAt: Date.now(),
      isNew: true,
    };
    setConversations([newChat, ...conversations]);
    setActiveId(newChat.id);
    setIsNewChatOpen(false);
  };

  const handleSelectChat = (id: string) => {
    setActiveId(id);
  };

  const handleDeleteChat = (id: string) => {
    const newConversations = conversations.filter((c) => c.id !== id);
    setConversations(newConversations);
    if (activeId === id) {
      setActiveId(newConversations[0]?.id || null);
    }
  };

  const handleSendMessage = async (text: string, image?: string) => {
    if (!activeId || !activeConversation) return;

    const { backendUrl, modelId } = activeConversation;
    const isFirstMessage = activeConversation.messages.length === 0;

    // Default pet analysis prompt
    const PET_PROMPT = `Please analyze this pet image and provide the following details:
1. **Breed Identification**: What breed(s) is this pet?
2. **Species**: Is it a dog or a cat?
3. **Key Characteristics**: Describe its physical features (coat, size, color).
4. **General Temperament**: What is this breed known for?
5. **Care Advice**: Provide 2-3 specific care tips for this breed.

Finally, provide a very short "Title" for this analysis in the format: "TITLE: [Animal] [Breed]" (e.g., TITLE: Dog Golden Retriever).`;

    const effectiveText = (isFirstMessage && image && !text.trim()) ? PET_PROMPT : text;

    // Build user message content
    let content: any = effectiveText;
    if (image) {
      content = [];
      if (effectiveText.trim()) {
        content.push({ type: "text", text: effectiveText.trim() });
      }
      content.push({ type: "image_url", image_url: { url: image } });
    }

    const userMessage: Message = { role: "user", content };
    
    // For UI display of the first message, if it contains the PET_PROMPT, 
    // we want to show a cleaner version (just the image or a simple text)
    const displayMessage: Message = isFirstMessage && image ? {
      role: "user",
      content: [{ type: "image_url", image_url: { url: image } }]
    } : userMessage;

    // Update UI immediately with display message
    setConversations((prev) => 
      prev.map((c) => {
        if (c.id === activeId) {
          const newMessages = [...c.messages, displayMessage];
          return {
            ...c,
            messages: newMessages,
            isNew: false, // No longer new after sending first message
          };
        }
        return c;
      })
    );
    
    setIsSending(true);
    try {
      const sanitizeMessages = (msgs: Message[]): Message[] => {
        const filtered = msgs.filter(m => {
          if (m.role === "system") return true;
          if (m.role === "assistant" && typeof m.content === "string" && m.content.startsWith("Error:")) return false;
          if (m.role === "assistant" && typeof m.content === "string" && !m.content.trim()) return false;
          return true;
        });

        const systemMsgs = filtered.filter(m => m.role === "system");
        const chatMsgs = filtered.filter(m => m.role !== "system");
        const sanitized: Message[] = [...systemMsgs];
        
        for (const msg of chatMsgs) {
          if (sanitized.length > 0 && sanitized[sanitized.length - 1].role === msg.role) {
            const prev = sanitized[sanitized.length - 1];
            if (typeof prev.content === "string" && typeof msg.content === "string") {
              prev.content = `${prev.content}\n\n${msg.content}`;
            } else {
              sanitized[sanitized.length - 1] = { ...msg };
            }
          } else {
            sanitized.push({ ...msg });
          }
        }

        const firstChatIdx = sanitized.findIndex(m => m.role !== "system");
        if (firstChatIdx !== -1 && sanitized[firstChatIdx].role === "assistant") {
           sanitized.splice(firstChatIdx, 1);
        }
        return sanitized;
      };

      const targetConv = conversations.find(c => c.id === activeId) || activeConversation;
      if (!targetConv) throw new Error("Conversation not found");

      const currentMessages = [...targetConv.messages, userMessage];
      const validMessages = sanitizeMessages(currentMessages);

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: backendUrl,
          messages: validMessages,
          model: modelId,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to connect to backend");
      }

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let assistantText = "";
      
      setConversations(prev => prev.map(c => 
        c.id === activeId ? { ...c, messages: [...c.messages, { role: "assistant", content: "" }] } : c
      ));

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") continue;
            
            try {
              const data = JSON.parse(dataStr);
              const token = data.choices[0]?.delta?.content || "";
              if (token) {
                assistantText += token;
                
                // Extract TITLE if present
                let extractedTitle = "";
                const titleMatch = assistantText.match(/TITLE:\s*(.+)$/i);
                if (titleMatch && titleMatch[1]) {
                  // Trim whitespace and surrounding asterisks (markdown bold)
                  extractedTitle = titleMatch[1].trim().replace(/^\*+|\*+$/g, "");
                }

                setConversations(prev => prev.map(c => {
                  if (c.id === activeId) {
                    const newMessages = [...c.messages];
                    newMessages[newMessages.length - 1] = {
                      ...newMessages[newMessages.length - 1],
                      content: assistantText
                    };
                    return { 
                      ...c, 
                      messages: newMessages,
                      title: (isFirstMessage && extractedTitle) ? extractedTitle : c.title
                    };
                  }
                  return c;
                }));
              }
            } catch (e) {}
          }
        }
      }
    } catch (error: any) {
      console.error("Failed to send message", error);
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error.message || "Failed to get response from backend."}`,
      };
      setConversations(prev => prev.map(c => 
        c.id === activeId ? { ...c, messages: [...c.messages, errorMessage] } : c
      ));
    } finally {
      setIsSending(false);
    }
  };

  const handleUpdateBackends = (backends: BackendService[]) => {
    setSettings({ selectedBackends: backends });
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden text-gray-900">
      <header className="h-12 border-b bg-white flex items-center px-4 shrink-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-[#1a73e8] rounded flex items-center justify-center">
            <PawPrint className="text-white" size={18} />
          </div>
          <h1 className="text-md font-semibold text-gray-800">Pet Analyzer</h1>
        </div>
      </header>
      
      <main className="flex flex-1 overflow-hidden">
        <Sidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={handleSelectChat}
          onNew={handleStartNewChat}
          onDelete={handleDeleteChat}
          onOpenSettings={() => setIsSettingsOpen(true)}
        />
        
        <ChatInterface
          conversation={activeConversation}
          onSendMessage={handleSendMessage}
          isSending={isSending}
        />
      </main>

      <NewChatDialog
        open={isNewChatOpen}
        onOpenChange={setIsNewChatOpen}
        backends={settings.selectedBackends}
        onCreate={handleCreateChat}
      />

      <SettingsDialog
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
        selectedBackends={settings.selectedBackends}
        onSave={handleUpdateBackends}
      />
    </div>
  );
}
