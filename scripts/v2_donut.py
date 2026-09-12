from __future__ import annotations

import argparse
import collections
import json
import re
import time
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
from v2_guard import assert_input_allowed

MODEL_ID = "naver-clova-ix/donut-base-finetuned-cord-v2"
REVISION = "8003d433113256b4ce3a0f5bf604b29ff78a7451"


def flatten(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    output=[]
    if isinstance(value, dict):
        for key,item in value.items(): output.extend(flatten(item,f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for item in value: output.extend(flatten(item,prefix))
    elif value is not None:
        text=re.sub(r"\s+"," ",str(value).strip().casefold())
        output.append((prefix,text))
    return output


def score(prediction: Any, truth: Any) -> tuple[int,int,int]:
    pred=collections.Counter(flatten(prediction)); gold=collections.Counter(flatten(truth))
    tp=sum((pred & gold).values()); return tp,sum(pred.values()),sum(gold.values())


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--limit",type=int,default=3); args=p.parse_args()
    assert_input_allowed(args.input)
    rows=[json.loads(x) for x in args.input.read_text().splitlines()[:args.limit]]
    torch.manual_seed(20260911); torch.cuda.reset_peak_memory_stats()
    started=time.perf_counter(); processor=DonutProcessor.from_pretrained(MODEL_ID,revision=REVISION)
    model=VisionEncoderDecoderModel.from_pretrained(MODEL_ID,revision=REVISION,torch_dtype=torch.float16).to("cuda").eval()
    load_seconds=time.perf_counter()-started; predictions=[]; timings=[]; totals=[0,0,0]
    task_prompt="<s_cord-v2>"
    decoder_input_ids=processor.tokenizer(task_prompt,add_special_tokens=False,return_tensors="pt").input_ids.to("cuda")
    for row in rows:
        image=Image.open(row["pages"][0]["image_path"]).convert("RGB")
        pixel_values=processor(image,return_tensors="pt").pixel_values.to("cuda",dtype=torch.float16)
        torch.cuda.synchronize(); t=time.perf_counter()
        with torch.inference_mode():
            output=model.generate(pixel_values,decoder_input_ids=decoder_input_ids,max_length=model.decoder.config.max_position_embeddings,
                early_stopping=True,pad_token_id=processor.tokenizer.pad_token_id,eos_token_id=processor.tokenizer.eos_token_id,
                use_cache=True,bad_words_ids=[[processor.tokenizer.unk_token_id]],return_dict_in_generate=True,output_scores=True)
        torch.cuda.synchronize(); timings.append(time.perf_counter()-t)
        sequence=processor.batch_decode(output.sequences)[0]
        sequence=sequence.replace(processor.tokenizer.eos_token,"").replace(processor.tokenizer.pad_token,"")
        sequence=re.sub(r"<.*?>","",sequence,count=1).strip()
        try: parsed=processor.token2json(sequence)
        except Exception: parsed={"_parse_failure":sequence}
        truth=row["ground_truth"].get("gt_parse",row["ground_truth"])
        values=score(parsed,truth); totals=[a+b for a,b in zip(totals,values)]
        transition=model.compute_transition_scores(output.sequences,output.scores,normalize_logits=True)[0]
        token_scores=transition[torch.isfinite(transition)]
        confidence=float(torch.exp(token_scores.mean()).cpu()) if len(token_scores) else 0.0
        doc_tp,doc_predicted,doc_gold=values
        doc_precision=doc_tp/doc_predicted if doc_predicted else 0
        doc_recall=doc_tp/doc_gold if doc_gold else 0
        predictions.append({"document_id":row["document_id"],"raw_sequence":sequence,"prediction":parsed,"truth":truth,
            "sequence_confidence":confidence,"schema_valid":not (isinstance(parsed,dict) and "_parse_failure" in parsed),
            "leaf_true_positive":doc_tp,"leaf_predicted":doc_predicted,"leaf_gold":doc_gold,
            "leaf_f1":2*doc_precision*doc_recall/(doc_precision+doc_recall) if doc_precision+doc_recall else 0,
            "latency_seconds":timings[-1]})
    tp,predicted,gold=totals; precision=tp/predicted if predicted else 0; recall=tp/gold if gold else 0
    split_name="official test" if "test" in args.input.name.casefold() else "validation"
    result={"experiment_id":"V2-E07","model":MODEL_ID,"revision":REVISION,"dataset":"CORD v2","split":split_name,
            "documents":len(rows),"device":torch.cuda.get_device_name(0),"physical_gpu_count":1,"precision":"FP16","batch_size":1,
            "load_seconds":load_seconds,"runtime_seconds":sum(timings),"latency_seconds":{"mean":sum(timings)/len(timings),"values":timings},
            "peak_vram_bytes":torch.cuda.max_memory_allocated(),"leaf_precision":precision,"leaf_recall":recall,
            "leaf_f1":2*precision*recall/(precision+recall) if precision+recall else 0,"true_positive_leaves":tp,"predicted_leaves":predicted,"gold_leaves":gold,
            "metric_definition":"Exact normalized (field-path, leaf-value) multiset; list row indices ignored.","predictions":predictions}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"predictions"}},sort_keys=True))


if __name__=="__main__": main()
