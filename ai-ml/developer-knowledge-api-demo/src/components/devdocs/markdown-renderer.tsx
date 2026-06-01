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
 * @file markdown-renderer.tsx
 * @description Custom component to render markdown content with specialized support for alerts and code blocks.
 * Why it matters: Ensures consistent and rich rendering of documentation content.
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Info, AlertTriangle, AlertOctagon } from 'lucide-react';
import { cn } from '@/lib/utils';

// Alert styles for different alert types
const ALERT_STYLES = {
  note: {
    icon: Info,
    className: 'border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950/20 text-blue-900 dark:text-blue-100',
    iconClass: 'text-blue-500'
  },
  tip: {
    icon: Info,
    className: 'border-l-4 border-green-500 bg-green-50 dark:bg-green-950/20 text-green-900 dark:text-green-100',
    iconClass: 'text-green-500'
  },
  important: {
    icon: AlertTriangle,
    className: 'border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-950/20 text-purple-900 dark:text-purple-100',
    iconClass: 'text-purple-500'
  },
  warning: {
    icon: AlertTriangle,
    className: 'border-l-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20 text-yellow-900 dark:text-yellow-100',
    iconClass: 'text-yellow-500'
  },
  caution: {
    icon: AlertOctagon,
    className: 'border-l-4 border-red-500 bg-red-50 dark:bg-red-950/20 text-red-900 dark:text-red-100',
    iconClass: 'text-red-500'
  }
};

// Type for alert types
type AlertType = keyof typeof ALERT_STYLES;

// Interface for the MarkdownRenderer component properties
interface MarkdownRendererProps {
  content: string;
  className?: string;
  resolveInternalLink?: (docId: string) => string;
}

