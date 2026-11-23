import asyncio
import threading
import torch
import torch.nn.functional as F
from llm import config
from llm.model import TinyLLM,TokenizerAdapter

SYSTEM_PROMPT = (
    "You are a helpful assistant. Solve simple problems step by step. "
    "If a question is beyond your ability, say so honestly."
)


def _seg(role: str, content: str) -> str:
    return f"<|im_start|>{role}\n{content}<|im_end|>\n"

def banned_ngram_tokens(ids,n):
    if n < 2 or len(ids) < n - 1:
        return set()
    prefix = tuple(ids[-(n - 1):])
    return {ids[i + n - 1] for i in range(len(ids) - n + 1) if tuple(ids[i : i + n - 1]) == prefix}

class Engine:
    def __init__(self):
        self.model = None
        self.tok = None
        self._lock = None
        self.waiting = 0

    def load(self,weights_path:str):
        self.device = config.DEVICE
        self.tok = TokenizerAdapter(config.TOKENIZER_NAME)
        self.model = TinyLLM(vocab_size=self.tok.vocab_size)

        sd = torch.load(weights_path,map_location='cpu',weights_only=True)
        self.model.load_state_dict(sd,strict=True)
        self.model.to(self.device).eval()

        if self.device.type == "cuda":
            bf16 = torch.cuda.get_device_capability()[0] >= 8
            self.amp_dtype = torch.bfloat16 if bf16 else torch.float16
        else:
            self.amp_dtype = None

        enc = lambda s: self.tok.encode(s,add_special_tokens=False) 
        self.im_end_id = enc("<|im_end|>")[0]
        self.stop_ids = {self.tok.eos_token_id, self.im_end_id}
        self.sys_ids = enc(_seg("system", SYSTEM_PROMPT))
        self.tail_ids = enc("<|im_start|>assistant\n")
        self._lock = asyncio.Lock()
        print(f"Engine ready on {self.device}")

    def build_prompt(self,history:list[dict],max_new:int) -> list[int]:
        enc = lambda s: self.tok.encode(s, add_special_tokens=False)
        budget = (config.MAX_SEQ_LEN - 1) - max_new - len(self.sys_ids) - len(self.tail_ids)

        kept , used = [] ,0
        for m in reversed(history):
            if m['role'] not in ("user", "assistant"):
                continue
            content = m['content']
            ids = enc(_seg(m['role'],content))
            if not kept and len(ids) > budget:
                while len(ids) > budget and content:
                    content = content[max(1, len(content) // 5):]
                    ids = enc(_seg(m["role"], content))
            if used + len(ids) > budget:
                break
            kept.append((m["role"], ids))
            used += len(ids)

        kept.reverse()
        while kept and kept[0][0] != "user":
            kept.pop(0)

        out = list(self.sys_ids)
        for _, ids in kept:
            out += ids
        return out + self.tail_ids

    @staticmethod
    def _sample(logits,gen_ids,temperature,top_k,top_p,rep_pen,banned=None):
        if rep_pen and rep_pen != 1.0 and gen_ids:
            idx = torch.tensor(list(set(gen_ids)),device=logits.device)
            v = logits[idx]
            logits[idx] = torch.where(v > 0,v / rep_pen, v * rep_pen)

        if banned:
            logits[torch.tensor(list(banned), device=logits.device)] = float("-inf")
    
        if temperature <= 0:
            return int(logits.argmax())
        logits = logits / temperature
        if top_k and top_k < logits.numel():
            kth = torch.topk(logits, top_k).values[-1]
            logits = logits.masked_fill(logits < kth, float("-inf"))
        if top_p and top_p < 1.0:
            sl, si = torch.sort(logits, descending=True)
            p = sl.softmax(-1)
            sl = sl.masked_fill(p.cumsum(-1) - p > top_p, float("-inf"))
            logits = torch.full_like(logits, float("-inf")).scatter(0, si, sl)
        return int(torch.multinomial(logits.softmax(-1), 1))

    @torch.inference_mode()
    def _generate(self, history, stop: threading.Event, max_new, temperature, top_k, top_p, rep_pen):
        m = self.model
        ids = self.build_prompt(history, max_new)
        out, raw_prev, started = [], "", False

        for _ in range(max_new):
            if stop.is_set():
                return
            x = torch.tensor([ids[-(config.MAX_SEQ_LEN - 1):]], device=self.device)
            with torch.autocast(self.device.type, dtype=self.amp_dtype or torch.float32,
                                enabled=self.amp_dtype is not None):
                h = m.embedding(x)
                for block in m.blocks:
                    h = block(h)
                h = m.norm(h[:, -1:, :])
                logits = F.linear(h, m.lm_head.weight).float()[0, -1]

            banned = banned_ngram_tokens(out, getattr(config, "NO_REPEAT_NGRAM_SIZE", 0))
            nxt = self._sample(logits, out, temperature, top_k, top_p, rep_pen, banned)
            if nxt in self.stop_ids:
                return
            ids.append(nxt)
            out.append(nxt)

            text = self.tok.decode(out, skip_special_tokens=True)
            if text.endswith("\ufffd"):
                continue
            piece = text[len(raw_prev):]
            raw_prev = text
            if not started:
                piece = piece.lstrip()
                if not piece:
                    continue
                started = True
            if piece:
                yield piece

    async def stream(self, history, max_new=None, temperature=None, top_k=None,top_p=None, rep_pen=None):
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        history = history[-getattr(config, "MAX_HISTORY_MESSAGES", 7):]
        kw = dict(
            max_new=max_new or config.MAX_NEW_TOKENS,
            temperature=config.TEMPERATURE if temperature is None else temperature,
            top_k=config.TOP_K if top_k is None else top_k,
            top_p=config.TOP_P if top_p is None else top_p,
            rep_pen=config.REPETITION_PENALTY if rep_pen is None else rep_pen,
        )
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        stop = threading.Event()
        DONE = object()

        def worker():
            try:
                for piece in self._generate(history, stop, **kw):
                    loop.call_soon_threadsafe(q.put_nowait, piece)
            except Exception as e:
                loop.call_soon_threadsafe(q.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, DONE)

        self.waiting += 1
        try:
            async with self._lock:
                fut = loop.run_in_executor(None, worker)
                try:
                    while True:
                        item = await q.get()
                        if item is DONE:
                            break
                        if isinstance(item, Exception):
                            raise item
                        yield item
                finally:
                    stop.set()
                    await asyncio.shield(fut)
        finally:
            self.waiting -= 1
            
    def busy(self) -> bool:
        return self.waiting >= getattr(config, "MAX_QUEUE", 4)


engine = Engine()