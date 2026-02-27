"use client";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PlusCircle, MessageSquare, Settings, Trash2, Cpu } from "lucide-react";
import { Conversation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onOpenSettings: () => void;
}

export function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onOpenSettings,
}: SidebarProps) {
  return (
    <div className="w-64 border-r bg-[#f8f9fa] flex flex-col h-full">
      <div className="p-4 border-b">
        <Button
          onClick={onNew}
          className="w-full justify-start gap-2 bg-[#1a73e8] hover:bg-[#1557b0] text-white"
        >
          <PlusCircle size={18} />
          New Analysis
        </Button>
      </div>

      <ScrollArea className="flex-1 p-2">
        <div className="space-y-1">
          {conversations.map((chat) => (
            <div
              key={chat.id}
              className={cn(
                "group flex flex-col gap-1 px-3 py-2 rounded-md cursor-pointer text-sm",
                activeId === chat.id
                  ? "bg-[#e8f0fe] text-[#1a73e8]"
                  : "hover:bg-gray-200 text-gray-700"
              )}
              onClick={() => onSelect(chat.id)}
            >
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="shrink-0" />
                <span className={cn("truncate flex-1", activeId === chat.id ? "font-medium" : "")}>
                  {chat.title || "Untitled Analysis"}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(chat.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-600 transition-opacity"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <div className="flex items-center gap-1.5 ml-6 overflow-hidden">
                <Cpu size={10} className={activeId === chat.id ? "text-[#1a73e8]" : "text-gray-400"} />
                <span className="text-[10px] truncate opacity-70">
                  {chat.modelId.split("/").pop()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      <div className="p-4 border-t mt-auto">
        <Button
          variant="ghost"
          onClick={onOpenSettings}
          className="w-full justify-start gap-2 text-gray-600 hover:bg-gray-200"
        >
          <Settings size={18} />
          Settings
        </Button>
      </div>
    </div>
  );
}
