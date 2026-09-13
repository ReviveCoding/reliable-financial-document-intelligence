from __future__ import annotations

import json
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel


MODEL = "naver-clova-ix/donut-base-finetuned-cord-v2"
REVISION = "8003d433113256b4ce3a0f5bf604b29ff78a7451"
processor = DonutProcessor.from_pretrained(MODEL, revision=REVISION)
model = VisionEncoderDecoderModel.from_pretrained(MODEL, revision=REVISION, torch_dtype=torch.float16).to("cuda").eval()
decoder_ids = processor.tokenizer("<s_cord-v2>", add_special_tokens=False, return_tensors="pt").input_ids.to("cuda")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/health": self.send_error(404); return
        self.respond({"status": "ok", "model": MODEL, "revision": REVISION, "device": torch.cuda.get_device_name(0)})

    def do_POST(self) -> None:
        if self.path != "/extract": self.send_error(404); return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        image = Image.open(payload["image_path"]).convert("RGB")
        pixels = processor(image, return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        torch.cuda.synchronize(); started = time.perf_counter()
        with torch.inference_mode():
            output = model.generate(pixels, decoder_input_ids=decoder_ids, max_length=model.decoder.config.max_position_embeddings, early_stopping=True, pad_token_id=processor.tokenizer.pad_token_id, eos_token_id=processor.tokenizer.eos_token_id, use_cache=True, bad_words_ids=[[processor.tokenizer.unk_token_id]], return_dict_in_generate=True, output_scores=True)
        torch.cuda.synchronize(); latency = time.perf_counter() - started
        sequence = processor.batch_decode(output.sequences)[0].replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()
        prediction = processor.token2json(sequence)
        scores = model.compute_transition_scores(output.sequences, output.scores, normalize_logits=True)[0]
        finite = scores[torch.isfinite(scores)]
        confidence = float(torch.exp(finite.mean()).cpu()) if len(finite) else 0.0
        self.respond({"prediction": prediction, "confidence": confidence, "inference_seconds": latency})

    def log_message(self, *_: object) -> None: pass

    def respond(self, payload: dict) -> None:
        body = json.dumps(payload).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8120), Handler).serve_forever()
