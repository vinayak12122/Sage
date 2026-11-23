# model.py
import math
import os

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer

from llm import config

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        variance = x.float().pow(2).mean(dim=-1, keepdim=True)
        x = x * torch.rsqrt(variance + self.eps)
        return x.to(dtype=self.weight.dtype) * self.weight


# class RoPE(nn.Module):
#     def __init__(self, head_dim: int, theta: float = 10000.0):
#         super().__init__()
#         inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
#         self.register_buffer("inv_freq", inv_freq, persistent=False)
#         self.register_buffer("_cos_cached", None, persistent=False)
#         self.register_buffer("_sin_cached", None, persistent=False)

#     def _update_cache(self, seq_len, device, dtype):
#         if (self._cos_cached is None or
#             self._cos_cached.size(-2) < seq_len or
#             self._cos_cached.device != device or
#             self._cos_cached.dtype != dtype):
#             positions = torch.arange(seq_len, device=device, dtype=torch.float32)
#             freqs = torch.outer(positions, self.inv_freq.to(device))
#             emb = torch.cat((freqs, freqs), dim=-1)
#             self._cos_cached = emb.cos()[None, None, :, :].to(dtype)
#             self._sin_cached = emb.sin()[None, None, :, :].to(dtype)

#     def _rotate_half(self, x: torch.Tensor):
#         half_dim = x.shape[-1] // 2
#         return torch.cat((-x[..., half_dim:], x[..., :half_dim]), dim=-1)

#     def forward(self, q: torch.Tensor, k: torch.Tensor):
#         seq_len = q.size(-2)
#         self._update_cache(seq_len, q.device, q.dtype)
#         cos = self._cos_cached[:, :, :seq_len, :]
#         sin = self._sin_cached[:, :, :seq_len, :]
#         return (q * cos) + (self._rotate_half(q) * sin), (k * cos) + (self._rotate_half(k) * sin)

class RoPE(nn.Module):
    def __init__(self, head_dim: int, theta: float = 10000.0):
        super().__init__()
        inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2, dtype=torch.float32) / head_dim))
        self.register_buffer("inv_freq", inv_freq, persistent=False)
        self.register_buffer("_cos_cached", None, persistent=False)
        self.register_buffer("_sin_cached", None, persistent=False)

    def _update_cache(self, seq_len, device):
        if (self._cos_cached is None or self._cos_cached.size(-2) < seq_len
                or self._cos_cached.device != device):
            positions = torch.arange(seq_len, device=device, dtype=torch.float32)
            freqs = torch.outer(positions, self.inv_freq.to(device))
            emb = torch.cat((freqs, freqs), dim=-1)
            self._cos_cached = emb.cos()[None, None, :, :]
            self._sin_cached = emb.sin()[None, None, :, :]

    def _rotate_half(self, x):
        half = x.shape[-1] // 2
        return torch.cat((-x[..., half:], x[..., :half]), dim=-1)

    def forward(self, q, k):
        T = q.size(-2)
        self._update_cache(T, q.device)
        cos, sin = self._cos_cached[:, :, :T, :], self._sin_cached[:, :, :T, :]
        qf, kf = q.float(), k.float()
        q_out = qf * cos + self._rotate_half(qf) * sin
        k_out = kf * cos + self._rotate_half(kf) * sin
        return q_out.to(q.dtype), k_out.to(k.dtype)

class CausalAttention(nn.Module):
    def __init__(self, dim, num_heads, num_kv_heads=2, dropout=0.0):
        super().__init__()
        assert dim % num_heads == 0, f"dim ({dim}) must be divisible by num_heads ({num_heads})"
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = dim // num_heads
        self.queries_per_kv = num_heads // num_kv_heads

        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, self.num_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(dim, self.num_kv_heads * self.head_dim, bias=False)
        self.out_proj = nn.Linear(dim, dim, bias=False)
        self.rope = RoPE(self.head_dim)
        self.dropout = dropout

    def forward(self, x):
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)

        q, k = self.rope(q, k)

        if self.queries_per_kv > 1:
            k = k.unsqueeze(2).expand(B, self.num_kv_heads, self.queries_per_kv, T, self.head_dim).reshape(B, self.num_heads, T, self.head_dim)
            v = v.unsqueeze(2).expand(B, self.num_kv_heads, self.queries_per_kv, T, self.head_dim).reshape(B, self.num_heads, T, self.head_dim)

        y = F.scaled_dot_product_attention(
            q, k, v, is_causal=True,
            dropout_p=(self.dropout if self.training else 0.0)
        )
        return self.out_proj(y.transpose(1, 2).contiguous().view(B, T, C))


