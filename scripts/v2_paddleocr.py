from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import paddle
import paddleocr
from paddleocr import PaddleOCR
from v2_guard import assert_input_allowed


def edit_distance(a, b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1): current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]


def reference_text(truth):
    words=[]
    for line in truth.get("valid_line",[]):
        words.extend(word.get("text","") for word in line.get("words",[]) if word.get("text"))
    return " ".join(words)


def normalize(text): return re.sub(r"\s+"," ",text.strip().casefold())


def total_from_ocr(text):
    matches=re.findall(r"(?:grand\s+)?total\s*[:\-]?\s*(?:[a-z]{3}\s*)?([0-9][0-9., ]*)",text,re.I)
    return re.sub(r"[^0-9]","",matches[-1]) if matches else None


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--limit",type=int,default=100); args=p.parse_args()
    assert_input_allowed(args.input)
    rows=[json.loads(x) for x in args.input.read_text().splitlines()[:args.limit]]; paddle.seed(20260911)
    started=time.perf_counter(); ocr=PaddleOCR(device="gpu:0",text_detection_model_name="PP-OCRv5_server_det",text_recognition_model_name="PP-OCRv5_server_rec",use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False); load_seconds=time.perf_counter()-started
    predictions=[]; char_edits=char_total=word_edits=word_total=total_correct=total_count=0; timings=[]
    for row in rows:
        paddle.device.synchronize(); t=time.perf_counter(); result=list(ocr.predict(row["pages"][0]["image_path"])); paddle.device.synchronize(); timings.append(time.perf_counter()-t)
        payload=result[0].json["res"]; predicted=" ".join(text for text in payload["rec_texts"] if text); reference=reference_text(row["ground_truth"])
        pa,ra=normalize(predicted),normalize(reference); pw,rw=pa.split(),ra.split()
        char_edits+=edit_distance(pa,ra); char_total+=len(ra); word_edits+=edit_distance(pw,rw); word_total+=len(rw)
        target=row["ground_truth"].get("gt_parse",{}).get("total",{}).get("total_price")
        guess=total_from_ocr(predicted)
        if target is not None: total_count+=1; total_correct+=guess==re.sub(r"[^0-9]","",target)
        predictions.append({"document_id":row["document_id"],"text":predicted,"reference":reference,"mean_confidence":sum(payload["rec_scores"])/len(payload["rec_scores"]) if payload["rec_scores"] else 0,"total_prediction":guess,"total_truth":target,"latency_seconds":timings[-1]})
    split_name="official test" if "test" in args.input.name.casefold() else "validation"
    result={"experiment_id":"V2-E04","ocr_model":"PP-OCRv5_server_det+PP-OCRv5_server_rec","model_revisions":{"PP-OCRv5_server_det":"ca867c897ecbca8873081573a802ad70d499cb94","PP-OCRv5_server_rec":"b26c3587fda8da3c8ec0ce357214b4d661ff1558"},"paddleocr":paddleocr.__version__,"paddle":paddle.__version__,"dataset":"CORD v2","split":split_name,"documents":len(rows),
            "device":paddle.device.cuda.get_device_name(),"physical_gpu_count":1,"precision":"framework default FP32","batch_size":1,"load_seconds":load_seconds,"runtime_seconds":sum(timings),
            "latency_seconds":{"mean":sum(timings)/len(timings),"values":timings},"peak_vram_bytes":paddle.device.cuda.max_memory_allocated(),"cer":char_edits/char_total,"wer":word_edits/word_total,
            "downstream_total_exact_match":total_correct/total_count if total_count else None,"total_evaluated":total_count,"predictions":predictions}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n"); print(json.dumps({k:v for k,v in result.items() if k!="predictions"},sort_keys=True))


if __name__=="__main__": main()
