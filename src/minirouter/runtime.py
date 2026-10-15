"""Local quantized inference: recommendations only, no downstream execution."""
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from .contract import CAPABILITIES,Request,ToolCatalog,Prediction,Route
from .policy import CalculatorHandler,PolicyConfig,decide
from .tokenization import InputTooLong,prepare

ROUTES=tuple(route.value for route in Route)

def probabilities(primary,capabilities,calibration=None):
    spec=calibration or {}
    temperature=float(spec.get('primary_temperature',1.0))
    if not np.isfinite(temperature) or temperature<=0:raise ValueError('invalid calibration temperature')
    p=np.asarray(primary,dtype=np.float64).reshape(5)/temperature
    scales=np.asarray(spec.get('capability_scales',[1]*4),dtype=np.float64)
    biases=np.asarray(spec.get('capability_biases',[0]*4),dtype=np.float64)
    if scales.shape!=(4,) or biases.shape!=(4,) or not np.all(np.isfinite(scales)) or not np.all(np.isfinite(biases)):raise ValueError('invalid capability calibration')
    c=np.asarray(capabilities,dtype=np.float64).reshape(4)*scales+biases
    if not np.all(np.isfinite(p)) or not np.all(np.isfinite(c)):raise ValueError('model produced nonfinite logits')
    exp=np.exp(p-p.max());p=exp/exp.sum()
    c=1/(1+np.exp(-np.clip(c,-60,60)))
    return Prediction(dict(zip(ROUTES,map(float,p))),dict(zip(CAPABILITIES,map(float,c))))

class PinnedTokenizer:
    """Small tokenizers adapter compatible with the shared serializer."""
    def __init__(self,bundle:Path):
        self.tokenizer=Tokenizer.from_file(str(bundle/'tokenizer.json'))
        cfg=json.loads((bundle/'config.json').read_text())
        self.cls_token_id=cfg.get('cls_token_id',cfg.get('bos_token_id'))
        self.sep_token_id=cfg.get('sep_token_id',cfg.get('eos_token_id'))
        self.pad_token_id=cfg.get('pad_token_id')
    def encode(self,text,add_special_tokens=False):
        return self.tokenizer.encode(text,add_special_tokens=add_special_tokens).ids

class MiniRouter:
    def __init__(self,bundle:str|Path,*,threads:int=4):
        self.bundle=Path(bundle).resolve()
        if type(threads)is not int or not 1<=threads<=16:raise ValueError('threads must be between1 and16')
        manifest_path=self.bundle/'bundle_manifest.json'
        manifest=json.loads(manifest_path.read_text())
        expected={'bundle_manifest.json'}
        for item in manifest['files']:
            name=item['path']
            if not isinstance(name,str) or Path(name).name!=name or name in expected:raise ValueError('invalid bundle manifest path')
            expected.add(name);path=self.bundle/name
            if path.is_symlink() or not path.is_file():raise ValueError('bundle member missing or symlink')
            if path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('bundle integrity check failed: '+name)
        actual={p.name for p in self.bundle.iterdir()}
        if actual!=expected:raise ValueError('bundle has unaccounted or missing assets')
        self.bundle_bytes=sum(p.stat().st_size for p in self.bundle.iterdir())
        if self.bundle_bytes>15_000_000:raise ValueError('inference bundle exceeds15MB')
        self.config=json.loads((self.bundle/'router_config.json').read_text())
        if self.config.get('trained_router')is not True:raise ValueError('router heads are untrained; use a trained bundle')
        self.calibration=json.loads((self.bundle/'calibration.json').read_text())
        if self.calibration.get('status')=='calibrated':
            if self.calibration.get('model_sha256')!=hashlib.sha256((self.bundle/'model.onnx').read_bytes()).hexdigest():
                raise ValueError('calibration belongs to a different quantized model')
            if self.calibration.get('checkpoint_sha256')!=self.config.get('checkpoint_sha256'):
                raise ValueError('calibration checkpoint does not match this bundle')
        policy=json.loads((self.bundle/'policy.json').read_text())
        self.policy=PolicyConfig(**{k:policy[k] for k in ('min_confidence','min_margin','capability_threshold','max_tokens') if k in policy})
        self.tokenizer=PinnedTokenizer(self.bundle)
        options=ort.SessionOptions();options.intra_op_num_threads=threads;options.inter_op_num_threads=1;options.enable_mem_pattern=True
        self.session=ort.InferenceSession(str(self.bundle/'model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        if self.session.get_providers()!=['CPUExecutionProvider']:raise ValueError('unexpected inference provider')
    def route(self,text:str,*,context=(),available_capabilities=CAPABILITIES,calculator:bool=True,locale:str='en',context_complete:bool=True):
        started=time.perf_counter()
        if type(calculator)is not bool or type(context_complete)is not bool:raise ValueError('calculator and context_complete must be booleans')
        if not isinstance(context,(list,tuple)):raise ValueError('context must be a list or tuple of turns')
        request=Request(text,tuple(context),locale)
        catalog=ToolCatalog(frozenset(available_capabilities),{'calculator_v1':CalculatorHandler()} if calculator else {})
        try:prepared=prepare(request,catalog,self.tokenizer,max_tokens=self.policy.max_tokens)
        except InputTooLong as exc:
            return dict(status='abstain',route=None,abstain_reason='overlength',confidence=0.0,requires=[],token_count=None,context_truncated=False,detail=str(exc),latency_ms=(time.perf_counter()-started)*1000,calibration_status=self.calibration.get('status','uncalibrated'))
        logits=self.session.run(None,prepared.feed)
        prediction=probabilities(logits[0][0],logits[1][0],self.calibration)
        decision=decide(request,catalog,prediction,token_count=prepared.token_count,context_complete=context_complete,config=self.policy)
        return dict(status='route' if decision.route else 'abstain',route=decision.route.value if decision.route else None,abstain_reason=decision.abstain_reason.value if decision.abstain_reason else None,confidence=decision.confidence,requires=[name for name,value in decision.capability_flags.items() if value],eligible_handler=decision.eligible_handler,probabilities={key.value:value for key,value in prediction.route_probabilities.items()},capability_scores=dict(prediction.capability_scores),token_count=prepared.token_count,context_truncated=prepared.context_truncated,latency_ms=(time.perf_counter()-started)*1000,calibration_status=self.calibration.get('status','uncalibrated'))
