// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

'use client';

/**
 * @file search-results.tsx
 * @description Component to render search results from the DKG API in a list or accordion layout.
 * Why it matters: Displays the core results to the user and allows viewing details.
 */

import { useState } from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Accordion, AccordionContent, AccordionItem } from '@/components/ui/accordion';
import * as AccordionPrimitive from "@radix-ui/react-accordion";
import { MarkdownRenderer } from '../markdown-renderer';
import { APP_TABS, APP_TAB_LABELS } from '@/lib/constants';
import { ProductConfig } from '@/lib/dkg/products';

interface SearchResultsProps {
  dkgQuery: string;
  setDkgQuery: (query: string) => void;
  dkgResults: any[];
  dkgViewMode: 'topics' | 'sections';
  expandedDkgNodes: Record<string, any>;
  loadingDkgNodes: Record<string, boolean>;
  handleDkgNodeExpand: (ids: string[]) => void;
  knowledgeSources: ProductConfig[];
  dkgError?: string | null;
}

/**
 * SearchResults component to render search results from the DKG API in a list or accordion layout.
 * 
 * @param dkgQuery The current search query.
 * @param setDkgQuery Function to update the search query.
 * @param dkgResults Array of search results.
 * @param dkgViewMode Current view mode ('topics' or 'sections').
 * @param expandedDkgNodes Map of expanded node details.
 * @param loadingDkgNodes Map of loading states for nodes.
 * @param handleDkgNodeExpand Function to handle node expansion.
 * @param knowledgeSources Array of configured knowledge sources.
 * @returns The JSX element for the search results.
 */
