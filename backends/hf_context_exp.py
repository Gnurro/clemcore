"""Experimenting with dialog and context handling."""

from typing import List, Dict, Tuple
from transformers import AutoConfig, AutoTokenizer

FALLBACK_CONTEXT_SIZE = 512


class DialogContextHandler:
    """
    Demo standalone class for HF transformers context checking.
    This class's functionality can be integrated into huggingface_local_api and llama2_hf_local_api.
    """
    def __init__(self, model_id: str):
        self.model_config = AutoConfig.from_pretrained(model_id)  # can be accessed as AutoModel.config
        if hasattr(self.model_config, 'max_position_embeddings'):  # this is the standard attribute used by most
            self.context_size = self.model_config.max_position_embeddings
        elif hasattr(self.model_config, 'n_positions'):  # some models may have their context size under this attribute
            self.context_size = self.model_config.n_positions
        else:  # few models, especially older ones, might not have their context size in the config
            self.context_size = FALLBACK_CONTEXT_SIZE
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, verbose=False)

    def check_context(self, messages: List[Dict], max_new_tokens: int = 100) -> Tuple[bool, int, int, int]:
        """
        Checks context for context token limit fit.
        :param messages: for example
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Who won the world series in 2020?"},
                    {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
                    {"role": "user", "content": "Where was it played?"}
                ]
        :param max_new_tokens: How many tokens to generate ('at most', but no stop sequence is defined).
        :return: Tuple with
                Bool: True if context limit is not exceeded, False if too many tokens
                Number of tokens for the given messages and maximum new tokens
                Number of tokens of 'context space left'
                Total context token limit
        """
        prompt_tokens = self.tokenizer.apply_chat_template(messages)  # the actual tokens, including chat format
        prompt_size = len(prompt_tokens)
        tokens_used = prompt_size + max_new_tokens  # context includes tokens to be generated
        tokens_left = self.context_size - tokens_used
        print(f"{tokens_used} input tokens, {tokens_left}/{self.context_size} tokens left.")
        fits = tokens_used <= self.context_size
        return fits, tokens_used, tokens_left, self.context_size


if __name__ == "__main__":
    # tester = DialogContextHandler("HuggingFaceH4/zephyr-7b-alpha")
    tester = DialogContextHandler("TheBloke/koala-13B-HF")

    test_messages1 = [
        {"role": "user", "content": "What is your favourite condiment?"},
        {"role": "assistant", "content": "Lard!"},
        {"role": "user", "content": "Do you have mayonnaise recipes?"}
    ]

    print(tester.check_context(test_messages1))

    test_messages2 = []

    for i in range(100):
        test_messages2.append({"role": "user", "content": "What is your favourite condiment?"})
        test_messages2.append({"role": "assistant", "content": "Lard!"})

    print(tester.check_context(test_messages2))
