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

export interface FeatureCardProps {
    image: string;
    title: string;
    description: string;
    price: string;
    buttonText?: string;
    id?: string;
}

export function FeatureCard({ image, title, description, price, buttonText = "Deploy", id }: FeatureCardProps): string {
    const cardContent = `
    <div class="flex flex-col md:flex-row border-4 border-terrain-earth bg-white group hover:shadow-[12px_12px_0px_0px_rgba(75,83,32,1)] transition-all h-full ${id ? 'cursor-pointer' : ''}">
      <div class="w-full md:w-1/2 aspect-square relative overflow-hidden bg-gray-300">
        <div class="absolute inset-0 bg-cover bg-center" style="background-image: url('${image}'); filter: saturate(1.6);"></div>
      </div>
      <div class="w-full md:w-1/2 p-8 flex flex-col justify-center">
        <h3 class="text-3xl mb-4 leading-tight group-hover:text-terrain-olive transition-colors">${title}</h3>
        <p class="font-body text-sm mb-6">${description}</p>
        <div class="flex items-center gap-4 mt-auto">
          <span class="font-display text-2xl text-terrain-orange">${price}</span>
          <button class="bg-terrain-olive text-white px-6 py-2 font-display text-xs uppercase hover:bg-terrain-earth transition-colors">${buttonText}</button>
        </div>
      </div>
    </div>
  `;

    if (id) {
        return `<a href="?product=${id}" class="block h-full">${cardContent}</a>`;
    }

    return cardContent;
}
