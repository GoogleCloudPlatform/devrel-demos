"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { BackendService } from "@/lib/types";
import { Server, Cpu } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface NewChatDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  backends: BackendService[];
  onCreate: (backendUrl: string, modelId: string) => void;
}

export function NewChatDialog({
  open,
  onOpenChange,
  backends,
  onCreate,
}: NewChatDialogProps) {
  const [selectedServiceUrl, setSelectedServiceUrl] = useState<string>("");
  const [selectedModel, setSelectedModel] = useState<string>("");

  useEffect(() => {
    if (open && backends.length > 0) {
      if (!selectedServiceUrl || !backends.find(b => b.url === selectedServiceUrl)) {
        const firstService = backends[0];
        setSelectedServiceUrl(firstService.url);
        if (firstService.models && firstService.models.length > 0) {
          setSelectedModel(firstService.models[0]);
        }
      }
    }
  }, [open, backends, selectedServiceUrl]);

  const handleServiceChange = (url: string) => {
    setSelectedServiceUrl(url);
    const service = backends.find(s => s.url === url);
    if (service && service.models && service.models.length > 0) {
      setSelectedModel(service.models[0]);
    }
  };

  const currentService = backends.find(s => s.url === selectedServiceUrl);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[450px]">
        <DialogHeader>
          <DialogTitle>Start New Analysis</DialogTitle>
          <DialogDescription>
            Choose from your pre-configured backend services.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Backend Service</label>
            <Select value={selectedServiceUrl} onValueChange={handleServiceChange}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a service" />
              </SelectTrigger>
              <SelectContent>
                {backends.map((s) => (
                  <SelectItem key={s.url} value={s.url}>
                    <div className="flex items-center gap-2">
                      <Server size={14} className="text-[#1a73e8]" />
                      <span>{s.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Model</label>
            <Select 
              value={selectedModel} 
              onValueChange={setSelectedModel}
              disabled={!currentService || !currentService.models || currentService.models.length === 0}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a model" />
              </SelectTrigger>
              <SelectContent>
                {currentService?.models?.map((m) => (
                  <SelectItem key={m} value={m}>
                    <div className="flex items-center gap-2">
                      <Cpu size={14} className="text-[#34a853]" />
                      <span>{m.split("/").pop()}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={() => onCreate(selectedServiceUrl, selectedModel)}
            disabled={!selectedServiceUrl || !selectedModel}
            className="bg-[#1a73e8] hover:bg-[#1557b0]"
          >
            Start Analysis
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
