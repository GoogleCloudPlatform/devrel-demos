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
from transformers import AutoModelForCausalLM
from transformers.models.gemma4.modeling_gemma4 import create_causal_mask, create_sliding_window_causal_mask

def run_test():
    device = "mps"
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained("google/gemma-4-e4b", torch_dtype=torch.float32)
    model.eval()
    model.config.use_cache = False
    
    # Fix sliding_window in config so create_sliding_window_causal_mask can find it
    if not hasattr(model.config, 'sliding_window') or model.config.sliding_window is None:
        model.config.sliding_window = getattr(model.config, "sliding_window_size", 4096)
        
    model = model.to(device)
    
    layers = model.model.language_model.layers
    
    print("Running forward pass to capture kwargs...")
    
    captured_kwargs = {}
    def hook(module, args, kwargs):
        captured_kwargs.update(kwargs)
        captured_kwargs['hidden_states'] = args[0]
        if len(args) > 1:
            captured_kwargs['per_layer_input'] = args[1]
        
    layer = layers[36]
    handle = layer.register_forward_pre_hook(hook, with_kwargs=True)
    
    dummy_input = torch.tensor([[1, 2, 3, 4, 5]], device=device)
    with torch.no_grad():
        model(dummy_input)
        
    handle.remove()
    
    h_36 = captured_kwargs['hidden_states'].clone().detach()
    h_36.requires_grad = True
    
    # We need the dictionary of position embeddings!
    position_ids = captured_kwargs['position_ids']
    position_embeddings_dict = {}
    rotary_emb = model.model.language_model.rotary_emb
    for layer_type in model.model.language_model.unique_layer_types:
        position_embeddings_dict[layer_type] = rotary_emb(h_36, position_ids, layer_type=layer_type)
        
    # We also need the attention mask mapping!
    inputs_embeds = model.model.language_model.embed_tokens(dummy_input)
    mask_kwargs = {
        "config": model.config,
        "inputs_embeds": inputs_embeds,
        "attention_mask": None,
        "past_key_values": None,
        "position_ids": position_ids,
    }
    
    causal_mask_mapping = {
        "full_attention": create_causal_mask(**mask_kwargs),
        "sliding_attention": create_sliding_window_causal_mask(**mask_kwargs),
    }
        
    kwargs_template = {k: v for k, v in captured_kwargs.items() if k not in ('hidden_states', 'position_embeddings', 'per_layer_input', 'attention_mask')}
    per_layer_inputs = model.model.language_model.get_per_layer_inputs(dummy_input, None)
    per_layer_inputs = model.model.language_model.project_per_layer_inputs(inputs_embeds, per_layer_inputs)
    
    # Run layers manually to build a clean graph
    h = h_36
    
    for i in range(36, 42):
        layer_type = layers[i].self_attn.layer_type
        layer_kwargs = dict(kwargs_template)
        layer_kwargs['position_embeddings'] = position_embeddings_dict[layer_type]
        layer_kwargs['attention_mask'] = causal_mask_mapping[layer_type]
        layer_kwargs['per_layer_input'] = per_layer_inputs[:, :, i, :] if per_layer_inputs is not None else None
        h = layers[i](h, **layer_kwargs)
            
    h_41 = h
    assert h_41 is not h_36, "h_41 should not be h_36"
    assert h_41.shape == h_36.shape == (1, 5, 2560), f"h_41 shape: {h_41.shape}, h_36 shape: {h_36.shape}"
    seq_len = h_41.shape[1]
    d_model = h_41.shape[-1]
    
    bs = 8
    print(f"h_41 shape: {h_41.shape}")
    print("Running batched backward...")
    grad_out = torch.zeros(bs, *h_41.shape, device=device, dtype=h_41.dtype)
    for i in range(bs):
        # We want to inject 1.0 for the dimension i at all sequence positions.
        grad_out[i, 0, :, i] = 1.0
        
    grads = torch.autograd.grad(
        outputs=h_41,
        inputs=h_36,
        grad_outputs=grad_out,
        retain_graph=True,
        is_grads_batched=True
    )
    
    # grads[0] is (bs, 1, seq_len, d_model)
    J_batched = grads[0].sum(dim=2).squeeze(1) # (bs, d_model)
    
    print("Running unbatched backward loop...")
    J_unbatched = []
    for i in range(bs):
        model.zero_grad()
        g = torch.zeros(*h_41.shape, device=device, dtype=h_41.dtype)
        g[0, :, i] = 1.0
        grad = torch.autograd.grad(
            outputs=h_41,
            inputs=h_36,
            grad_outputs=g,
            retain_graph=True
        )[0]
        J_unbatched.append(grad.sum(dim=1)) # (1, d_model)
        
    J_unbatched = torch.cat(J_unbatched, dim=0) # (bs, d_model)
    
    delta = (J_batched - J_unbatched).abs().max().item()
    print(f"max|Delta| = {delta:.8f}")
    assert delta < 1e-4, f"Batched backward failed! max delta: {delta}"
    print("Smoke test passed: is_grads_batched perfectly matches per-dim loop on L36.")

if __name__ == "__main__":
    run_test()
