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

import type { Product, Biome } from '../types';

export const biomes: Biome[] = [
    { id: 'mountain', label: 'Mountain', icon: 'landscape', colorClass: 'bg-terrain-blue' },
    { id: 'forest', label: 'Forest', icon: 'forest', colorClass: 'bg-terrain-olive' },
    { id: 'water', label: 'Water', icon: 'tsunami', colorClass: 'bg-terrain-orange' },
];

export const products: Product[] = [
    {
        id: 'weatherproof-shell',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBZTP-6YFH1N5O6mGZg2ViHR05j9Xab84giq2tH3U-sZ2EWvriANdRu8Z2G7w-OeoKDGZR4hpLSbqhuJmZQWWAtYtqZRepeivYjrFt-_OBkAxuokoJP410_rFUWHuY8SVu51dZ2gn6OF0uydZxdJh0aNKv_E6h-fCYleZ2MDce5fXsburkqytfot1NLQxaqzhaWpAjMJNG1G9Sb3RITgIuF3imGvyKFIHCdHfhhFEtGyhxRRStdChgAVdELxGZd-w8uu6hG_2w8BkA',
        label: 'Peak Tested',
        labelColorClass: 'bg-terrain-blue',
        title: 'WEATHERPROOF SHELL 4.0',
        price: '$449.00',
        spec: 'Alpine Spec',
        description: 'The ultimate barrier against the elements. Constructed with our proprietary tri-layer membrane, this shell offers 20,000mm waterproofing while maintaining exceptional breathability. Features helmet-compatible hood and reinforced articulation points.',
        features: ['Tri-layer Membrane', 'Helmet Compatible', 'Reinforced Articulation', 'Waterproof Zippers']
    },
    {
        id: 'all-terrain-boots',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAz7yot4-djZu3kJm57J6znnFJw9poT_SMTcQYXoGjpxOKv5_4c20sa3TfjYGY8Zc7B5YVCNv-Vhmd09Zb2GUQNtYKqawkgGbTc2Ern6Fv8v7SPBSL_soFBjmmhJudTOKbznhkbHHRCoHpxTeYpCHQP8kZh5QmCJkqoXIPkPO_jAs64FxbtjJZgyvCnzV9u9nG_RTD6XfIF8NtbU2Co29JOyhdI1itXlEjEeS1cZm9uxDCPbmFFDcvX_BaiR4Q-5oENCSqEB0QcCs0',
        label: 'Unbreakable',
        labelColorClass: 'bg-terrain-orange',
        title: 'ALL-TERRAIN BOOTS',
        price: '$285.00',
        spec: 'Vibram Sole',
        description: 'Dominate any surface with the All-Terrain Boots. Featuring a Vibram Megagrip outsole and abrasion-resistant upper, these boots provide unmatched traction and durability in the harshest environments.',
        features: ['Vibram Megagrip', 'Abrasion Resistant', 'Ankle Support', 'Quick Lacing System']
    },
    {
        id: 'thermal-base-layer',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD9Zd3amieNI1JypaIerSK6meL0fJMO-_3Jd3Px80RSlmVl1QUeybgHdqBTufb_ryw-WLrbNPw5DkbXhPYVzk7vzjNqXZch9cU088pC8E4IMyUkYDWceUOvHwoUfDbfOiiMUrT2cZYvuhxu4Rqh_o1IbB_V8AjDAirv-DQputz00wmTF2k3fQud-mZJ_dCsSvwUnnuKdfzxRQLWzW-156vUYN1Zq_ra4gorIiUcXPZyf77iAnILOGUAZBTD_ZDYuhM_bddoiRhquU0',
        label: '',
        labelColorClass: '',
        title: 'THERMAL BASE LAYER',
        price: '$120.00',
        spec: 'Merino Core',
        description: 'Regulate your core temperature with premium Merino wool. Naturally antimicrobial and moisture-wicking, this base layer keeps you warm when wet and cool when active.',
        features: ['Merino Wool', 'Moisture Wicking', 'Antimicrobial', 'Flatlock Seams']
    },
    {
        id: 'sub-zero-beanie',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDJiS0N-kV89eCT5eh97zoEG5GFGGEvmfjyEWcisp4fJKWgWjEQCjYeEWV7g7U6JYBYudKHJPcGAG07ufuqJB9bCpgy0UtpOCX1A1lqQhKzV3Sa-AZIUbdx9ky693HktZJErY2QFkSjLXI0E25Bu_2w3ypHDb5AqJnNLHVNckmGPaMaJcsr-YHZ3oDWIKC9WnZNgoaABsIwIgobWMl8Cv2-6SmHiPkuwFVwkL3SdghGtKzAi4T_Z506vVzig3S-90c8MdNGfdVmpgI',
        label: '',
        labelColorClass: '',
        title: 'SUB-ZERO BEANIE',
        price: '$45.00',
        spec: 'Windproof',
        description: 'Essential headwear for freezing conditions. Lined with windproof fleece and featuring a knitted outer layer for maximum insulation.',
        features: ['Windproof Fleece Lining', 'Insulated Knit', 'One Size Fits All', 'Quick Dry']
    },
    {
        id: 'ripstop-pants',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCEa0d-kKxPL2aIsZz4VQamrBlLVA12cjGvat6BX-xpfKmaSDeGaeHTuu7vcFBV5j-E4lNF3om6m8SlKnByOXCfRlGWuqQ9xMLWjyyMaODRvNIC_aPiMx25Qdkm2bOFBOkW-fPgbBwpgpnDSqRH2rZoVq5A7YzF7XHKbIAwrqwMY39jJoOrYLLqvEJwBYmNndmclxAEMiltR_sEXWMZj-2qTgbN0fG92J62bfZai901SADkbhvV6TlXFOt3wtqW3TwM1k2Rh7S7sbo',
        label: '',
        labelColorClass: '',
        title: 'RIPSTOP FIELD PANTS',
        price: '$185.00',
        spec: 'Heavy Duty',
        description: 'Reinforced knees and moisture-wicking technology. Designed to navigate the dense undergrowth without compromise.',
        features: ['Reinforced Knees', 'Moisture Wicking', 'Articulated Fit', 'Multi-Pocket Design']
    },
    {
        id: 'tactical-pack',
        image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB5QEV1RFKwViOj7qFhneE3HsemjhqEyER-H1VdzUrgSuhGtDgLkd1sjkGerYQSuKKalK2ZYHkh0GPnVGb73B1iF7WUWi-AFi6qSU4h3DJg98ajVyx1Rc6smvoFKtYayKQon1ZuskjzFq77Ay3R91ImZ-naDVU3C6BVeS5XdxM65mZ-rc6SLBTXMHyTAEyPT5OUEk_PznXVX-lhlxPFUkWwB46OWlP8r0skV8BCYNHt_UNHfj7MV3_27ss2Zcic0hsDjO5KB2rBGnQ',
        label: '',
        labelColorClass: '',
        title: 'TACTICAL PACK 30L',
        price: '$220.00',
        spec: '30L Capacity',
        description: 'Hydration ready with modular attachment points. Built for multi-day excursions deep into the timberline.',
        features: ['Hydration Compatible', 'Modular Attachments', 'Ergonomic Straps', 'Rain Cover Included']
    }
];