export function SearchResults({
  dkgQuery,
  setDkgQuery,
  dkgResults,
  dkgViewMode,
  expandedDkgNodes,
  loadingDkgNodes,
  handleDkgNodeExpand,
  knowledgeSources,
  dkgError,
}: SearchResultsProps) {
  const [showRawSections, setShowRawSections] = useState<Record<string, boolean>>({});

  /**
   * Toggles the raw view state for a specific section.
   * 
   * @param key The unique key for the section.
   */
  const toggleRaw = (key: string) => {
    setShowRawSections(prev => ({ ...prev, [key]: prev[key] === false ? true : false }));
  };

  /**
   * Determines the display string for the source of a result node.
   * 
   * @param node The result node.
   * @returns The display string for the source.
   */
  const getSourceDisplay = (node: any) => {
    // 1. Try to find a matching knowledge source based on the URL or ID
    const isRemoteIds = node.id.startsWith('remote-');
    const isRemoteMeta = node.metadata?.source === 'dkg-api';
    let url = '';

    if (node.metadata?.siteFilter) {
      return node.metadata.siteFilter;
    }

    if (isRemoteMeta && node.metadata?.originalUrl) {
      url = node.metadata.originalUrl;
    } else if (isRemoteIds) {
      try {
        const encoded = node.id.replace('remote-', '');
        const decoded = atob(encoded);
        if (decoded.includes('.')) {
          url = decoded;
        }
      } catch (e) { }
    } else if (node.metadata?.productId === 'dart') {
      return 'dart.dev';
    } else if (node.metadata?.productId === 'flutter') {
      return 'flutter.dev';
    }

    if (url) {
      // Clean URL to match siteFilter format (usually domain/path, no protocol)
      const cleanUrl = url.replace(/^https?:\/\//, '');

      // Find matching source
      // Sort sources by siteFilter length desc to match most specific first
      const matchingSource = knowledgeSources
        .filter(s => s.siteFilter && cleanUrl.includes(s.siteFilter))
        .sort((a, b) => (b.siteFilter?.length || 0) - (a.siteFilter?.length || 0))[0];

      if (matchingSource?.siteFilter) {
        return matchingSource.siteFilter;
      }

      try {
        return new URL(url.startsWith('http') ? url : `https://${url}`).hostname;
      } catch (e) {
        return url;
      }
    }

    return 'Unknown Source';
  };

  const renderedSections = dkgResults.flatMap(result => {
    const items = [];
    for (const section of (result.sections || [])) {
      items.push({ node: result, section, type: 'h2' });
      if (section.subsections) {
        for (const sub of section.subsections) {
          items.push({ node: result, section: sub, type: 'h3', parentSection: section });
          if (sub.subsections) {
            for (const subSub of sub.subsections) {
              items.push({ node: result, section: subSub, type: 'h4', parentSection: sub, grandParentSection: section });
            }
          }
        }
      }
    }
    return items;
  }).map(({ node, section, type, parentSection, grandParentSection }, idx) => {
    const sectionKey = `${node.id}-${section.anchor}-${idx}`;
    const isRaw = showRawSections[sectionKey] !== false;
    return (
      <AccordionItem value={sectionKey} key={sectionKey} className="border rounded-md data-[state=closed]:bg-transparent data-[state=open]:bg-card transition-colors">
        <AccordionPrimitive.Header className="flex w-full items-center justify-between min-w-0">
          <AccordionPrimitive.Trigger className="flex flex-1 items-center gap-3 min-w-0 py-3 px-4 hover:no-underline text-left transition-all [&[data-state=open]>svg]:rotate-180 group">
            <div className="flex-1 min-w-0 w-0 overflow-hidden">
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-semibold text-base truncate min-w-0">
                  {section.title}
                  <span className="text-muted-foreground font-normal">
                    {type === 'h3'
                      ? ` (${node.title} > ${parentSection.title})`
                      : type === 'h4'
                        ? ` (${node.title} > ${grandParentSection.title} > ${parentSection.title})`
                        : ` (${node.title})`
                    }
                  </span>
                </span>
                <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full capitalize shrink-0">
                  Section
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                from: {getSourceDisplay(node)}
              </p>
            </div>
            <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200 text-muted-foreground group-hover:text-foreground" />
          </AccordionPrimitive.Trigger>
        </AccordionPrimitive.Header>
        <AccordionContent>
          <div className="px-4 pb-4 pt-1 space-y-4">
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => toggleRaw(sectionKey)}
              >
                {isRaw ? 'Show Rendered' : 'Show Raw'}
              </Button>
            </div>
            {section.content ? (
              isRaw ? (
                <pre className="bg-muted p-4 rounded-md overflow-x-auto whitespace-pre-wrap text-sm font-mono">
                  {section.content}
                </pre>
              ) : (
                  <MarkdownRenderer content={section.content} />
                )
            ) : (
              !section.subsections?.length && (
                <div className="space-y-4">
                  <div className="border-t -mx-4 mb-4" />
                  <p className="text-sm text-muted-foreground italic mb-2">
                    Click below to view this section on the Flutter website.
                  </p>
                </div>
              )
            )}

            {section.subsections && section.subsections.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">In this section</h5>
                <div className="grid grid-cols-1 gap-1">
                  {section.subsections.map((sub: any, subIdx: number) => (
                    <a
                      key={subIdx}
                      href="#"
                      className="text-base font-medium text-foreground/90 hover:text-primary hover:underline truncate block py-0.5 transition-colors pl-2 border-l-2 border-transparent hover:border-primary/50"
                      onClick={(e) => {
                        e.preventDefault();
                        const path = node.metadata?.path || node.id;
                        const cleanPath = path.startsWith('/') ? path.slice(1) : path;
                        window.open(`https://docs.flutter.dev/${cleanPath}#${sub.anchor}`, '_blank');
                      }}
                    >
                      {sub.title}
                    </a>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-start mt-4">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  const getUrl = () => {
                    if (node.metadata?.source === 'dkg-api' && node.metadata?.originalUrl) {
                      return node.metadata.originalUrl.startsWith('http') ? node.metadata.originalUrl : `https://${node.metadata.originalUrl}`;
                    }
                    if (node.id.startsWith('remote-')) {
                      try {
                        const decoded = atob(node.id.replace('remote-', ''));
                        return decoded.startsWith('http') ? decoded : `https://${decoded}`;
                      } catch (e) { }
                    }
                    const path = node.metadata?.path || node.id;
                    const cleanPath = path.startsWith('/') ? path.slice(1) : path;

                    if (node.metadata?.productId === 'dart') {
                      const finalPath = cleanPath.replace(/^dart-/, '');
                      return `https://dart.dev/${finalPath}#${section.anchor}`;
                    }

                    return `https://docs.flutter.dev/${cleanPath}#${section.anchor}`;
                  };
                  window.open(getUrl(), '_blank');
                }}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                View full topic
              </Button>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    );
  });

  return (
    <Card className="h-full w-full overflow-hidden border-none shadow-none">
      <CardHeader className="pb-4">
        <CardTitle>{APP_TAB_LABELS[APP_TABS.SEARCH]} Results</CardTitle>
        <CardDescription>
          {dkgQuery ? `Results for "${dkgQuery}"` : 'Explore the Knowledge Graph'}
        </CardDescription>
      </CardHeader>
      <CardContent className="h-full p-0">
        <ScrollArea className="h-full">
          <div className="space-y-2 pb-24 px-4 pr-6">
            {dkgError ? (
              <div className="text-center text-destructive p-12 bg-destructive/10 rounded-xl border-dashed border-2 not-prose">
                {dkgError === 'Unauthorized' ? 'API Key is missing or invalid. Please configure it in the Sources tab.' : dkgError}
              </div>
            ) : dkgViewMode === 'sections' && dkgResults.length > 0 ? (
              <Accordion type="single" collapsible className="w-full space-y-2">
                {renderedSections}
                {dkgResults.some(r => r.sections && r.sections.length > 0) === false && (
                    dkgResults.every(r => !r.sections || r.sections.length === 0) && (
                  <p className="text-center text-muted-foreground py-10">
                    No sections found in these results.
                  </p>
                ))}
              </Accordion>
            ) : dkgResults.length > 0 ? (
                <Accordion type="single" collapsible className="w-full space-y-2" onValueChange={(val) => {
                  if (!val) return;
                  const node = dkgResults.find(r => r.id === val);
                  // If it's a local file or already has sections, don't fetch
                  if (node && (node.metadata?.type === 'local-file' || (node.sections && node.sections.length > 0))) {
                    return;
                  }
                  handleDkgNodeExpand([val]);
                }}>
                {dkgResults.map((result: any) => {
                  // Fallback to the result itself if it has sections (local files) or details are missing
                  const details = expandedDkgNodes[result.id] || (result.sections || result.metadata?.type === 'local-file' ? { node: result, neighbors: [] } : null);
                  const isLoading = loadingDkgNodes[result.id];
                  const neighbors = details?.neighbors || [];

                  return (
                    <AccordionItem
                      key={result.id}
                      value={result.id}
                      className="border rounded-md data-[state=closed]:bg-transparent data-[state=open]:bg-card transition-colors"
                    >
                      <AccordionPrimitive.Header className="flex w-full items-center justify-between min-w-0">
                        <AccordionPrimitive.Trigger className="flex flex-1 items-center gap-3 min-w-0 py-3 px-4 hover:no-underline text-left transition-all [&[data-state=open]>svg]:rotate-180 group">
                          <div className="flex-1 min-w-0 w-0 overflow-hidden">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="font-semibold truncate min-w-0">{result.title}</span>
                              <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full capitalize">
                                {result.type}
                              </span>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              from: {getSourceDisplay(result)}
                            </p>
                          </div>
                          <ChevronDown className="h-4 w-4 shrink-0 transition-transform duration-200 text-muted-foreground group-hover:text-foreground" />
                        </AccordionPrimitive.Trigger>

                      </AccordionPrimitive.Header>
                      <AccordionContent>
                        <div className="px-4 pb-4 pt-1 space-y-4">
                          <p className="text-base text-foreground/80 leading-relaxed">
                            {result.description}
                          </p>

                          {isLoading ? (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                              <div className="h-4 w-4 rounded-full bg-muted-foreground/20" />
                              Loading details...
                            </div>
                          ) : (
                            <>
                              {details?.node?.sections?.length > 0 && (
                                <div className="py-2">
                                  <div className="grid grid-cols-1 gap-1 pl-3 border-l-2 border-primary/20">
                                    {details.node.sections.map((section: any, idx: number) => (
                                      <a
                                        key={idx}
                                        href="#"
                                        className="text-base font-medium text-foreground/90 hover:text-primary hover:underline truncate block py-0.5 transition-colors"
                                        onClick={(e) => {
                                          e.preventDefault();

                                          // Resolve URL helper
                                          const getUrl = () => {
                                            if (result.metadata?.source === 'dkg-api' && result.metadata?.originalUrl) {
                                              return result.metadata.originalUrl.startsWith('http') ? result.metadata.originalUrl : `https://${result.metadata.originalUrl}`;
                                            }
                                            if (result.id.startsWith('remote-')) {
                                              try {
                                                const decoded = atob(result.id.replace('remote-', ''));
                                                return decoded.startsWith('http') ? decoded : `https://${decoded}`;
                                              } catch (e) { }
                                            }

                                            const path = result.metadata?.path || result.id;
                                            const cleanPath = path.startsWith('/') ? path.slice(1) : path;

                                            if (result.metadata?.productId === 'dart') {
                                              // Fix double dart- prefix if id has it
                                              const finalPath = cleanPath.replace(/^dart-/, '');
                                              return `https://dart.dev/${finalPath}#${section.anchor}`;
                                            }

                                            return `https://docs.flutter.dev/${cleanPath}#${section.anchor}`;
                                          };

                                          window.open(getUrl(), '_blank');
                                        }}
                                      >
                                        {section.title}
                                      </a>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {neighbors.length > 0 && (
                                <div className="space-y-2">
                                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Related Topics</h4>
                                  <div className="flex flex-wrap gap-2">
                                    {neighbors.slice(0, 10).map((neighbor: any) => (
                                      <Button
                                        key={neighbor.id}
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-xs"
                                        onClick={() => setDkgQuery(neighbor.title)}
                                      >
                                        {neighbor.title}
                                      </Button>
                                    ))}
                                  </div>
                                </div>
                              )}

                              <div className="pt-2 flex">
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => {
                                    const getUrl = () => {
                                      if (result.metadata?.source === 'dkg-api' && result.metadata?.originalUrl) {
                                        return result.metadata.originalUrl.startsWith('http') ? result.metadata.originalUrl : `https://${result.metadata.originalUrl}`;
                                      }
                                      if (result.id.startsWith('remote-')) {
                                        try {
                                          const decoded = atob(result.id.replace('remote-', ''));
                                          return decoded.startsWith('http') ? decoded : `https://${decoded}`;
                                        } catch (e) { }
                                      }
                                      const path = result.metadata?.path || result.id;
                                      const cleanPath = path.startsWith('/') ? path.slice(1) : path;

                                      if (result.metadata?.productId === 'dart') {
                                        const finalPath = cleanPath.replace(/^dart-/, '');
                                        return `https://dart.dev/${finalPath}`;
                                      }

                                      return `https://docs.flutter.dev/${cleanPath}`;
                                    };
                                    window.open(getUrl(), '_blank');
                                  }}
                                >
                                  <ExternalLink className="h-4 w-4 mr-2" />
                                  View full topic
                                </Button>
                              </div>
                            </>
                          )}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            ) : dkgQuery ? (
              <div className="text-center text-muted-foreground p-12 bg-muted/20 rounded-xl border-dashed border-2 not-prose">
                No results found for "{dkgQuery}"
              </div>
            ) : (
              <div className="text-center text-muted-foreground p-12 bg-muted/20 rounded-xl border-dashed border-2 not-prose">
                Start typing to search the Knowledge Graph...
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
