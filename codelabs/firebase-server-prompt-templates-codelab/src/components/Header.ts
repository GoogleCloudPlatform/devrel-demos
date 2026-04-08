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

export class Header {
    private container: HTMLElement;

    constructor() {
        this.container = document.createElement('header');
        this.container.className = "sticky top-0 z-50 w-full bg-terrain-earth text-white border-b-4 border-terrain-orange";
        this.render();
    }

    private render() {
        this.container.innerHTML = `
      <div class="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div class="flex items-center gap-3">
          <span class="material-symbols-outlined !text-[36px] text-terrain-orange">explore</span>
          <h2 class="text-2xl font-display leading-none">Rugged <br /><span class="text-sm tracking-[0.2em]">Terrain
              Guide</span></h2>
        </div>
        <nav class="hidden lg:flex items-center gap-8">
          <a class="font-condensed text-lg font-bold uppercase hover:text-terrain-orange transition-colors"
            href="#">Mountain</a>
          <a class="font-condensed text-lg font-bold uppercase hover:text-terrain-orange transition-colors"
            href="#">Forest</a>
          <a class="font-condensed text-lg font-bold uppercase hover:text-terrain-orange transition-colors"
            href="#">Water</a>
          <a class="font-condensed text-lg font-bold uppercase hover:text-terrain-orange transition-colors"
            href="#">Desert</a>
        </nav>
        <div class="flex items-center gap-4">
          <button
            class="p-2 hover:bg-white/10 rounded-none border-2 border-transparent active:border-terrain-orange transition-all">
            <span class="material-symbols-outlined">search</span>
          </button>
          <button
            class="p-2 hover:bg-white/10 rounded-none border-2 border-transparent active:border-terrain-orange transition-all">
            <span class="material-symbols-outlined">shopping_cart</span>
          </button>
        </div>
      </div>
        `;
    }

    public mount(target: HTMLElement) {
        target.prepend(this.container);
    }
}