class SwiGLU(nn.Module):
    def __init__(self, dim, hidden_dim):
        super().__init__()
        self.w12 = nn.Linear(dim, 2 * hidden_dim, bias=False)
        self.down = nn.Linear(hidden_dim, dim, bias=False)

    def forward(self, x):
        x1, x2 = self.w12(x).chunk(2, dim=-1)
        gate = F.silu(x1.float()) * x2.float()
        # fp16 max ~65504 - clamp before casting back down to prevent the
        # overflow-to-inf failure mode that crashed the original run.
        gate = gate.clamp(-30000.0, 30000.0)
        return self.down(gate.to(dtype=x1.dtype))


class DecoderBlock(nn.Module):
    def __init__(self, dim, num_heads, num_kv_heads, ffn_dim, dropout=0.0):
        super().__init__()
        self.norm1 = RMSNorm(dim)
        self.attention = CausalAttention(dim=dim, num_heads=num_heads, num_kv_heads=num_kv_heads, dropout=dropout)
        self.norm2 = RMSNorm(dim)
        self.ffn = SwiGLU(dim, ffn_dim)

    def forward(self, x):
        x = x + self.attention(self.norm1(x))
        x = x + self.ffn(self.norm2(x))
        return x


class TinyLLM(nn.Module):
    def __init__(self, vocab_size, dim=config.DIM, num_heads=config.NUM_HEADS,
                 num_kv_heads=config.NUM_KV_HEADS, num_layers=config.NUM_LAYERS,
                 ffn_dim=config.FFN_DIM, dropout=config.DROPOUT):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, dim)
        self.blocks = nn.ModuleList([
            DecoderBlock(dim=dim, num_heads=num_heads, num_kv_heads=num_kv_heads,
                         ffn_dim=ffn_dim, dropout=dropout) for _ in range(num_layers)
        ])
        self.norm = RMSNorm(dim)
        self.lm_head = nn.Linear(dim, vocab_size, bias=False)

        self.apply(self._init_weights)
        for name, p in self.named_parameters():
            if name.endswith('out_proj.weight') or name.endswith('down.weight'):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * num_layers))
        self.lm_head.weight = self.embedding.weight

    @staticmethod
    def _init_weights(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, tokens, targets=None):
        x = self.embedding(tokens)
        for block in self.blocks:
            x = block(x)

        normed = self.norm(x)
        logits = F.linear(normed, self.lm_head.weight).float()     # fp16 matmul, fp32 result
        loss = None
        if targets is not None:
            with torch.autocast(device_type=x.device.type, enabled=False):
                loss = F.cross_entropy(logits.transpose(1, 2), targets, ignore_index=-100)
        return logits, loss


def parameters(model):
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f'\nTotal Parameters : {total / 1e6:.2f}M')
    print(f'Trainable parameters : {trainable / 1e6:.2f}M')
    return total


