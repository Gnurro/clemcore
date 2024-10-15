"""
Extract tags and special tokens from HF model tokenizer configs and chat templates.
"""

import json
import os.path
from transformers import AutoTokenizer
import backends

# load model registry:
with open("model_registry.json", 'r', encoding='utf-8') as registry_file:
    registry = json.load(registry_file)

# check for custom model registry:
if os.path.isfile("model_registry_custom.json"):
    # load custom model registry:
    with open("model_registry.json_custom", 'r', encoding='utf-8') as registry_custom_file:
        registry_custom = json.load(registry_custom_file)
    # append custom model registry to base registry:
    registry.append(registry_custom)

# load HF API key:
creds = backends.load_credentials("huggingface")
api_key = creds["huggingface"]["api_key"]

base_token_names = ["_bos_token", "_eos_token", "_unk_token", "_sep_token", "_pad_token", "_cls_token", "_mask_token"]

tokenizer_data = dict()
for model_entry in registry:
    if model_entry['backend'] == "huggingface_local":
        # get tokenizer:
        if 'requires_api_key' in model_entry and model_entry['requires_api_key']:
            tokenizer = AutoTokenizer.from_pretrained(model_entry['huggingface_id'], token=api_key)
        else:
            tokenizer = AutoTokenizer.from_pretrained(model_entry['huggingface_id'])

        cur_tokenizer_data = dict()

        for attribute, value in tokenizer.__dict__.items():
            # get base special token set:
            if attribute in base_token_names:
                cur_tokenizer_data[attribute] = str(value)

            # get chat template:
            if attribute == "chat_template":
                if value:
                    cur_tokenizer_data['chat_template'] = value
                else:
                    print(f"No tokenizer chat template found for {model_entry['model_name']}")
                    print(f"Using model registry custom chat template: {model_entry['custom_chat_template']}")
                    cur_tokenizer_data['chat_template'] = model_entry['custom_chat_template']

            # get additional special tokens:
            if attribute == "_additional_special_tokens":
                cur_tokenizer_data['additional_special_tokens'] = value

        tokenizer_data[model_entry['model_name']] = cur_tokenizer_data

# save tag database:
with open("tag_database.json", 'w', encoding='utf-8') as tag_database_file:
    json.dump(tokenizer_data, tag_database_file, indent=2)

"""
strings_to_check = ["assistant", "im_end"]

# TODO: add argumentParser to make this usable via cli?

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

"""
