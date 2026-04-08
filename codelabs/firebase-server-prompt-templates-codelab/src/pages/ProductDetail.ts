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

export function ProductDetail(product: Product): string {
    const featureList = product.features ? product.features.map(f => `<li class="flex items-center gap-2"><span class="material-symbols-outlined text-terrain-orange text-sm">check_circle</span>${f}</li>`).join('') : '';

    return `
    <div class="flex flex-col gap-8">
        <div class="border-b-4 border-terrain-earth pb-4">
            <a href="/" class="inline-flex items-center gap-2 font-display text-sm text-terrain-earth hover:text-terrain-orange mb-4">
                <span class="material-symbols-outlined">arrow_back</span> BACK TO BASE
            </a>
            <h1 class="text-5xl md:text-7xl text-terrain-earth uppercase leading-none">${product.title}</h1>
        </div>
        
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div class="border-8 border-terrain-earth bg-gray-200 relative aspect-square shadow-[12px_12px_0px_0px_rgba(44,62,80,1)]">
                 <div class="absolute inset-0 bg-cover bg-center" style="background-image: url('${product.image}'); filter: saturate(1.2);"></div>
                 ${product.label ? `<div class="absolute top-4 left-4 ${product.labelColorClass} text-white px-4 py-2 font-display text-sm uppercase tracking-wider border-2 border-white shadow-md">${product.label}</div>` : ''}
            </div>

            <div class="flex flex-col gap-8">
                <div>
                    <div class="flex justify-between items-baseline mb-4">
                        <span class="font-display text-4xl text-terrain-orange">${product.price}</span>
                        <span class="font-condensed font-bold uppercase bg-terrain-earth text-white px-3 py-1 text-sm">${product.spec}</span>
                    </div>
                    <p class="font-body text-lg leading-relaxed text-terrain-earth/80 border-l-4 border-terrain-olive pl-4">
                        ${product.description}
                    </p>
                </div>

                ${featureList ? `
                <div class="bg-white p-6 border-2 border-terrain-earth/10">
                    <h3 class="font-display text-xl mb-4 text-terrain-earth">Tactical Specs</h3>
                    <ul class="font-condensed font-bold uppercase text-terrain-earth/70 grid grid-cols-1 sm:grid-cols-2 gap-3">
                        ${featureList}
                    </ul>
                </div>
                ` : ''}

                <div class="mt-auto">
                    <button class="w-full bg-terrain-orange text-white py-4 font-display text-xl uppercase tracking-widest hover:bg-terrain-earth hover:shadow-[8px_8px_0px_0px_rgba(75,83,32,1)] transition-all transform active:translate-y-1 active:shadow-none border-4 border-transparent hover:border-white">
                        Add to Arsenal
                    </button>
                    <p class="text-center mt-3 font-condensed text-xs uppercase text-terrain-earth/50">Secure Transmission // Global Shipping Available</p>
                </div>
            </div>
        </div>
    </div>
    `;
}
