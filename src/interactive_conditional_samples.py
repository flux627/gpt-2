#!/usr/bin/env python3

import fire
import json
import os
import requests
import numpy as np
import tensorflow as tf

import model, sample, encoder

def interact_model(
    model_name='117M',
    seed=None,
    nsamples=1,
    batch_size=1,
    length=None,
    temperature=1,
    top_k=0,
    top_p=0.0,
    prompt_url=None,
    author='Alan Watts'
):
    """
    Interactively run the model
    :model_name=117M : String, which model to use
    :seed=None : Integer seed for random number generators, fix seed to reproduce
     results
    :nsamples=1 : Number of samples to return total
    :batch_size=1 : Number of batches (only affects speed/memory).  Must divide nsamples.
    :length=None : Number of tokens in generated text, if None (default), is
     determined by model hyperparameters
    :temperature=1 : Float value controlling randomness in boltzmann
     distribution. Lower temperature results in less random completions. As the
     temperature approaches zero, the model will become deterministic and
     repetitive. Higher temperature results in more random completions.
    :top_k=0 : Integer value controlling diversity. 1 means only 1 word is
     considered for each step (token), resulting in deterministic completions,
     while 40 means 40 words are considered at each step. 0 (default) is a
     special setting meaning no restrictions. 40 generally is a good value.
    :top_p=0.0 : Float value controlling diversity. Implements nucleus sampling,
     overriding top_k if set to a value > 0. A good setting is 0.9.
    """
    if batch_size is None:
        batch_size = 1
    assert nsamples % batch_size == 0

    enc = encoder.get_encoder(model_name)
    hparams = model.default_hparams()
    with open(os.path.join('models', model_name, 'hparams.json')) as f:
        hparams.override_from_dict(json.load(f))

    if length is None:
        length = hparams.n_ctx // 2
    elif length > hparams.n_ctx:
        raise ValueError("Can't get samples longer than window size: %s" % hparams.n_ctx)

    with tf.Session(graph=tf.Graph()) as sess:
        context = tf.placeholder(tf.int32, [batch_size, None])
        np.random.seed(seed)
        tf.set_random_seed(seed)
        output = sample.sample_sequence(
            hparams=hparams, length=length,
            context=context,
            batch_size=batch_size,
            temperature=temperature, top_k=top_k, top_p=top_p
        )

        saver = tf.train.Saver()
        ckpt = tf.train.latest_checkpoint(os.path.join('models', model_name))
        saver.restore(sess, ckpt)

        if prompt_url:
            r = requests.get(prompt_url)
            prompt = r.text
            batches = get_batches(prompt, enc, nsamples, batch_size, sess, output)
            quotes = []
            for batch in batches:
                quotes.extend(find_quotes(batch))
            for quote in quotes:
                print(quote)
            return

        while True:
            raw_text = input("Model prompt >>> ")
            while not raw_text:
                print('Prompt should not be empty!')
                raw_text = input("Model prompt >>> ")
            batches = get_batches(prompt, enc, nsamples, batch_size, sess, output)
            quotes = []
            for batch in batches:
                quotes.extend(find_quotes(batch))
            for quote in quotes:
                print(quote)

def get_batches(prompt, enc, nsamples, batch_size, sess, output):
    context_tokens = enc.encode(prompt)
    generated = 0
    for _ in range(nsamples // batch_size):
        out = sess.run(output, feed_dict={
            context: [context_tokens for _ in range(batch_size)]
        })[:, len(context_tokens):]
        batches = []
        for i in range(batch_size):
            generated += 1
            text = enc.decode(out[i])
            batches.append(text)

    return batches

def find_quotes(batch):
    quotes = []
    potential_quotes = batch.split('\n\n')

    for potential_quote in potential_quotes:
        if potential_quote.startswith('"') and potential_quote.endswith('" - Alan Watts'):
            quotes.append(potential_quote)
    return quotes

if __name__ == '__main__':
    fire.Fire(interact_model)
