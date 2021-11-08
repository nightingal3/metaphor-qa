import argparse
import logging
from typing import Optional
from glob import glob

import transformers
from transformers import (
    CONFIG_MAPPING,
    MODEL_WITH_LM_HEAD_MAPPING,
    AutoConfig,
    AutoModelWithLMHead,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    DataCollatorForPermutationLanguageModeling,
    DataCollatorForWholeWordMask,
    HfArgumentParser,
    LineByLineTextDataset,
    LineByLineWithRefDataset,
    PreTrainedTokenizer,
    TextDataset,
    Trainer,
    TrainingArguments,
    set_seed,
)
from torch.utils.data import ConcatDataset
import pdb

from gpt_score import model_init

logger = logging.getLogger(__name__)

def main(model_name: str, train_path: str, num_epochs: int, seed: int, use_cuda: bool, cache_dir: str = "./lm_train_cache/") -> None:
    # Set up models, random seed, and logging
    model_names = {"gpt2": "gpt2", "neo-sm": "EleutherAI/gpt-neo-1.3B", "neo-lg": "EleutherAI/gpt-neo-2.7B"}
    model_id = model_names[model_name]
    model, tokenizer = model_init(model_name, use_cuda)
    #model.resize_token_embeddings(len(tokenizer))
    set_seed(seed)
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S",
        level=logging.INFO,
    )
    transformers.utils.logging.set_verbosity_info()
    transformers.utils.logging.enable_default_handler()
    transformers.utils.logging.enable_explicit_format()
    logger.info("Training/evaluation parameters %s", locals())

    # load datasets and initialize trainer
    train_dataset = (
        get_dataset("./lm_train_data/test.txt", tokenizer=tokenizer, cache_dir=cache_dir)
    )
    data_collator = DataCollatorForLanguageModeling(
                tokenizer=tokenizer, mlm=False
            )
    training_args = { #TODO: make other training args customizable
        "output_dir": f"./lm_train_outputs/{model}/",
        "do_train": True,
        "prediction_loss_only": True,
        "per_device_batch_size": 8,
        "num_train_epochs": num_epochs,
        "seed": seed
    }
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=train_dataset
    )

    # Train the model
    trainer.train()
    trainer.save_model("./lm_train_cache/")
    pdb.set_trace()

# This is adapted from the huggingface LM training example here: https://github.com/huggingface/transformers/blob/master/examples/legacy/run_language_modeling.py
def get_dataset(
    train_data_file: str,
    tokenizer: PreTrainedTokenizer,
    line_by_line: bool = True,
    evaluate: bool = False,
    eval_data_file: str = None,
    cache_dir: Optional[str] = None,
):
    def _dataset(file_path, ref_path=None):
        if line_by_line:
            if ref_path is not None:
                if not args.whole_word_mask or not args.mlm:
                    raise ValueError("You need to set world whole masking and mlm to True for Chinese Whole Word Mask")
                return LineByLineWithRefDataset(
                    tokenizer=tokenizer,
                    file_path=file_path,
                    block_size=args.block_size,
                    ref_path=ref_path,
                )

            return LineByLineTextDataset(tokenizer=tokenizer, file_path=file_path, block_size=-1)

    if evaluate:
        return _dataset(eval_data_file)
    else:
        return _dataset(train_data_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train models with the causal language modelling objective (GPT-*)")
    #TODO: add ability to load a pretrained model and just evaluate it
    parser.add_argument("model", choices=["gpt2", "gpt-neo-sm", "gpt-neo-lg"]) 
    parser.add_argument("-t", "--train_path", default="./filtered_data/processed.csv")
    parser.add_argument("-e", "--eval_path", type=str)
    parser.add_argument("-s", "--seed", default=42, type=int)
    parser.add_argument("-c", "--cuda", default=False, action="store_true")
    parser.add_argument("--num_epochs", default=3, type=int)
    args = parser.parse_args()
    main(args.model, args.train_path, args.num_epochs, args.seed, args.cuda)