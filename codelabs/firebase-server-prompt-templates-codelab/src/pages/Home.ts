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

import { BiomeCard } from '../components/BiomeCard';
import { ProductCard } from '../components/ProductCard';
import { FeatureCard } from '../components/FeatureCard';
import { biomes, products } from '../data';

export function Home(): string {
    return `
    <section class="relative w-full aspect-[21/9] min-h-[500px] rounded-none border-8 border-terrain-earth overflow-hidden bg-[#d4cbb3] shadow-[12px_12px_0px_0px_rgba(75,83,32,1)]">
        <div class="absolute inset-0 map-texture"></div>
        <div class="absolute inset-0 z-0 opacity-40 mix-blend-multiply bg-cover bg-center" style="background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuBZTP-6YFH1N5O6mGZg2ViHR05j9Xab84giq2tH3U-sZ2EWvriANdRu8Z2G7w-OeoKDGZR4hpLSbqhuJmZQWWAtYtqZRepeivYjrFt-_OBkAxuokoJP410_rFUWHuY8SVu51dZ2gn6OF0uydZxdJh0aNKv_E6h-fCYleZ2MDce5fXsburkqytfot1NLQxaqzhaWpAjMJNG1G9Sb3RITgIuF3imGvyKFIHCdHfhhFEtGyhxRRStdChgAVdELxGZd-w8uu6hG_2w8BkA');"></div>
        <div class="relative z-10 h-full w-full flex flex-col items-center justify-center text-center p-8">
            <h1 class="text-5xl md:text-7xl lg:text-8xl mb-4 text-terrain-earth drop-shadow-md">Choose Your <br/>Adventure</h1>
            <p class="max-w-2xl font-condensed text-xl md:text-2xl font-bold uppercase text-terrain-olive mb-10">Select a biome to gear up for the extreme.</p>
            <div id="biome-grid" class="flex flex-wrap justify-center gap-6">
                ${biomes.map(biome => BiomeCard(biome)).join('')}
            </div>
        </div>
    </section>
    <section>
        <div class="flex items-end justify-between mb-8 border-b-4 border-terrain-blue pb-4">
            <div>
                <h2 class="text-4xl text-terrain-blue">Altitude Armour</h2>
                <p class="font-condensed font-bold uppercase text-terrain-earth">Engineered for the peaks</p>
            </div>
            <a class="font-display text-sm flex items-center gap-2 text-terrain-blue hover:text-terrain-orange" href="#">
                Full Arsenal <span class="material-symbols-outlined">trending_flat</span>
            </a>
        </div>
        <div id="product-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            ${products.filter(p => !['ripstop-pants', 'tactical-pack'].includes(p.id)).map(product => ProductCard(product)).join('')}
        </div>
    </section>
    <section>
        <div class="flex items-end justify-between mb-8 border-b-4 border-terrain-olive pb-4">
            <div>
                <h2 class="text-4xl text-terrain-olive">Woodland Resilience</h2>
                <p class="font-condensed font-bold uppercase text-terrain-earth">Silent, Durable, Adaptive</p>
            </div>
        </div>
        <div id="feature-grid" class="grid grid-cols-1 md:grid-cols-2 gap-8">
             ${products.filter(p => ['ripstop-pants', 'tactical-pack'].includes(p.id)).map(product => FeatureCard({
        id: product.id,
        image: product.image,
        title: product.title,
        description: product.description,
        price: product.price,
        buttonText: 'View Gear'
    })).join('')}
        </div>
    </section>
    <section class="relative h-64 border-8 border-terrain-blue overflow-hidden group">
        <div class="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105" style="background-image: url('https://lh3.googleusercontent.com/aida-public/AB6AXuCZpsHGB5nXccGwHqsDhgq_c1UaGSFgSmnL1nGnns9iW3JC8zNceYEXb5Uu8nZHqqp9uQ0g_H7XcvpzQY8P336mk-mWM1GP0XiVu2fwHJz7AIRFPx5g_HCNL-aYI0hqVriyst3GKJH_L9qtIp0tpAtOE2zTrrktUP-gz1QfdFMXqq2xIQPDeBWxZB_ysLbpGgt-1p4FpPnaLtz0Tm0zsmie2Vh2vmeBytMRgBdGFGOwk_3Bd5Z7l4sS6PRCZcMkvQaqIC4WPBy-CUM'); filter: saturate(2) brightness(0.6);"></div>
        <div class="relative h-full flex flex-col items-center justify-center text-white text-center">
            <h2 class="text-5xl lg:text-6xl drop-shadow-lg">HYDRO-BARRIER</h2>
            <p class="font-display text-sm tracking-[0.4em] uppercase">100% Submersible Technology Coming Soon</p>
        </div>
    </section>
  `;
}
