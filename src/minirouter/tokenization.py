"""Deterministic, bounded serialization shared by training and inference."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .contract import Request, ToolCatalog

class InputTooLong(ValueError):
    pass

@dataclass(frozen=True)
class PreparedInput:
    feed: dict[str, np.ndarray]
    token_count: int
    context_truncated: bool

def prepare(request: Request, catalog: ToolCatalog, tokenizer, *, max_tokens: int = 512) -> PreparedInput:
    if type(max_tokens) is not int or not 16 <= max_tokens <= 512:
        raise ValueError('max_tokens must be an integer between 16 and 512')
    def encode(text):
        return tokenizer.encode(text, add_special_tokens=False)
    cls = tokenizer.cls_token_id if tokenizer.cls_token_id is not None else tokenizer.bos_token_id
    sep = tokenizer.sep_token_id if tokenizer.sep_token_id is not None else tokenizer.eos_token_id
    if cls is None or sep is None:
        raise ValueError('pinned tokenizer must provide start and separator tokens')
    metadata = 'Available capabilities: ' + ', '.join(sorted(catalog.available_capabilities))
    metadata += '; deterministic handlers: ' + ', '.join(sorted(catalog.deterministic_handlers))
    meta_ids = encode(metadata)
    user_ids = encode(request.text)
    mandatory = 1 + len(meta_ids) + 1 + len(user_ids) + 1
    if mandatory > max_tokens:
        raise InputTooLong(f'Current request and trusted metadata need {mandatory} tokens; limit {max_tokens}')
    prefix = [cls] + meta_ids + [sep]
    history = encode('\n'.join(request.context[-2:])) if request.context else []
    history_budget = min(128, max(0, max_tokens - mandatory - 1))
    retained = history[-history_budget:] if history_budget else []
    if retained:
        prefix += retained + [sep]
    ids = prefix + user_ids + [sep]
    mask = [0] * len(prefix) + [1] * len(user_ids) + [0]
    feed = {'input_ids':np.asarray([ids],dtype=np.int64),
            'attention_mask':np.ones((1,len(ids)),dtype=np.int64),
            'request_mask':np.asarray([mask],dtype=np.int64)}
    return PreparedInput(feed,len(ids),len(history) != len(retained) or len(request.context)>2)
