import csv
import logging
import sys
import numpy as np
import os
import random
import pickle

np.random.seed(2019)

logging.basicConfig(format = '%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt = '%m/%d/%Y %H:%M:%S',
                    level = logging.INFO)
logger = logging.getLogger(__name__)

class InputExample(object):
    """A single training/test example for simple sequence classification."""

    def __init__(self, guid, text_a, text_b=None, label=None, prons=None):
        """Constructs a InputExample.

        Args:
            guid: Unique id for the example.
            text_a: string. The untokenized text of the first sequence. For single
            sequence tasks, only this sequence must be specified.
            text_b: (Optional) string. The untokenized text of the second sequence.
            Only must be specified for sequence pair tasks.
            label: (Optional) string. The label of the example. This should be
            specified for train and dev examples, but not for test examples.
        """
        self.guid = guid
        self.text_a = text_a
        self.text_b = text_b
        self.label = label
        self.prons = prons

class InputFeatures(object):
    """A single set of features of data."""

    def __init__(self, input_ids, input_mask, segment_ids, label_id):
        self.input_ids = input_ids
        self.input_mask = input_mask
        self.segment_ids = segment_ids
        self.label_id = label_id

class InputPronFeatures(object):
    """A single set of features of data."""

    def __init__(self, input_ids, input_mask, segment_ids, label_id, prons_id, prons_att_mask):
        self.input_ids = input_ids
        self.input_mask = input_mask
        self.segment_ids = segment_ids
        self.label_id = label_id
        self.prons_id = prons_id
        self.prons_att_mask = prons_att_mask


def readfile(filename):
    '''
    read file
    return format :
    [ ['EU', 'B-ORG'], ['rejects', 'O'], ['German', 'B-MISC'], ['call', 'O'], ['to', 'O'], ['boycott', 'O'], ['British', 'B-MISC'], ['lamb', 'O'], ['.', 'O'] ]
    '''
    f = open(filename)
    data = []
    sentence = []
    label= []
    prons = []
    for line in f:
        if len(line)==0 or line.startswith('-DOCSTART') or line[0]=="\n":
            if len(sentence) > 0:
                data.append((sentence,label,prons))
                sentence = []
                label = []
                prons = []
            continue
        splits = line.split(' ')
        sentence.append(splits[0])
        label.append(splits[-2])
        prons.append(splits[-1][:-1].split(','))

    if len(sentence) >0:
        data.append((sentence,label,prons))
        sentence = []
        label = []
        prons = []
    return data

