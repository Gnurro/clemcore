""" Backend for multimodal/image+text models from HuggingFace (based on huggingface_local_api) """

from typing import List, Dict, Tuple, Any
import torch
import backends

import requests

import PIL
from PIL import Image

import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoProcessor, AutoModelForVision2Seq
import os
import copy

logger = backends.get_logger(__name__)

MODEL_BLIP2_OPT_2_7B = "blip2-opt-2.7b"


SUPPORTED_MODELS = [MODEL_BLIP2_OPT_2_7B]


PROCESSOR_REQUIRED = [MODEL_BLIP2_OPT_2_7B]


PREMADE_CHAT_TEMPLATE = []

SLOW_TOKENIZER = []


TEST_IMAGE = "https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg"


def load_image_from_url(img_url: str, convert_to: str = 'RGB', verbose: bool = True) -> Image:
    raw_image = Image.open(requests.get(img_url, stream=True).raw).convert(convert_to)
    if verbose:
        print(f"Loaded image from URL {img_url}")
    return raw_image


def load_image_from_disk(img_path: str, convert_to: str = 'RGB') -> Image:
    raw_image = Image.open(img_path).convert(convert_to)
    return raw_image


class HuggingfaceMultimodalLocal(backends.Backend):
    def __init__(self):
        self.temperature: float = -1.
        self.model_loaded = False

    def load_model(self, model_name):
        logger.info(f'Start loading huggingface model: {model_name}')

        # model cache handling
        root_data_path = os.path.join(os.path.abspath(os.sep), "data")
        # check if root/data exists:
        if not os.path.isdir(root_data_path):
            logger.info(f"{root_data_path} does not exist, creating directory.")
            # create root/data:
            os.mkdir(root_data_path)
        CACHE_DIR = os.path.join(root_data_path, "huggingface_cache")

        if model_name in [MODEL_BLIP2_OPT_2_7B]:  # Salesforce models
            hf_user_prefix = "Salesforce/"

        hf_model_str = f"{hf_user_prefix}{model_name}"

        # use 'slow' tokenizer for models that require it:
        if model_name in SLOW_TOKENIZER:
            self.tokenizer = AutoTokenizer.from_pretrained(hf_model_str, device_map="auto", torch_dtype="auto",
                                                           cache_dir=CACHE_DIR, verbose=False, use_fast=False)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(hf_model_str, device_map="auto", torch_dtype="auto",
                                                           cache_dir=CACHE_DIR, verbose=False)

        # apply proper chat template:
        if model_name not in PREMADE_CHAT_TEMPLATE:
            pass

        self.processor = None
        # load processor for models that require it:
        if model_name in PROCESSOR_REQUIRED:
            self.processor = AutoProcessor.from_pretrained(hf_model_str)

        # load all models using their default configuration:
        # self.model = AutoModelForCausalLM.from_pretrained(hf_model_str, device_map="auto", torch_dtype="auto",
        #                                                  cache_dir=CACHE_DIR)
        self.model = AutoModelForVision2Seq.from_pretrained(hf_model_str, device_map="auto", torch_dtype="auto",
                                                            cache_dir=CACHE_DIR)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.model_loaded = True

    def generate_response(self, messages: List[Dict], model: str,
                          max_new_tokens: int = 100, return_full_text: bool = False) -> Tuple[Any, Any, str]:
        """
        :param messages: for example
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Who won the world series in 2020?"},
                    {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
                    {"role": "user", "content": "Where was it played?"}
                ]
        :param model: model name
        :param max_new_tokens: How many tokens to generate ('at most', but no stop sequence is defined).
        :param return_full_text: If True, whole input context is returned.
        :return: the continuation
        """
        assert 0.0 <= self.temperature <= 1.0, "Temperature must be in [0.,1.]"

        # load the model to the memory
        if not self.model_loaded:
            self.load_model(model)
            logger.info(f"Finished loading huggingface model: {model}")
            logger.info(f"Model device map: {self.model.hf_device_map}")

        # log current given messages list:
        # logger.info(f"Raw messages passed: {messages}")

        # deepcopy messages to prevent reference issues:
        current_messages = copy.deepcopy(messages)

        # cull empty system message:
        if current_messages[0]['role'] == "system":
            if not current_messages[0]['content']:
                del current_messages[0]

        # flatten consecutive user messages:
        for msg_idx, message in enumerate(current_messages):
            if msg_idx > 0 and message['role'] == "user" and current_messages[msg_idx - 1]['role'] == "user":
                current_messages[msg_idx - 1]['content'] += f" {message['content']}"
                del current_messages[msg_idx]
            elif msg_idx > 0 and message['role'] == "assistant" and current_messages[msg_idx - 1]['role'] == "assistant":
                current_messages[msg_idx - 1]['content'] += f" {message['content']}"
                del current_messages[msg_idx]

        # log current flattened messages list:
        # logger.info(f"Flattened messages: {current_messages}")

        # apply chat template & tokenize:
        prompt_tokens = self.tokenizer.apply_chat_template(current_messages, return_tensors="pt")
        prompt_tokens = prompt_tokens.to(self.device)

        prompt_text = self.tokenizer.batch_decode(prompt_tokens)[0]
        prompt = {"inputs": prompt_text, "max_new_tokens": max_new_tokens,
                  "temperature": self.temperature, "return_full_text": return_full_text}

        print("Prompt text:", prompt_text)

        # load and process image into multimodal input:
        input_img = None
        if not input_img:
            input_img = load_image_from_url(TEST_IMAGE)
        if self.processor:
            inputs = self.processor(input_img, prompt_text, return_tensors="pt").to(self.device)

        print("Input:", inputs)

        # greedy decoding:
        do_sample: bool = False
        if self.temperature > 0.0:
            do_sample = True

        # test to check if temperature is properly set on this Backend object:
        # logger.info(f"Currently used temperature for this instance of HuggingfaceLocal: {self.temperature}")

        if do_sample:
            model_output_ids = self.model.generate(
                **inputs,
                temperature=self.temperature,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample
            )
        else:
            model_output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample
            )

        # model_output = self.tokenizer.batch_decode(model_output_ids)[0]

        model_output = self.processor.decode(model_output_ids[0])

        response = {'response': model_output}

        # cull input context; equivalent to transformers.pipeline method:
        if not return_full_text:
            response_text = model_output.replace(prompt_text, '').strip()

            # remove llama2 EOS token at the end of output:
            if response_text[-4:len(response_text)] == "</s>":
                response_text = response_text[:-4]

        else:
            response_text = model_output.strip()

        return prompt, response, response_text

    def supports(self, model_name: str):
        return model_name in SUPPORTED_MODELS


if __name__ == "__main__":
    test_messages = [
        {"role": "user", "content": "How many dogs are in the picture?"},
    ]

    test_backend = HuggingfaceMultimodalLocal()
    test_backend.temperature = 0.0

    test_output = test_backend.generate_response(test_messages, "blip2-opt-2.7b")
    print(test_output)
