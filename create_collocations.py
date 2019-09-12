#!/usr/bin/env python3
import argparse
import csv
import os
import string
from collections import Counter
from math import log


def isdir(path):
    if os.path.isdir(path):
        return path
    try:
        os.mkdir(path)
        return path
    except:
        raise argparse.ArgumentTypeError("{} is not a valid path".format(path))


def add_coo(subdict, sentence, pos, span):
    for i in range(-span, span + 1):
        if i != 0 and pos + i >= 0 and pos + i < len(sentence):
            tword = sentence[pos + i]
            subdict[tword] += 1


def count_text(fo, coocurrence, fdict, span):
    for e in fo:
        line = e.split()
        for i, w in enumerate(line):
            if w not in coocurrence:
                coocurrence[w] = Counter()
            add_coo(coocurrence[w], line, i, span)
            fdict[w] += 1


def count_vrt(fo, coocurrence, fdict, span):
    sentence = []
    for e in fo:
        if e.startswith("<s") or e.startswith("</s"):
            for i, w in enumerate(sentence):
                if w not in coocurrence:
                    coocurrence[w] = Counter()
                add_coo(coocurrence[w], sentence, i, span)
                fdict[w] += 1
            sentence.clear()
        elif e.startswith("<"):
            continue
        else:
            sentence.append(e.strip().split("\t")[0])


def compute_ll(w1, w2, minval, coocurrence, fdict, total):
    if fdict[w1] < minval or fdict[w2] < minval:
        return -1
    a = coocurrence[w1][w2]
    b = fdict[w2] - a
    c = fdict[w1] - a
    d = total - (fdict[w1] + fdict[w2])

    try:
        collocation_val = 2 * (
                a * log(a) + b * log(b) + c * log(c) + d * log(d) - (a + b) * log(a + b) - (a + c) * log(a + c) - (
                b + d) * log(b + d) - (c + d) * log(c + d) + (a + b + c + d) * log(a + b + c + d))
    except ValueError:
        return -1
    return collocation_val


def compute_word_collocates(w1, limit, minval, coocurrence, fdict, total):
    results = sorted([(compute_ll(w1, w2, minval, coocurrence, fdict, total), w2) for w2 in coocurrence[w1]],
                     reverse=True)[:limit]
    return [{"word": word, "LL": ll, "coll_count": coocurrence[w1][word], "word_count": fdict[word]} for i, (ll, word)
            in enumerate(results) if ll > 0]


def main():
    parser = argparse.ArgumentParser("Create-Collocations")
    parser.add_argument("-o", "--output", type=isdir, help="Path to output dir", required=True)
    parser.add_argument("-t", "--text", type=argparse.FileType("r"), help="Input as One Sentence per Line")
    parser.add_argument("-v", "--vrt", type=argparse.FileType("r"), help="Input as VRT File")
    parser.add_argument("-s", "--span", type=int, default=3, help="Span of Collocate Calculation")
    parser.add_argument("-m", "--mincount", type=int, default=5,
                        help="Min Count of Sourcewords and Target words to be in the output.")
    parser.add_argument("--limit", type=int, default=1000, help="MaxCollocates per Word")

    args = parser.parse_args()
    BASEPATH = args.output
    SPAN = args.span

    coocurrence = dict()
    fdict = Counter()

    if args.text and args.vrt:
        raise argparse.ArgumentError("Do not use both -v and -t.")

    if args.text:
        count_text(args.text, coocurrence, fdict, SPAN)
    if args.vrt:
        count_vrt(args.vrt, coocurrence, fdict, SPAN)

    total = sum(fdict.values())

    for word in fdict:
        if fdict[word] < args.mincount:
            continue

        bc = word[0].upper()
        if bc in string.punctuation:
            bc = "$punct$"

        target_folder = os.path.join(BASEPATH, bc)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

        with open(os.path.join(target_folder, "'{}'_collocates.tsv".format(word.replace(r"/", "<slash>"))), "w") as f:
            f.write("WORD\t{}\tFREQUENCY\t{}\n".format(word, fdict[word]))
            writer = csv.DictWriter(f, fieldnames=["word", "LL", "coll_count", "word_count"], dialect="excel-tab")
            writer.writeheader()
            for r in compute_word_collocates(word, args.limit, args.mincount, coocurrence, fdict, total):
                writer.writerow(r)


if __name__ == '__main__':
    main()