// MarkdownRenderer component to render markdown content with specialized
// support for alerts and code blocks.
export function MarkdownRenderer({
  content,
  className,
  resolveInternalLink,
}: MarkdownRendererProps) {

  const preProcessedContent = content
    .replace(/\[([^\]]+)\]\[(?:[^\]]*)\]/g, '$1')
    .replace(/:::(\w+)\s*\n([\s\S]*?)\n:::/g, (match, type, innerContent) => {
      const alertType = type.toLowerCase();
      const quotedContent = innerContent.split('\n').map((line: string) => `> ${line}`).join('\n');
      return `> [!${alertType.toUpperCase()}]\n${quotedContent}`;
    })
    .replace(/!\[(.*?)\]\((.*?)\)\{:\s*([^\}]+)\s*\}/g, (match, alt, srcAndTitle, attrs) => {
      let src = srcAndTitle;
      let title = '';

      const titleMatch = srcAndTitle.match(/^(\S+)\s+"(.*)"$/);
      if (titleMatch) {
        src = titleMatch[1];
        title = titleMatch[2];
      }

      let styleString = '';
      let classString = '';

      // Parse attributes
      // width="100%"
      const widthMatch = attrs.match(/width="([^"]+)"/);
      if (widthMatch) {
        styleString += `width: ${widthMatch[1]};`;
      }

      // height="50px"
      const heightMatch = attrs.match(/height="([^"]+)"/);
      if (heightMatch) {
        styleString += `height: ${heightMatch[1]};`;
      }

      // .classname
      const classMatch = attrs.match(/\.([\w-]+)/g);
      if (classMatch) {
        classString = classMatch.map((c: string) => c.substring(1)).join(' ');
      }

      const styleAttr = styleString ? ` style="${styleString}"` : '';
      const classAttr = classString ? ` class="${classString}"` : '';
      const titleAttr = title ? ` title="${title}"` : '';

      return `<img src="${src}" alt="${alt}"${titleAttr}${styleAttr}${classAttr} />`;
    });

  // Custom rehype plugin to strip 'key' and 'ref' properties from HAST nodes.
  const rehypeStripSpecialTags = () => {
    return (tree: any) => {
      const visit = (node: any) => {
        if (node.type === 'element' && node.properties) {
          if ('key' in node.properties) {
            delete node.properties.key;
          }
          if ('ref' in node.properties) {
            delete node.properties.ref;
          }
        }
        if (node.children && node.children.length > 0) {
          node.children.forEach(visit);
        }
      };
      visit(tree);
    };
  };

  // Memoized custom components for rendering markdown.
  const components = React.useMemo(() => {
    // Helper to strip key from props to prevent duplicate key errors and spread warnings
    // eslint-disable-next-line react/display-name
    const strip = (Tag: any) => ({ node, ...props }: any) => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { key, ...rest } = props;
      return <Tag {...rest} />;
    };

    return {
      // Custom components
      tabs: strip('div'), // Render tabs as divs
      tab: strip('div'),   // Render tab as div

      // Custom blockquote (can't use simple strip because of custom logic)
      blockquote: ({ node, children, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        const arrayChildren = React.Children.toArray(children);
        const firstChild = arrayChildren[0];

        let alertType: AlertType | null = null;

        if (React.isValidElement(firstChild)) {
          const grandChildren = React.Children.toArray(firstChild.props.children);
          if (grandChildren.length > 0 && typeof grandChildren[0] === 'string') {
            const text = grandChildren[0] as string;
            const match = text.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i);
            if (match) {
              alertType = match[1].toLowerCase() as AlertType;
            }
          }
        }

        if (alertType && ALERT_STYLES[alertType]) {
          const style = ALERT_STYLES[alertType];
          const Icon = style.icon;

          return (
            <div className={cn("my-4 rounded-md p-4 flex gap-3", style.className)} {...rest}>
              <Icon className={cn("h-5 w-5 shrink-0 mt-0.5", style.iconClass)} />
              <div className="flex-1 [&>p:first-child]:mt-0 [&>p:first-child]:before:content-none [&>p:first-child]:text-inherit">
                {children}
              </div>
            </div>
          );
        }

        return (
          <blockquote className="border-l-2 pl-4 italic text-muted-foreground" {...rest}>
            {children}
          </blockquote>
        );
      },

      // Code block with copy/regen
      code: ({ node, inline, className, children, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        const match = /language-(\w+)/.exec(className || '');
        const lang = match ? match[1] : '';
        const codeString = String(children).replace(/\n$/, '');

        if (!inline && match) {
          return (
            <div className="my-4 relative group/code not-prose">
              <pre className={cn("bg-zinc-950 text-white p-4 rounded-md overflow-x-auto font-mono text-xs", className)}>
                <code>{codeString}</code>
              </pre>
              <div className="absolute top-2 right-2 flex items-center gap-2">
                <div className="text-[10px] uppercase tracking-wider text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded">{lang}</div>
              </div>
            </div>
          );
        }
        return (
          <code className={cn("bg-muted px-1.5 py-0.5 rounded text-xs font-mono text-muted-foreground", className)} {...rest}>
            {children}
          </code>
        );
      },

      // Links with logic
      a: ({ node, href, children, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        const isExternal = href?.startsWith('http') || href?.startsWith('https');
        const isInternalDoc = href?.startsWith('doc://');

        let target = rest.target;
        let rel = rest.rel;
        let finalHref = href;

        if (isExternal) {
          target = "_blank";
          rel = "noopener noreferrer";
        } else if (isInternalDoc && href) {
          const id = href.replace('doc://', '');
          if (resolveInternalLink) {
            finalHref = resolveInternalLink(id);
          } else {
            finalHref = `/?doc=${id}`;
          }
          target = "_blank";
          rel = "noopener noreferrer";
        }

        return (
          <a
            href={finalHref}
            target={target}
            rel={rel}
            className="text-primary hover:underline font-medium decoration-primary/30 underline-offset-4 cursor-pointer"
            {...rest}
          >
            {children}
          </a>
        );
      },

      // Structural & Basic Elements (Stripped)
      div: strip('div'),
      span: strip('span'),
      p: ({ node, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        return <p className="mb-4 last:mb-0" {...rest} />;
      },
      img: ({ node, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        return <img className="rounded-lg border my-4 max-w-full h-auto" {...rest} />;
      },
      ul: ({ node, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        return <ul className="list-disc pl-6 mb-4 space-y-2" {...rest} />;
      },
      ol: ({ node, ...props }: any) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { key, ...rest } = props;
        return <ol className="list-decimal pl-6 mb-4 space-y-2" {...rest} />;
      },
      li: strip('li'),
      h1: ({ node, ...props }: any) => {
        const { key, ...rest } = props;
        return <h1 className="text-3xl font-bold mt-8 mb-4 border-b pb-2" {...rest} />;
      },
      h2: ({ node, ...props }: any) => {
        const { key, ...rest } = props;
        return <h2 className="text-2xl font-bold mt-8 mb-4 border-b pb-2" {...rest} />;
      },
      h3: ({ node, ...props }: any) => {
        const { key, ...rest } = props;
        return <h3 className="text-xl font-bold mt-6 mb-3" {...rest} />;
      },
      h4: ({ node, ...props }: any) => {
        const { key, ...rest } = props;
        return <h4 className="text-lg font-bold mt-6 mb-3" {...rest} />;
      },
      h5: ({ node, ...props }: any) => {
        const { key, ...rest } = props;
        return <h5 className="text-base font-bold mt-4 mb-2" {...rest} />;
      },
      h6: ({ node, ...props }: any) => {
        const { key, ...rest } = props;
        return <h6 className="text-sm font-bold mt-4 mb-2" {...rest} />;
      },
      pre: ({ children }: any) => <>{children}</>,

      // Extended HTML tags to prevent "duplicate key" errors from raw HTML
      section: strip('section'),
      article: strip('article'),
      header: strip('header'),
      footer: strip('footer'),
      nav: strip('nav'),
      aside: strip('aside'),
      main: strip('main'),
      figure: strip('figure'),
      figcaption: strip('figcaption'),
      table: strip('table'),
      thead: strip('thead'),
      tbody: strip('tbody'),
      tr: strip('tr'),
      th: strip('th'),
      td: strip('td'),
      dl: strip('dl'),
      dt: strip('dt'),
      dd: strip('dd'),
      br: strip('br'),
      hr: strip('hr'),
      em: strip('em'),
      strong: strip('strong'),
      del: strip('del'),
      input: strip('input'),
      button: strip('button'),
      select: strip('select'),
      option: strip('option'),
      textarea: strip('textarea'),
      label: strip('label'),
      dbname: strip('span'),
      username: strip('span')
    };
  }, [resolveInternalLink, content]);

  return (
    <div className={cn("prose prose-lg max-w-none dark:prose-invert break-words", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeStripSpecialTags]}
        urlTransform={(url) => {
          if (url.startsWith('doc://')) return url;
          return url;
        }}
        components={components}
      >
        {preProcessedContent}
      </ReactMarkdown>
    </div>
  );
}
