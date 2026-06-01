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
 * @file schema.ts
 * @description Defines the schema for nodes and edges in the Developer Knowledge Graph (DKG).
 * Why it matters: Ensures consistent data structure for graph nodes and edges across the system.
 */

// Type alias for the node types in the Developer Knowledge Graph.
export type DkgNodeType = 
  | 'concept'       // High level concepts like "State Management"
  | 'widget'        // Flutter Widgets (e.g. Container)
  | 'class'         // Dart Classes (non-widget)
  | 'library'       // Dart Libraries (e.g. dart:async)
  | 'property'      // Class properties
  | 'method'        // Class methods
  | 'mixins'        // Dart Mixins
  | 'enum';         // Dart Enums

// Type alias for the relation types in the Developer Knowledge Graph.
export type DkgRelationType = 
  | 'inherits_from' // Class inheritance
  | 'implements'    // Interface implementation
  | 'mixes_in'      // Mixin usage
  | 'uses'          // General usage (e.g. Widget X uses Widget Y)
  | 'belongs_to'    // Property/Method belongs to Class
  | 'related_to';   // Loose semantic relationship

// Interface for a node in the Developer Knowledge Graph.
export interface DkgNode {
  id: string;             // Unique identifier (e.g. "api.flutter.dev/flutter/widgets/Container-class")
  type: DkgNodeType;
  title: string;          // Human readable title (e.g. "Container")
  description: string;    // Short summary/definition
  content?: string;       // Full markdown content (optional, or stored separately)
  sourcePath: string;     // Relative path to source file in flutter/website
  metadata: Record<string, any>; // Extra data (e.g. stable/beta, platform support)
  sections?: Array<{            // Extracted sections for search
    title: string;
    anchor: string;
    level: number;
  }>;
}

// Interface for an edge (relationship) in the Developer Knowledge Graph.
export interface DkgEdge {
  sourceId: string;
  targetId: string;
  type: DkgRelationType;
  metadata?: Record<string, any>;
}

// Interface for the Developer Knowledge Graph.
export interface DkgGraph {
  nodes: Record<string, DkgNode>;
  edges: DkgEdge[];
  updatedAt: string;
}
