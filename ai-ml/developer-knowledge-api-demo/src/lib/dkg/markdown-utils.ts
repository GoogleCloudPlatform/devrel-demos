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


/**
 * @file markdown-utils.ts
 * @description Provides functions to parse markdown content into structured sections (H2, H3).
 * Why it matters: Used to extract searchable sections from documentation content.
 */

// Interface for a documentation section.
export interface Section {
  title: string;
  anchor: string;
  level: number;
  content: string;
  subsections: Section[];
}

// Parses markdown content into structured sections based on H2 and H3 headers.
export function parseSectionsFromMarkdown(content: string): Section[] {
  const sections: Section[] = [];
  const lines = content.split('\n');
  let currentH2: Section | null = null;
  let currentH3: Section | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const h2Match = line.match(/^##\s+(.+)$/);
    const h3Match = line.match(/^###\s+(.+)$/);

    if (h2Match) {
      const title = h2Match[1].replace(/\{:\s*#[^}]+\}/g, '').trim();
      const anchor = title.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');

      currentH2 = {
        title,
        anchor,
        level: 2,
        content: '',
        subsections: []
      };
      sections.push(currentH2);
      currentH3 = null; // Reset H3 when new H2 starts
    } else if (h3Match && currentH2) {
      // H3 belongs to current H2
      const title = h3Match[1].replace(/\{:\s*#[^}]+\}/g, '').trim();
      const anchor = title.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-');

      currentH3 = {
        title,
        anchor,
        level: 3,
        content: '',
        subsections: []
      };
      currentH2.subsections.push(currentH3);
    } else {
      // Content line
      // Basic accumulation
      // If we are in an H3, append to H3. Else if in H2, append to H2. Else ignore (pre-header content)
      if (currentH3) {
        currentH3.content += line + '\n';
      } else if (currentH2) {
        currentH2.content += line + '\n';
      }
    }
  }

  // Trim content
  sections.forEach(s => {
    s.content = s.content.trim();
    s.subsections.forEach(sub => sub.content = sub.content.trim());
  });

  return sections;
}
