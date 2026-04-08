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

export class Footer {
    private container: HTMLElement;

    constructor() {
        this.container = document.createElement('footer');
        this.container.className = "mt-20 border-t-8 border-terrain-earth bg-terrain-olive text-white pt-16 pb-8";
        this.render();
    }

    private render() {
        this.container.innerHTML = `
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="grid grid-cols-1 gap-12 md:grid-cols-2 lg:grid-cols-4">
          <div class="flex flex-col gap-6">
            <div class="flex items-center gap-3">
              <span class="material-symbols-outlined !text-[40px] text-terrain-orange">explore</span>
              <h2 class="text-2xl font-display leading-none">Rugged <br /><span
                  class="text-sm tracking-[0.2em] text-white/70">Terrain Guide</span></h2>
            </div>
            <p class="font-condensed font-bold uppercase text-white/80">
              Forged in the wild. Proven in the field. Our gear doesn't just survive; it thrives.
            </p>
          </div>
          <div>
            <h3 class="mb-6 text-xl text-terrain-orange">The Arsenal</h3>
            <ul class="flex flex-col gap-3 font-condensed font-bold uppercase text-white/70">
              <li><a class="hover:text-white transition-colors" href="#">Mountain Spec</a></li>
              <li><a class="hover:text-white transition-colors" href="#">Forest Grade</a></li>
              <li><a class="hover:text-white transition-colors" href="#">Aquatic Tech</a></li>
              <li><a class="hover:text-white transition-colors" href="#">Arid Survival</a></li>
            </ul>
          </div>
          <div>
            <h3 class="mb-6 text-xl text-terrain-orange">Intel</h3>
            <ul class="flex flex-col gap-3 font-condensed font-bold uppercase text-white/70">
              <li><a class="hover:text-white transition-colors" href="#">Repair Guides</a></li>
              <li><a class="hover:text-white transition-colors" href="#">Material Science</a></li>
              <li><a class="hover:text-white transition-colors" href="#">Expeditions</a></li>
              <li><a class="hover:text-white transition-colors" href="#">Field Support</a></li>
            </ul>
          </div>
          <div>
            <h3 class="mb-6 text-xl text-terrain-orange">Transmission</h3>
            <p class="mb-6 font-body text-sm text-white/70">Join the frequency for gear drops and tactical updates.</p>
            <form class="flex flex-col gap-2">
              <input
                class="w-full bg-terrain-earth/50 border-2 border-white/20 px-4 py-3 text-sm font-display text-white focus:border-terrain-orange focus:ring-0 placeholder:text-white/30"
                placeholder="IDENTIFY EMAIL" type="email" />
              <button
                class="w-full bg-terrain-orange py-3 text-sm font-display text-white transition-all hover:bg-white hover:text-terrain-orange"
                type="button">
                SUBSCRIBE
              </button>
            </form>
          </div>
        </div>
        <div class="mt-16 flex flex-col items-center justify-between gap-4 border-t border-white/10 pt-8 sm:flex-row">
          <p class="font-condensed text-xs font-bold uppercase text-white/50">© 2024 RUGGED TERRAIN GUIDE. ALL SYSTEMS
            GO.</p>
          <div class="flex gap-6">
            <a class="text-white/50 hover:text-terrain-orange transition-colors" href="#"><span
                class="material-symbols-outlined">satellite_alt</span></a>
            <a class="text-white/50 hover:text-terrain-orange transition-colors" href="#"><span
                class="material-symbols-outlined">hub</span></a>
            <a class="text-white/50 hover:text-terrain-orange transition-colors" href="#"><span
                class="material-symbols-outlined">public</span></a>
          </div>
        </div>
      </div>
        `;
    }

    public mount(target: HTMLElement) {
        target.appendChild(this.container);
    }
}
