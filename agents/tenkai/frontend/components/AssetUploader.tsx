import React from "react";
import { Input, TextArea } from "@/components/ui/input";

interface AssetUploaderProps {
    assetType: 'none' | 'folder' | 'files' | 'git' | 'create';
    setAssetType: (type: 'none' | 'folder' | 'files' | 'git' | 'create') => void;
    files: FileList | null;
    setFiles: (files: FileList | null) => void;
    fileName: string;
    setFileName: (name: string) => void;
    fileContent: string;
    setFileContent: (content: string) => void;
    existingAssets?: any[];
}

export function AssetUploader({
    assetType,
    setAssetType,
    files,
    setFiles,
    fileName,
    setFileName,
    fileContent,
    setFileContent,
    existingAssets = []
}: AssetUploaderProps) {
    return (
        <div className="space-y-6">
            <div className="flex gap-4 border-b border-border pb-4">
                <button
                    type="button"
                    onClick={() => setAssetType('none')}
                    className={`px-4 py-2 rounded font-bold text-xs uppercase tracking-widest transition-colors ${assetType === 'none' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                    None
                </button>
                <button
                    type="button"
                    onClick={() => { setAssetType('folder'); setFiles(null); }}
                    className={`px-4 py-2 rounded font-bold text-xs uppercase tracking-widest transition-colors ${assetType === 'folder' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                    Upload Folder
                </button>
                <button
                    type="button"
                    onClick={() => { setAssetType('files'); setFiles(null); }}
                    className={`px-4 py-2 rounded font-bold text-xs uppercase tracking-widest transition-colors ${assetType === 'files' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                    Upload Files
                </button>
                <button
                    type="button"
                    onClick={() => { setAssetType('create'); setFiles(null); }}
                    className={`px-4 py-2 rounded font-bold text-xs uppercase tracking-widest transition-colors ${assetType === 'create' ? 'bg-secondary text-secondary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                    Create File
                </button>
            </div>

            {existingAssets.length > 0 && (
                <div className="space-y-3">
                    <h4 className="text-xs font-black uppercase tracking-tighter text-muted-foreground">Existing Assets</h4>
                    <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto custom-scrollbar pr-2">
                        {existingAssets.map((asset, idx) => {
                            const isBinary = /\.(jpe?g|png|gif|zip|gz|exe|bin|pdf|docx?|xlsx?)$/i.test(asset.target);
                            return (
                                <div key={idx} className="flex items-center justify-between p-2 bg-card border border-border rounded-md">
                                    <div className="flex items-center gap-3">
                                        <span className="text-lg">{isBinary ? '📦' : '📄'}</span>
                                        <div>
                                            <div className="text-sm font-bold text-foreground">{asset.target}</div>
                                            <div className="text-[10px] text-muted-foreground uppercase">{asset.type} • {isBinary ? 'binary' : 'text'}</div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {(assetType === 'folder' || assetType === 'files') && (
                <div className="space-y-4">
                    <div className="panel p-6 border-dashed bg-muted/10 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                        <div className="text-2xl mb-2 grayscale opacity-50">{assetType === 'folder' ? '📂' : '📄'}</div>
                        <p className="text-xs font-bold text-primary uppercase tracking-widest hover:text-primary/80">
                            {assetType === 'folder' ? 'Click to Select Folder' : 'Click to Select Files'}
                        </p>
                        <input
                            type="file"
                            className="absolute opacity-0 w-full h-full cursor-pointer inset-0 z-10"
                            {...(assetType === 'folder' ? { webkitdirectory: "", directory: "" } as any : { multiple: true })}
                            onChange={(e) => setFiles(e.target.files)}
                        />
                        <p className="text-[10px] uppercase font-mono text-muted-foreground/60 mt-2">
                            {assetType === 'folder' ? "Drag folder here or click" : "Drag files here or click"}
                        </p>
                    </div>

                    {files && files.length > 0 && (
                        <div className="bg-card rounded border border-border p-4 space-y-2 animate-in fade-in slide-in-from-top-2 duration-300">
                            <div className="flex justify-between items-center mb-2 border-b border-border pb-2">
                                <span className="text-xs font-bold uppercase text-muted-foreground">Selected Items ({files.length})</span>
                                <button type="button" onClick={() => setFiles(null)} className="text-xs text-destructive hover:text-destructive/80 transition-colors">Clear Selection</button>
                            </div>
                            <div className="max-h-64 overflow-y-auto space-y-1 pr-2 custom-scrollbar">
                                {Array.from(files).slice(0, 50).map((f: any, i) => (
                                    <div key={i} className="flex justify-between text-xs font-mono text-foreground group py-0.5">
                                        <span className="truncate pr-4 group-hover:text-primary transition-colors">
                                            {f.webkitRelativePath || f.name}
                                        </span>
                                        <span className="text-muted-foreground whitespace-nowrap">{(f.size / 1024).toFixed(1)} KB</span>
                                    </div>
                                ))}
                                {files.length > 50 && (
                                    <div className="text-xs text-muted-foreground italic pt-2 border-t border-border mt-2">
                                        ...and {files.length - 50} more items.
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {assetType === 'create' && (
                <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                    <Input
                        label="Filename"
                        value={fileName}
                        onChange={(e) => setFileName(e.target.value)}
                        required
                        placeholder="e.g. main.go"
                    />
                    <TextArea
                        label="File Content"
                        value={fileContent}
                        onChange={(e) => setFileContent(e.target.value)}
                        rows={8}
                        required
                        className="font-mono"
                        placeholder="// File content here..."
                    />
                </div>
            )}
        </div>
    );
}
