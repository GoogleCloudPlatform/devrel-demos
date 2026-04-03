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
import { RefreshCw, Server, Loader2, Cpu, AlertTriangle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedBackends: BackendService[];
  onSave: (backends: BackendService[]) => void;
}

export function SettingsDialog({
  open,
  onOpenChange,
  selectedBackends,
  onSave,
}: SettingsDialogProps) {
  const [availableServices, setAvailableServices] = useState<BackendService[]>([]);
  const [loadingServices, setLoadingServices] = useState(false);
  const [localSelected, setLocalSelected] = useState<BackendService[]>(selectedBackends);
  const [probingUrls, setProbingUrls] = useState<Record<string, boolean>>({});
  const [failedUrls, setFailedUrls] = useState<Record<string, boolean>>({});

  const fetchServices = async () => {
    setLoadingServices(true);
    setFailedUrls({});
    try {
      const res = await fetch("/api/services");
      const services: BackendService[] = await res.json();
      setAvailableServices(services);
      
      // Start probing each service in background
      services.forEach(s => probeService(s.url));
    } catch (error) {
      console.error("Failed to fetch services", error);
    } finally {
      setLoadingServices(false);
    }
  };

  const probeService = async (url: string) => {
    setProbingUrls(prev => ({ ...prev, [url]: true }));
    try {
      const res = await fetch("/api/services/probe", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      
      if (data.models && data.models.length > 0) {
        setAvailableServices(prev => prev.map(s => 
          s.url === url ? { ...s, models: data.models } : s
        ));
      } else {
        setFailedUrls(prev => ({ ...prev, [url]: true }));
      }
    } catch (e) {
      setFailedUrls(prev => ({ ...prev, [url]: true }));
    } finally {
      setProbingUrls(prev => ({ ...prev, [url]: false }));
    }
  };

  useEffect(() => {
    if (open) {
      fetchServices();
      setLocalSelected(selectedBackends);
    }
  }, [open, selectedBackends]);

  const toggleService = (service: BackendService) => {
    const hasModels = (service.models && service.models.length > 0);
    if (!hasModels) return; // Prevent selection of invalid services

    setLocalSelected((prev) => {
      const exists = prev.find((s) => s.url === service.url);
      if (exists) {
        return prev.filter((s) => s.url !== service.url);
      } else {
        return [...prev, service];
      }
    });
  };

  const handleSave = () => {
    onSave(localSelected);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:w-[500px] sm:max-w-none">
        <DialogHeader>
          <DialogTitle>Backend Settings</DialogTitle>
          <DialogDescription>
            Choose the Cloud Run services you want to use for chats. Only valid vLLM services can be selected.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 my-2">
          <div className="flex justify-between items-center">
            <h4 className="text-sm font-medium">Available Services</h4>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchServices}
              disabled={loadingServices}
              className="gap-2"
            >
              <RefreshCw size={14} className={loadingServices ? "animate-spin" : ""} />
              Refresh & Probe
            </Button>
          </div>

          <ScrollArea className="h-[350px] border rounded-md w-full">
            <div className="p-3 space-y-2">
              {loadingServices && availableServices.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-[300px] text-gray-500 gap-2">
                  <Loader2 className="animate-spin" />
                  <span className="text-sm">Fetching services...</span>
                </div>
              ) : availableServices.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  No Cloud Run services found.
                </div>
              ) : (
                [...availableServices]
                  .sort((a, b) => {
                    const aHasModels = (a.models && a.models.length > 0) ? 1 : 0;
                    const bHasModels = (b.models && b.models.length > 0) ? 1 : 0;
                    if (aHasModels !== bHasModels) return bHasModels - aHasModels;
                    return a.name.localeCompare(b.name);
                  })
                  .map((service, idx) => {
                  const isSelected = !!localSelected.find((s) => s.url === service.url);
                  const isProbing = probingUrls[service.url];
                  const isFailed = failedUrls[service.url];
                  const hasModels = service.models && service.models.length > 0;
                  const canSelect = hasModels && !isProbing;
                  const isSmall = !hasModels && !isProbing;

                  return (
                    <div
                      key={`${service.name}-${idx}`}
                      className={`flex items-start gap-3 rounded-lg border transition-all w-full ${
                        isSmall ? "p-1.5 opacity-50 bg-gray-50 text-gray-500 border-gray-100" : 
                        "p-3 " + (isSelected ? "border-[#1a73e8] bg-[#e8f0fe] cursor-pointer" : "hover:bg-gray-50 cursor-pointer")
                      } ${!canSelect ? "cursor-not-allowed" : ""}`}
                      onClick={() => canSelect && toggleService(service)}
                    >
                      <div className={isSmall ? "pt-0.5" : "pt-1"} onClick={(e) => e.stopPropagation()}>
                        <Checkbox 
                          checked={isSelected} 
                          disabled={!canSelect}
                          onCheckedChange={() => canSelect && toggleService(service)} 
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Server size={isSmall ? 12 : 14} className={isFailed ? "text-gray-400" : "text-[#1a73e8]"} />
                          <span className={`${isSmall ? "text-xs" : "text-sm"} font-medium truncate`}>{service.name}</span>
                          {isSmall && isFailed && (
                            <div className="flex items-center gap-1 text-[9px] text-orange-600 ml-auto whitespace-nowrap">
                              <AlertTriangle size={10} />
                              Invalid vLLM
                            </div>
                          )}
                        </div>
                        
                        {!isSmall && (
                          <>
                            <div className="text-[10px] text-gray-500 truncate mt-0.5 opacity-80" title={service.url}>
                              {service.url}
                            </div>
                            <div className="mt-2 flex flex-wrap gap-1 items-center min-h-[16px]">
                              {isProbing && (
                                <div className="flex items-center gap-1 text-[10px] text-gray-400">
                                  <Loader2 size={10} className="animate-spin" />
                                  Checking vLLM...
                                </div>
                              )}
                              {!isProbing && isFailed && (
                                <div className="flex items-center gap-1 text-[10px] text-orange-600">
                                  <AlertTriangle size={10} />
                                  Not a valid vLLM service
                                </div>
                              )}
                              {!isProbing && hasModels && service.models!.map((m) => (
                                <span key={m} className="text-[10px] bg-white border px-1.5 py-0.5 rounded text-gray-600 flex items-center gap-1">
                                  <Cpu size={8} />
                                  {m.split("/").pop()}
                                </span>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>
          </ScrollArea>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSave} className="bg-[#1a73e8] hover:bg-[#1557b0]">
            Save Selected
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

