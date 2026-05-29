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

import { useState } from 'react';
import calmUnicorn from '../assets/unicorn_calm.png';
import neighUnicorn from '../assets/unicorn_neigh.png';

export default function UnicornMascot() {
  const [isNeighing, setIsNeighing] = useState(false);

  return (
    <div 
      className="flex items-center gap-3 cursor-pointer group"
      onClick={() => setIsNeighing(!isNeighing)}
      title="Click me!"
    >
      <img 
        src={isNeighing ? neighUnicorn : calmUnicorn} 
        alt="Friendly Unicorn Mascot" 
        className="w-12 h-12 transition-transform group-hover:scale-110"
      />
      <span className="font-bold text-lg select-none">
        Hackathon Judge
      </span>
    </div>
  );
}
