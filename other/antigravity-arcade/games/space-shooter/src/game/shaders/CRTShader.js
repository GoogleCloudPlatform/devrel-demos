// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { Renderer } from 'phaser';

export class CRTPipeline extends Renderer.WebGL.Pipelines.PostFXPipeline {
  constructor(game) {
    super({
      game: game,
      name: 'CRTPipeline',
      renderTarget: true,
      fragShader: `
                precision mediump float;
                uniform sampler2D uMainSampler;
                varying vec2 outTexCoord;
                uniform float uTime;

                void main() {
                    vec2 uv = outTexCoord;

                    // Curvature (optional, let's keep it simple first)
                    vec2 dc = uv - 0.5;
                    uv = 0.5 + dc * (1.0 + 0.2 * dot(dc, dc));

                    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
                        gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
                        return;
                    }

                    vec4 color = texture2D(uMainSampler, uv);

                    // Scanlines
                    float scanline = sin(uv.y * 100.0 - uTime * 2.0) * 0.05 + 0.95;

                    // Slight color separation (chromatic aberration)
                    float r = texture2D(uMainSampler, uv + vec2(0.001, 0.0)).r;
                    float g = color.g;
                    float b = texture2D(uMainSampler, uv - vec2(0.001, 0.0)).b;

                    // Vignette
                    vec2 v = uv * (1.0 - uv.yx);
                    float vig = v.x * v.y * 15.0;
                    vig = clamp(pow(vig, 0.25), 0.0, 1.0);

                    gl_FragColor = vec4(vec3(r, g, b) * scanline * vig, color.a);
                }
            `
    });
  }

  onPreRender() {
    this.set1f('uTime', this.game.loop.time / 1000);
  }
}