class DataProcessor(object):
    """Base class for data converters for sequence classification data sets."""

    def get_train_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the train set."""
        raise NotImplementedError()

    def get_dev_examples(self, data_dir):
        """Gets a collection of `InputExample`s for the dev set."""
        raise NotImplementedError()

    def get_labels(self):
        """Gets the list of labels for this data set."""
        raise NotImplementedError()

    @classmethod
    def _read_tsv(cls, input_file, quotechar=None):
        """Reads a tab separated value file."""
        return readfile(input_file)


class NerProcessor(DataProcessor):
    """Processor for the CoNLL-2003 data set."""

    def get_train_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_tsv(os.path.join(data_dir, "train.txt")), "train")
    
    def get_dev_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_tsv(os.path.join(data_dir, "valid.txt")), "dev")
    
    def get_test_examples(self, data_dir):
        """See base class."""
        return self._create_examples(
            self._read_tsv(os.path.join(data_dir, "test.txt")), "test")
    
    def get_labels(self):
        #return ["O", "B-MISC", "I-MISC",  "B-PER", "I-PER", "B-ORG", "I-ORG", "B-LOC", "I-LOC", "X", "[CLS]", "[SEP]"]
        return ["O", "P", "X", "[CLS]", "[SEP]"]

    def _create_examples(self,lines,set_type):
        examples = []
        for i,(sentence,label,prons) in enumerate(lines):
            guid = "%s-%s" % (set_type, i)
            text_a = ' '.join(sentence)
            text_b = None
            label = label
            prons = prons
            examples.append(InputExample(guid=guid,text_a=text_a,text_b=text_b,label=label,prons=prons))
        return examples

def convert_examples_to_features(examples, label_list, max_seq_length, tokenizer):
    """Loads a data file into a list of `InputBatch`s."""

    label_map = {label : i for i, label in enumerate(label_list,1)}
    
    features = []
    for (ex_index,example) in enumerate(examples):
        textlist = example.text_a.split(' ')
        labellist = example.label
        tokens = []
        labels = []
        for i, word in enumerate(textlist):
            token = tokenizer.tokenize(word)
            tokens.extend(token)
            label_1 = labellist[i]
            for m in range(len(token)):
                if m == 0:
                    labels.append(label_1)
                else:
                    labels.append("X")
        if len(tokens) >= max_seq_length - 1:
            tokens = tokens[0:(max_seq_length - 2)]
            labels = labels[0:(max_seq_length - 2)]
        ntokens = []
        segment_ids = []
        label_ids = []
        ntokens.append("[CLS]")
        segment_ids.append(0)
        label_ids.append(label_map["[CLS]"])
        for i, token in enumerate(tokens):
            ntokens.append(token)
            segment_ids.append(0)
            label_ids.append(label_map[labels[i]])
        ntokens.append("[SEP]")
        segment_ids.append(0)
        label_ids.append(label_map["[SEP]"])
        input_ids = tokenizer.convert_tokens_to_ids(ntokens)
        input_mask = [1] * len(input_ids)
        while len(input_ids) < max_seq_length:
            input_ids.append(0)
            input_mask.append(0)
            segment_ids.append(0)
            label_ids.append(0)
        assert len(input_ids) == max_seq_length
        assert len(input_mask) == max_seq_length
        assert len(segment_ids) == max_seq_length
        assert len(label_ids) == max_seq_length
        
        if ex_index < 5:
            logger.info("*** Example ***")
            logger.info("guid: %s" % (example.guid))
            logger.info("tokens: %s" % " ".join(
                    [str(x) for x in tokens]))
            logger.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            logger.info("input_mask: %s" % " ".join([str(x) for x in input_mask]))
            logger.info(
                    "segment_ids: %s" % " ".join([str(x) for x in segment_ids]))
            # logger.info("label: %s (id = %d)" % (example.label, label_ids))

        features.append(
                InputFeatures(input_ids=input_ids,
                              input_mask=input_mask,
                              segment_ids=segment_ids,
                              label_id=label_ids))
    return features

def convert_examples_to_pron_features(examples, label_list, max_seq_length, max_pron_length, tokenizer, prons_map):
    """Loads a data file into a list of `InputBatch`s."""

    label_map = {label : i for i, label in enumerate(label_list,1)}
    
    features = []
    for (ex_index,example) in enumerate(examples):
        textlist = example.text_a.split(' ')
        labellist = example.label
        pronslist = example.prons
        tokens = []
        labels = []
        prons = []
        prons_mask = []
        for i, word in enumerate(textlist):
            token = tokenizer.tokenize(word)
            tokens.extend(token)
            label_1 = labellist[i]
            pron_1 = pronslist[i] # the complete prons of a word
            pron_2 = [] # save the ids of prons of a word
            for j in range(len(pron_1)): 
                index = len(prons_map) # expand the map with new prons
                if pron_1[j] not in prons_map:
                    prons_map[pron_1[j]] = index + 1
                pron_2.append(prons_map[pron_1[j]])
            pron_mask_2 = [1] * len(pron_2)

            if len(pron_2) >= max_pron_length: 
                pron_2 = pron_2[0:max_pron_length] # trunk it if too long
                pron_mask_2 = pron_mask_2[0:max_pron_length]
            else:
                pron_2 += [0] * (max_pron_length - len(pron_2)) # pad it if too short
                pron_mask_2 += [0] * (max_pron_length - len(pron_mask_2))
            for m in range(len(token)):
                if m == 0:
                    labels.append(label_1)
                    prons.append(pron_2) # only send the prons to the first piece_token of a word
                    prons_mask.append(pron_mask_2)
                else:
                    labels.append("X")
                    prons.append([0] * max_pron_length) # pad other piece_token with 0's
                    prons_mask.append([0] * max_pron_length)
        if len(tokens) >= max_seq_length - 1:
            tokens = tokens[0:(max_seq_length - 2)]
            labels = labels[0:(max_seq_length - 2)]
            prons = prons[0:(max_seq_length - 2)]
            prons_mask = prons_mask[0:(max_seq_length - 2)]

        ntokens = []
        segment_ids = []
        label_ids = []
        prons_ids = []
        prons_att_mask = []
        ntokens.append("[CLS]")
        segment_ids.append(0)
        label_ids.append(label_map["[CLS]"])
        prons_ids.append([0] * max_pron_length) # pad the cls with 0's
        prons_att_mask.append([0] * max_pron_length)
        for i, token in enumerate(tokens):
            ntokens.append(token)
            segment_ids.append(0)
            label_ids.append(label_map[labels[i]])
            prons_ids.append(prons[i])
            prons_att_mask.append(prons_mask[i])
        ntokens.append("[SEP]")
        segment_ids.append(0)
        label_ids.append(label_map["[SEP]"])
        prons_ids.append([0] * max_pron_length) # pad the sep with 0's
        prons_att_mask.append([0] * max_pron_length)
        input_ids = tokenizer.convert_tokens_to_ids(ntokens)
        input_mask = [1] * len(input_ids)
        while len(input_ids) < max_seq_length:
            input_ids.append(0)
            input_mask.append(0)
            segment_ids.append(0)
            label_ids.append(0)
            prons_ids.append([0] * max_pron_length)
            prons_att_mask.append([0] * max_pron_length)
        assert len(input_ids) == max_seq_length
        assert len(input_mask) == max_seq_length
        assert len(segment_ids) == max_seq_length
        assert len(label_ids) == max_seq_length
        assert len(prons_ids) == max_seq_length
        assert len(prons_att_mask) == max_seq_length
        
        if ex_index < 0:
            logger.info("*** Example ***")
            logger.info("guid: %s" % (example.guid))
            logger.info("tokens: %s" % " ".join(
                    [str(x) for x in tokens]))
            logger.info("input_ids: %s" % " ".join([str(x) for x in input_ids]))
            logger.info("input_mask: %s" % " ".join([str(x) for x in input_mask]))
            logger.info("segment_ids: %s" % " ".join([str(x) for x in segment_ids]))
            logger.info("label_ids: %s" % " ".join([str(x) for x in label_ids]))
            logger.info("prons_ids: %s" % " ".join([str(x) for x in prons_ids]))
            logger.info("prons_att_mask: %s" % " ".join([str(x) for x in prons_att_mask]))
            logger.info("prons_map: %s" % str(prons_map))
            # logger.info("label: %s (id = %d)" % (example.label, label_ids))

        features.append(
                InputPronFeatures(input_ids=input_ids,
                              input_mask=input_mask,
                              segment_ids=segment_ids,
                              label_id=label_ids,
                              prons_id=prons_ids,
                              prons_att_mask=prons_att_mask))
    return features, prons_map


def embed_load(file_input):

    f = open(file_input, 'r')
    line = f.readline()
    pron_map = {}
    num,dim = line.rstrip().split(' ')
    line = f.readline()
    embeddings = [[0.0]*int(dim)]
    while line != '':
        vec  = line.rstrip().split(' ')
        token = vec[0]
        emb = vec[1:]
        if token not in pron_map: 
            pron_map[token] = len(pron_map) + 1
            embeddings.append([float(x) for x in emb])
    
        line = f.readline()

    return pron_map, embeddings


def embed_extend(embeddings, length):

    dim = len(embeddings[0])
    for i in range(length+1-len(embeddings)):
        embeddings.append(np.random.random([dim])*2-1)

    return embeddings

def write_scores(file_output, y):
    with open(file_output, 'wb') as f:
        pickle.dump(y, f)