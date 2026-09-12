from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, Dataset
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor
from v2_guard import assert_input_allowed

MODEL_ID="microsoft/layoutlmv3-base"
REVISION="cfbbbff0762e6aab37086fdd4739ad14fe7d5db4"
LABELS=["O","B-HEADER","I-HEADER","B-QUESTION","I-QUESTION","B-ANSWER","I-ANSWER"]
LABEL2ID={name:i for i,name in enumerate(LABELS)}


def words_boxes_labels(record):
    with Image.open(record["pages"][0]["image_path"]) as image: width,height=image.size
    words=[]; boxes=[]; labels=[]
    for entity in record["ground_truth"]["form"]:
        category=entity["label"].upper()
        if category not in {"HEADER","QUESTION","ANSWER"}: category="O"
        for index,word in enumerate(entity.get("words",[])):
            text=word.get("text","").strip()
            if not text: continue
            x0,y0,x1,y1=word["box"]
            boxes.append([max(0,min(1000,round(1000*x0/width))),max(0,min(1000,round(1000*y0/height))),
                          max(0,min(1000,round(1000*x1/width))),max(0,min(1000,round(1000*y1/height)))])
            words.append(text)
            labels.append(LABEL2ID["O" if category=="O" else ("B-" if index==0 else "I-")+category])
    return words,boxes,labels


class FunsdDataset(Dataset):
    def __init__(self,records,processor): self.records=records; self.processor=processor
    def __len__(self): return len(self.records)
    def __getitem__(self,index):
        row=self.records[index]; words,boxes,labels=words_boxes_labels(row)
        image=Image.open(row["pages"][0]["image_path"]).convert("RGB")
        encoded=self.processor(image,words,boxes=boxes,word_labels=labels,padding="max_length",truncation=True,max_length=512,return_tensors="pt")
        return {k:v.squeeze(0) for k,v in encoded.items()}


def evaluate(model,loader):
    truth=[]; pred=[]; losses=[]; timings=[]
    model.eval()
    with torch.inference_mode():
        for batch in loader:
            batch={k:v.to("cuda",non_blocking=True) for k,v in batch.items()}; torch.cuda.synchronize(); t=time.perf_counter()
            output=model(**batch); torch.cuda.synchronize(); timings.append(time.perf_counter()-t); losses.append(float(output.loss))
            guess=output.logits.argmax(-1); mask=batch["labels"]!=-100
            truth.extend(batch["labels"][mask].cpu().tolist()); pred.extend(guess[mask].cpu().tolist())
    return {"loss":sum(losses)/len(losses),"token_accuracy":accuracy_score(truth,pred),"macro_f1":f1_score(truth,pred,labels=list(range(len(LABELS))),average="macro",zero_division=0),
            "latency_seconds":timings,"tokens":len(truth),"predictions":pred,"labels":truth}


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",type=Path,required=True); p.add_argument("--output",type=Path,required=True)
    p.add_argument("--max-train",type=int,default=120); p.add_argument("--max-dev",type=int,default=29); p.add_argument("--epochs",type=int,default=3); p.add_argument("--batch-size",type=int,default=2); args=p.parse_args()
    assert_input_allowed(args.input)
    rows=[json.loads(x) for x in args.input.read_text().splitlines()]; rng=random.Random(20260911); rng.shuffle(rows)
    train_rows=rows[:args.max_train]; dev_rows=rows[-args.max_dev:]
    torch.manual_seed(20260911); torch.cuda.manual_seed_all(20260911); torch.cuda.reset_peak_memory_stats()
    started=time.perf_counter(); processor=LayoutLMv3Processor.from_pretrained(MODEL_ID,revision=REVISION,apply_ocr=False)
    model=LayoutLMv3ForTokenClassification.from_pretrained(MODEL_ID,revision=REVISION,num_labels=len(LABELS),id2label=dict(enumerate(LABELS)),label2id=LABEL2ID).to("cuda")
    load_seconds=time.perf_counter()-started
    train_loader=DataLoader(FunsdDataset(train_rows,processor),batch_size=args.batch_size,shuffle=True,num_workers=2,pin_memory=True)
    dev_loader=DataLoader(FunsdDataset(dev_rows,processor),batch_size=args.batch_size,num_workers=2,pin_memory=True)
    optimizer=torch.optim.AdamW(model.parameters(),lr=3e-5,weight_decay=.01); scaler=torch.amp.GradScaler("cuda")
    epoch_losses=[]; train_started=time.perf_counter(); model.train()
    for _ in range(args.epochs):
        losses=[]
        for batch in train_loader:
            batch={k:v.to("cuda",non_blocking=True) for k,v in batch.items()}; optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda",dtype=torch.float16): output=model(**batch); loss=output.loss
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update(); losses.append(float(loss))
        epoch_losses.append(sum(losses)/len(losses))
    torch.cuda.synchronize(); train_seconds=time.perf_counter()-train_started
    metrics=evaluate(model,dev_loader)
    checkpoint=Path("/home/bjw-0/.local/share/rfdi-runtime/checkpoints/layoutlmv3-v2")
    checkpoint.mkdir(parents=True,exist_ok=True); model.save_pretrained(checkpoint,safe_serialization=True); processor.save_pretrained(checkpoint)
    result={"experiment_id":"V2-E06","model":MODEL_ID,"revision":REVISION,"dataset":"FUNSD","split":"deterministic train subset/dev holdout from official train",
            "train_documents":len(train_rows),"dev_documents":len(dev_rows),"seed":20260911,"device":torch.cuda.get_device_name(0),"physical_gpu_count":1,
            "precision":"FP16 autocast","batch_size":args.batch_size,"epochs":args.epochs,"learning_rate":3e-5,"load_seconds":load_seconds,"train_seconds":train_seconds,
            "epoch_losses":epoch_losses,"peak_vram_bytes":torch.cuda.max_memory_allocated(),"checkpoint":str(checkpoint),"metrics":metrics}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    summary={k:v for k,v in result.items() if k!="metrics"}; summary["metrics"]={k:v for k,v in metrics.items() if k not in {"predictions","labels","latency_seconds"}}; print(json.dumps(summary,sort_keys=True))


if __name__=="__main__": main()
