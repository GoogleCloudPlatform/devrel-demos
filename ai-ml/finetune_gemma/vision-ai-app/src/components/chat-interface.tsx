"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Message, Conversation } from "@/lib/types";
import { Send, Image as ImageIcon, X, Loader2, User, Bot, Upload } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import ReactMarkdown from "react-markdown";

interface ChatInterfaceProps {
  conversation: Conversation | null;
  onSendMessage: (text: string, image?: string) => void;
  isSending: boolean;
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc ml-4 mb-2 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="text-sm">{children}</li>,
        strong: ({ children }) => <span className="font-bold">{children}</span>,
        code: ({ children }) => <code className="bg-black/10 rounded px-1 text-xs">{children}</code>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

export function ChatInterface({
  conversation,
  onSendMessage,
  isSending,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [image, setImage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation?.messages, isSending]);

  const handleSend = () => {
    if ((!input.trim() && !image) || isSending) return;
    onSendMessage(input, image || undefined);
    setInput("");
    setImage(null);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500 bg-white">
        <Bot size={64} className="mb-4 text-gray-200" />
        <p className="text-xl font-medium">Select an analysis or start a new one</p>
        <p className="text-sm">Make sure to configure a backend in Settings</p>
      </div>
    );
  }

  // If it's a new analysis and no messages yet, show the "Initial Upload" UI
  if (conversation.isNew && conversation.messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col bg-white overflow-hidden h-full">
        <div className="h-14 border-b flex items-center px-6 bg-white shrink-0">
          <h2 className="font-semibold text-gray-800 truncate">New Analysis</h2>
        </div>
        <div 
          className="flex-1 flex flex-col items-center justify-center p-6"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
        >
          <div className="max-w-md w-full space-y-8 text-center">
            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-gray-900">Start Pet Analysis</h3>
              <p className="text-gray-500 text-sm">Upload an image of a dog or cat to begin specialized identification and health analysis.</p>
            </div>

            <div 
              className={`border-2 border-dashed rounded-xl p-12 transition-colors flex flex-col items-center gap-4 cursor-pointer hover:border-[#1a73e8] hover:bg-gray-50 ${image ? "border-[#1a73e8] bg-[#e8f0fe]" : "border-gray-200"}`}
              onClick={() => !image && fileInputRef.current?.click()}
            >
              <input
                type="file"
                accept="image/*"
                className="hidden"
                ref={fileInputRef}
                onChange={handleImageUpload}
              />
              {image ? (
                <div className="relative group">
                  <img src={image} alt="Upload preview" className="max-h-64 rounded-lg shadow-md" />
                  <button
                    onClick={(e) => { e.stopPropagation(); setImage(null); }}
                    className="absolute -top-3 -right-3 bg-red-500 text-white rounded-full p-1.5 shadow-lg hover:bg-red-600 transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <>
                  <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center text-[#1a73e8]">
                    <Upload size={32} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 text-sm">Click to upload or drag and drop</p>
                    <p className="text-xs text-gray-500 mt-1">PNG, JPG, or WEBP (max 10MB)</p>
                  </div>
                </>
              )}
            </div>

            {image && (
              <Button 
                onClick={handleSend}
                disabled={isSending}
                className="w-full h-12 text-lg bg-[#1a73e8] hover:bg-[#1557b0] rounded-xl shadow-md transition-all active:scale-[0.98]"
              >
                {isSending ? (
                  <>
                    <Loader2 size={20} className="animate-spin mr-2" />
                    Analyzing Pet...
                  </>
                ) : (
                  "Run Full Analysis"
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-white overflow-hidden h-full">
      <div className="h-14 border-b flex items-center px-6 bg-white shrink-0">
        <h2 className="font-semibold text-gray-800 truncate">{conversation.title || "Untitled Analysis"}</h2>
        <div className="ml-auto text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
          {conversation.modelId.split("/").pop()}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
        <div className="max-w-3xl mx-auto space-y-6 pb-4">
          {conversation.messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <Avatar className={msg.role === "user" ? "bg-[#1a73e8]" : "bg-gray-200"}>
                <AvatarFallback className="text-xs">
                  {msg.role === "user" ? <User size={16} className="text-white" /> : <Bot size={16} className="text-gray-600" />}
                </AvatarFallback>
              </Avatar>
              <div className={`flex flex-col max-w-[80%] ${msg.role === "user" ? "items-end" : ""}`}>
                <div
                  className={`p-4 rounded-2xl text-sm ${
                    msg.role === "user"
                      ? "bg-[#1a73e8] text-white rounded-tr-none"
                      : "bg-[#f1f3f4] text-gray-800 rounded-tl-none"
                  }`}
                >
                  {typeof msg.content === "string" ? (
                    <MarkdownContent content={msg.content} />
                  ) : (
                    <div className="space-y-4">
                      {msg.content.map((part, j) => {
                        if ("text" in part) {
                          return <MarkdownContent key={j} content={part.text} />;
                        } else if ("image_url" in part) {
                          return (
                            <img
                              key={j}
                              src={part.image_url.url}
                              alt="Uploaded"
                              className="rounded-lg max-h-64 object-contain bg-black/5"
                            />
                          );
                        }
                        return null;
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {isSending && (
            <div className="flex gap-4">
              <Avatar className="bg-gray-200">
                <AvatarFallback>
                  <Bot size={16} className="text-gray-600" />
                </AvatarFallback>
              </Avatar>
              <div className="bg-[#f1f3f4] p-4 rounded-2xl rounded-tl-none flex items-center gap-2">
                <Loader2 size={16} className="animate-spin text-gray-500" />
                <span className="text-sm text-gray-500">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="p-4 border-t bg-white shrink-0">
        <div className="max-w-3xl mx-auto">
          {image && (
            <div className="mb-2 relative inline-block">
              <img src={image} alt="Upload preview" className="h-20 w-20 object-cover rounded-md border" />
              <button
                onClick={() => setImage(null)}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1"
              >
                <X size={12} />
              </button>
            </div>
          )}
          <div className="flex gap-2 items-end">
            <input
              type="file"
              accept="image/*"
              className="hidden"
              ref={fileInputRef}
              onChange={handleImageUpload}
            />
            <Button
              variant="outline"
              size="icon"
              className="rounded-full shrink-0"
              onClick={() => fileInputRef.current?.click()}
            >
              <ImageIcon size={20} className="text-[#1a73e8]" />
            </Button>
            <div className="flex-1 relative">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Ask a follow-up question..."
                className="pr-10 py-6 rounded-2xl bg-[#f1f3f4] border-none focus-visible:ring-1 focus-visible:ring-[#1a73e8]"
              />
              <Button
                size="icon"
                onClick={handleSend}
                disabled={(!input.trim() && !image) || isSending}
                className="absolute right-2 bottom-1.5 h-8 w-8 rounded-full bg-[#1a73e8] hover:bg-[#1557b0]"
              >
                <Send size={16} />
              </Button>
            </div>
          </div>
          <p className="text-[10px] text-center mt-2 text-gray-400">
            Powered by Gemma 3 & Cloud Run Serverless GPUs
          </p>
        </div>
      </div>
    </div>
  );
}
