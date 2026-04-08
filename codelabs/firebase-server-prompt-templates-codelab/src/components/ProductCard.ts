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

import type { Product } from '../types';

export function ProductCard(product: Product): string {
    // Check if label exists to conditionally render it
    const labelHtml = product.label
        ? `<div class="absolute top-2 left-2 ${product.labelColorClass} text-white px-3 py-1 font-display text-xs">${product.label}</div>`
        : '';

    return `
    <a href="?product=${product.id}" class="group block border-4 border-terrain-earth bg-white p-1 hover:shadow-[8px_8px_0px_0px_rgba(27,79,114,1)] transition-all cursor-pointer">
      <div class="relative aspect-square overflow-hidden mb-4 bg-gray-200">
        <div class="absolute inset-0 bg-cover bg-center grayscale-0 group-hover:scale-110 transition-transform duration-500" style="background-image: url('${product.image}'); filter: saturate(1.8);"></div>
        ${labelHtml}
      </div>
      <div class="px-2 pb-2">
        <h3 class="font-condensed text-xl font-black leading-tight mb-1 text-terrain-earth group-hover:text-terrain-blue transition-colors">${product.title}</h3>
        <div class="flex justify-between items-center border-t-2 border-terrain-earth pt-2">
          <span class="font-display text-lg text-terrain-orange">${product.price}</span>
          <span class="text-xs font-bold uppercase bg-terrain-earth text-white px-2 py-0.5">${product.spec}</span>
        </div>
      </div>
    </a>
  `;
}
