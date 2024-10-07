"""
Extract tags and special tokens from HF model tokenizer configs and chat templates.
"""

import json
from transformers import AutoTokenizer

# load model registry:
with open("model_registry.json", 'r', encoding='utf-8') as registry_file:
    registry = json.load(registry_file)

# print(registry)

base_token_names = ["_bos_token", "_eos_token", "_unk_token", "_sep_token", "_pad_token", "_cls_token", "_mask_token"]

tokenizer_data = dict()
for model_entry in registry:
    # if model_entry['backend'] == "huggingface_local":
    if model_entry['backend'] == "huggingface_local" and model_entry['model_name'] == "Qwen2.5-7B-Instruct":
        # print(model_entry)
        # get tokenizer:
        tokenizer = AutoTokenizer.from_pretrained(model_entry['huggingface_id'])
        # print(tokenizer)

        cur_tokenizer_data = dict()

        for attribute, value in tokenizer.__dict__.items():
            # print(attribute, ":", value)
            # get base special token set:
            if attribute in base_token_names:
                cur_tokenizer_data[attribute] = str(value)
            # get chat template:
            if attribute == "chat_template":
                cur_tokenizer_data['chat_template'] = value

        # print(cur_tokenizer_data)
        tokenizer_data[model_entry['model_name']] = cur_tokenizer_data
        break

strings_to_check = ["assistant", "im_end"]
# string_to_check = "assistant"

for model_name, cur_tokenizer_data in tokenizer_data.items():
    for attribute, value in cur_tokenizer_data.items():
        if attribute in base_token_names:
            for string_to_check in strings_to_check:
                if string_to_check in value:
                    print(f"{string_to_check} in {model_name} {attribute}!")
        if attribute == "chat_template":
            for string_to_check in strings_to_check:
                if string_to_check in value:
                    print(f"{string_to_check} in {model_name} chat template!")
