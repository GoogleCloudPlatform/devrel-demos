/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export interface BiomeCardProps {
    label: string;
    icon: string;
    colorClass: string; // e.g., 'bg-terrain-blue'
}

export function BiomeCard({ label, icon, colorClass }: BiomeCardProps): string {
    return `
    <button class="group relative flex flex-col items-center gap-2">
      <div class="w-16 h-16 rounded-full ${colorClass} border-4 border-white flex items-center justify-center text-white group-hover:scale-125 transition-transform">
        <span class="material-symbols-outlined !text-3xl">${icon}</span>
      </div>
      <span class="font-display text-sm">${label}</span>
    </button>
  `;
}
