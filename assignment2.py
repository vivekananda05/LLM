# -*- coding: utf-8 -*-
"""LLM_finetune

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/17SBy_sRr4KGvLlaiGKMI_idzzR6SRTAz
"""

pip install unsloth datasets trl transformers

import torch
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments
from unsloth.chat_templates import get_chat_template, standardize_sharegpt

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/llama-3.2-3b-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
)

tokenizer = get_chat_template(
    tokenizer,
    chat_template="llama-3.2"
)

dataset = load_dataset("mlabonne/FineTome-100k", split="train")

dataset = standardize_sharegpt(dataset)

dataset

dataset[0]

dataset = dataset.map(
    lambda x: {"text": tokenizer.apply_chat_template(x["conversations"], tokenize=False)},
    #remove_columns=["conversations"],
)

dataset

dataset[0]

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = 2048,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 100,
        max_steps = 60,
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        bf16 = torch.cuda.is_bf16_supported(),
        logging_steps = 1,
        output_dir = "outputs"
),
)

trainer.train()

model.save_pretrained("finetuned_model")

inference_model, inference_tokenizer = FastLanguageModel.from_pretrained(
    model_name="./finetuned_model",
    max_seq_length=2048,
    load_in_4bit=True
)

text_prompts = {
    "What are the key principles of investment"
}
for prompt in text_prompts:
  formatted_prompt = inference_tokenizer.apply_chat_template([{
      "role": "user",
      "content": prompt
  }], tokenize=False)
  inputs = inference_tokenizer(formatted_prompt, return_tensors="pt").to("cuda")
  outputs = inference_model.generate(**inputs, max_new_tokens=512,
                                     temperature=0.7,
                                     do_sample=True,
                                     pad_token_id=inference_tokenizer.pad_token_type_id
  )
  response = inference_tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
  print(f"Prompt: {prompt}\nResponse: {response}\n")

pip install evaluate

from evaluate import load

prompts = [
    "What are the key principles of investment"
]
references = [
    "The key principles of investment include diversification, long-term perspective, risk management, and understanding the market."
]
predictions = []

for prompt in prompts:
    formatted_prompt = inference_tokenizer.apply_chat_template([{
        "role": "user",
        "content": prompt
    }], tokenize=False)

    inputs = inference_tokenizer(formatted_prompt, return_tensors="pt").to("cuda")
    outputs = inference_model.generate(**inputs, max_new_tokens=512, temperature=0.7, do_sample=True)

    generated = inference_tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
    )
    predictions.append(generated)

bleu = load("bleu")
bleu_score = bleu.compute(predictions=predictions, references=[[ref] for ref in references])
print("BLEU Score:", bleu_score)