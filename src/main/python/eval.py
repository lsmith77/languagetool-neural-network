import sys
from ast import literal_eval
from typing import Callable, List

import numpy as np
from nltk import edit_distance

from EvalResult import EvalResult
from LayeredScorer import LayeredScorer
from parallel import parmap
from repl import has_error


def evaluate_ngrams(ngrams: [[str]], subjects: [str],
                    check_function: Callable[[List[str]], bool]) -> EvalResult:
    eval_result = EvalResult()
    substitutions = create_substitution_dict(subjects)
    for ngram in ngrams:
        middle = int(len(ngram) / 2)
        middle_word = ngram[middle]
        for substitution in substitutions[middle_word]:
            eval_ngram = ngram[:]
            eval_ngram[middle] = substitution
            error_detected = check_function(eval_ngram)
            if not error_detected and substitution == middle_word:
                eval_result.add_tn()
            elif error_detected and substitution == middle_word:
                eval_result.add_fp()
                print("false positive:", eval_ngram)
            elif not error_detected and substitution != middle_word:
                eval_result.add_fn()
            elif error_detected and substitution != middle_word:
                eval_result.add_tp()
    return eval_result


def get_relevant_ngrams(sentences: str, subjects: [str], n: int=5) -> [[str]]:
    ngrams = []
    half_context_length = int(n / 2)
    tokens = sentences.split(" ")
    for i in range(half_context_length, len(tokens) - half_context_length + 1):
        if tokens[i] in subjects:
            ngrams.append(tokens[i-half_context_length:i+half_context_length+1])
    return ngrams


def similar_words(word: str, words: List[str]):
    if len(word) < 4:
        max_distance = 1
    else:
        max_distance = 1
    return list(filter(lambda w: edit_distance(word, w, substitution_cost=1, transpositions=True) <= max_distance,
                       words))


def create_substitution_dict(subjects: List[str]) -> dict:
    return {subject: similar_words(subject, subjects) for subject in subjects}


def main():
    if len(sys.argv) != 4:
        raise ValueError("Expected dict, finalembedding, W, b")

    dictionary_path = sys.argv[1]
    embedding_path = sys.argv[2]
    weights_path = sys.argv[3]

    with open(dictionary_path) as dictionary_file:
        dictionary = literal_eval(dictionary_file.read())
    embedding = np.loadtxt(embedding_path)

    subjects = ["als", "also", "da", "das", "dass", "de", "den", "denn", "die", "durch", "zur", "ihm", "im", "um", "nach", "noch", "war", "was"]
    # subjects = ["and", "end", "as", "at", "is", "do", "for", "four", "form", "from", "he", "if", "is", "its", "it", "no", "now", "on", "one", "same", "some", "than", "that", "then", "their", "there", "them", "the", "they", "to", "was", "way", "were", "where"]
    print(subjects)

    # eval_subjects = subjects
    eval_subjects = ["das", "dass"]

    with open("/tmp/tokens-de") as file:
        sentences = file.read()

    scorer = LayeredScorer(weights_path)
    ngrams = get_relevant_ngrams(sentences, eval_subjects, n=scorer.context_size(embedding.shape[1])+1)

    eval_results = parmap(lambda t: evaluate_ngrams(ngrams, eval_subjects, lambda ngram: has_error(dictionary, embedding, scorer, ngram, subjects, error_threshold=t, suggestion_threshold=t)),
                          np.arange(0, 1, .025))
                          # [.3])
    print(eval_results)


if __name__ == '__main__':
    main()
