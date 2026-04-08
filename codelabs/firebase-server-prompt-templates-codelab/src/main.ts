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

import { Home } from './pages/Home';
import { ProductDetail } from './pages/ProductDetail';
import { products } from './data';

console.log('Rugged Terrain Guide Loaded');

const appContent = document.querySelector<HTMLElement>('#app-content');

if (appContent) {
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('product');

    if (productId) {
        const product = products.find(p => p.id === productId);
        if (product) {
            appContent.innerHTML = ProductDetail(product);
            // Scroll to top when loading product page
            window.scrollTo(0, 0);
        } else {
            appContent.innerHTML = '<div class="p-10 text-center uppercase font-display text-2xl text-terrain-orange">Product Not Found</div>';
        }
    } else {
        // Render Home Page
        appContent.innerHTML = Home();
    }
}
// Initialize Chat Widget
import { ChatWidget } from './components/ChatWidget';
const chatWidget = new ChatWidget();
chatWidget.mount(document.body);

// Initialize Header and Footer
import { Header } from './components/Header';
import { Footer } from './components/Footer';

const appLayout = document.querySelector<HTMLElement>('#app-layout');
if (appLayout) {
    const header = new Header();
    header.mount(appLayout);

    const footer = new Footer();
    footer.mount(appLayout);
}