class TokenizerAdapter:
    def __init__(self, tokenizer_name):
        print(f"Loading tokenizer : {tokenizer_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, use_fast=True)

        if self.tokenizer.eos_token is None:
            self.tokenizer.add_special_tokens({"eos_token": "<|im_end|>"})
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.vocab_size = len(self.tokenizer)
        self.pad_token_id = self.tokenizer.pad_token_id
        self.eos_token_id = self.tokenizer.eos_token_id

        print(f"Vocabulary : {self.vocab_size}")
        print(f"PAD token  : {self.pad_token_id}")
        print(f"EOS token  : {self.eos_token_id}")

    @property
    def chat_template(self):
        return self.tokenizer.chat_template

    @property
    def is_fast(self):
        return self.tokenizer.is_fast

    def encode(self, text, **kwargs):
        return self.tokenizer.encode(text, **kwargs)

    def decode(self, tokens, **kwargs):
        return self.tokenizer.decode(tokens, **kwargs)

    def __call__(self, text, **kwargs):
        return self.tokenizer(text, **kwargs)

    def apply_chat_template(self, messages, **kwargs):
        return self.tokenizer.apply_chat_template(messages, **kwargs)

    def __len__(self):
        return self.vocab_size


class EarlyStopping:
    def __init__(self, patience, min_delta):
        self.patience = patience
        self.min_delta = min_delta
        self.best_loss = float("inf")
        self.counter = 0
        self.should_stop = False

    def step(self, val_loss):
        if val_loss < (self.best_loss - self.min_delta):
            self.best_loss = val_loss
            self.counter = 0
            return True
        self.counter += 1
        if self.counter >= self.patience:
            self.should_stop = True
        return False


def create_scheduler(optimizer, total_steps, warmup_ratio, min_lr_ratio):
    warmup_steps = int(total_steps * warmup_ratio)

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        cosine = 0.5 * (1 + math.cos(math.pi * progress))
        return min_lr_ratio + (1 - min_lr_ratio) * cosine

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def save_checkpoint(path, model, optimizer, scheduler, scaler, epoch, step, global_step, val_loss):
    model_state = model._orig_mod.state_dict() if hasattr(model, "_orig_mod") else model.state_dict()
    checkpoint = {
        "model_state_dict": model_state,
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "epoch": epoch,
        "step": step,
        "global_step": global_step,
        "val_loss": val_loss,
        "cpu_rng_state": torch.get_rng_state(),
        "cuda_rng_state": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
    }
    if scaler is not None:
        checkpoint["scaler_state_dict"] = scaler.state_dict()

    temp_path = path + ".tmp"
    torch.save(checkpoint, temp_path)
    os.replace(temp_path, path)


def load_checkpoint(path, model, optimizer=None, scheduler=None, scaler=None, is_finetuning=False):
    if not os.path.exists(path):
        return 0, 0, 0, float("inf")

    print(f"\n=> Loading checkpoint from: {path}...")
    checkpoint = torch.load(path, map_location=config.DEVICE, weights_only=False)
    state_dict = checkpoint["model_state_dict"] if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint else checkpoint

    target_model = model._orig_mod if hasattr(model, "_orig_mod") else model
    # strict=True on purpose: if pretrain.py and finetune.py architecture
    # constants in config.py ever drift apart, this fails loudly here
    # instead of silently loading a partially-matching state dict.
    target_model.load_state_dict(state_dict, strict=True)

    if not is_finetuning and isinstance(checkpoint, dict):
        if "optimizer_state_dict" in checkpoint and optimizer is not None:
            optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        if "scheduler_state_dict" in checkpoint and scheduler is not None:
            scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        if scaler is not None and checkpoint.get("scaler_state_dict") is not None:
            scaler.load_state_dict(checkpoint["scaler_state_dict"])

        epoch = checkpoint.get("epoch", 0)
        step = checkpoint.get("step", 0)
        global_step = checkpoint.get("global_step", 0)
        best_val_loss = checkpoint.get("val_loss", float("inf"))
        print(f"=> [RESUME] Epoch {epoch + 1}, Step {step} (Global Step {global_step})")
    else:
        epoch, step, global_step = 0, 0, 0
        best_val_loss = checkpoint.get("val_loss", float("inf")) if isinstance(checkpoint, dict) else float("inf")
        print("=> [NEW STAGE] Weights loaded, counters reset to step 0.")

    if isinstance(checkpoint, dict):
        if checkpoint.get("cpu_rng_state") is not None:
            try:
                torch.set_rng_state(checkpoint["cpu_rng_state"].to(torch.uint8))
            except Exception:
                pass
        if checkpoint.get("cuda_rng_state") is not None and torch.cuda.is_available():
            try:
                torch.cuda.set_rng_state_all(checkpoint["cuda_rng_state"])
            except Exception:
                pass

    return epoch, step, global_step, best_val_loss