# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import torch
import torch.nn.functional as F

def run_test():
    d = 8
    seq_len = 1
    
    # dummy h_target
    h_target = torch.randn(1, seq_len, d, requires_grad=True)
    
    # dummy network
    weight = torch.randn(d, d)
    bias = torch.randn(d)
    
    # forward
    h_out = F.linear(h_target, weight, bias)
    
    # Batched backward
    grad_out = torch.eye(d).view(d, 1, d).expand(d, seq_len, d)
    J_batched = torch.autograd.grad(h_out, h_target, grad_outputs=grad_out, is_grads_batched=True, retain_graph=True)[0]
    # shape: (d, 1, seq_len, d) => (d, d)
    J_batched = J_batched.sum(dim=(1, 2))
    
    # Unbatched (per-dim) backward
    J_unbatched = []
    for i in range(d):
        g = torch.zeros(1, seq_len, d)
        g[0, :, i] = 1.0
        J_unbatched.append(torch.autograd.grad(h_out, h_target, grad_outputs=g, retain_graph=True)[0])
    J_unbatched = torch.cat(J_unbatched, dim=0).sum(dim=1)
    
    delta = (J_batched - J_unbatched).abs().max().item()
    print(f"max|Delta| = {delta:.6f}")
    assert delta < 1e-4, f"Batched backward failed! max delta: {delta}"
    print("Smoke test passed: is_grads_batched perfectly matches per-dim loop.")

if __name__ == "__main__":
    run_test()
