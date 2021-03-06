#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 10 14:50:17 2017

@author: Samuele Garda
"""

import logging
import pandas as pd   
from collections import defaultdict
import numpy as np
from utils import load_data 
from utils import ValidationUtilities as validation
from utils import concatenate
from FeatureExtraction.ExtraFeatures import getNegFeatures,getSentFeatures,getADRlexFeatures
from FeatureExtraction.DenseDocVec import getLSAVectors, getDoc2VecVectors
from FeatureExtraction.CNN import CNN
from sklearn import svm
from collections import OrderedDict


logger = logging.getLogger(__name__)
logging.basicConfig(format = '%(asctime)s : %(levelname)s : %(module)s: %(message)s', level = 'INFO')

def experiment1(data,y,cnn_adr,cnn_sswe,reference_we,tang_we):
  """
  See Section 4.1 in ./final-report.pdf
  """
  
  logger.info("\n\nLoading feature matrices for first experiment\n")
  
  tokenized_tweets = list(data['tok_text'].values)
  pos_text_tweets = list(data['pos_text'].values)
  
  X_LSA = getLSAVectors(pos_text_tweets, k = 300, ngram_range = (1,3))
  X_Doc2Vec= getDoc2VecVectors(tokenized_tweets, dm = 1, window = 3, dm_mean = 1, negative = 50, size = 300)
  X_cnn_adr = cnn_adr.getCNNfeautures(we_file= reference_we,text = tokenized_tweets,y = y,
                                        model = 'cnn-static')
  X_cnn_sswe = cnn_sswe.getCNNfeautures(we_file= tang_we,text = tokenized_tweets,y = y, 
                                          model = 'sswe-static')
  
  base_feature = {"LSA" : X_LSA,"Doc2Vec" : X_Doc2Vec ,"CNN-ADR" : X_cnn_adr,"CNN-SSWE" : X_cnn_sswe}
  
  
  return base_feature

def experiment2(experiment1, data,y,cnn_adr,reference_we,sent_pos,sent_neg,adr_lexicon):
  """
  See Section 4.2 in ./final-report.pdf
  """
  
  logger.info("\n\nLoading feature matrices for second experiment\n")
  
  tokenized_tweets = list(data['tok_text'].values)
  raw_text_tweet = list(data['raw_text'].values)
  
  base_feature = {"LSA" : experiment1.pop("LSA") , "CNN-ADR" : experiment1.pop("CNN-ADR")}
  
  X_neg = getNegFeatures(tokenized_tweets)
  X_sent = getSentFeatures(tokenized_tweets,sent_pos,sent_pos)
  X_adr = getADRlexFeatures(raw_text_tweet,adr_lexicon)
  X_sent_specific = concatenate([X_sent,X_neg])
  X_tot_extra = concatenate([X_sent_specific,X_adr])
  
  extra_feature = {"ADR-LEX" : X_adr, "SENT" : X_sent_specific,"TOT-EXTRA" : X_tot_extra }
  
  complete_feature = {}
  for name_base_X,base_X in base_feature.items():
    for name_extra_X,extra_X in extra_feature.items():
      complete_feature["{0}-{1}".format(name_base_X,name_extra_X)] =  concatenate([base_X,extra_X])
      
  return complete_feature
  
  
def experiment3(data,y,cnn_adr,cnn_sswe,reference_we,tang_we):
  """
  See Section 4.3 in ./final-report.pdf
  """
  
  logger.info("\n\nLoading feature matrices for third experiment\n")
  
  tokenized_tweets = list(data['tok_text'].values)
  
  X_cnn_adr = cnn_adr.getCNNfeautures(we_file= reference_we,text = tokenized_tweets,y = y,
                                      model = 'cnn-non-static') 
  X_cnn_sswe = cnn_sswe.getCNNfeautures(we_file= tang_we,text = tokenized_tweets,y = y, 
                                        model = 'sswe-non-static')
   
  cnn_feature = {"CNN-ADR-T" : X_cnn_adr, "CNN-SSWE-T" : X_cnn_sswe}
   
  return cnn_feature     

def experiment_validation(clf,y,feature_dict):
  """
  Compute F1 score,precision,recall of classifier with 10 fold stratified cross validation.
  """
  overall_scores = defaultdict(OrderedDict)
  
  for name_X,X in feature_dict.items():  
    logger.info("Evaluating SVM on {0} {1}".format(name_X,X.shape))
    scores_svm = validation.standard_validation(clf,X,y)
    overall_scores[name_X]['P'] = scores_svm['test_precision_macro']
    overall_scores[name_X]['R'] = scores_svm['test_recall_macro']
    overall_scores[name_X]['F1'] = scores_svm['test_f1_macro']
    
  visualize_results = pd.DataFrame.from_dict(overall_scores, orient = 'index')
  logger.info("\n{}\n".format(visualize_results))
  logger.info("\n{}\n".format(visualize_results.to_latex()))
    
if __name__ == '__main__':
  
  seed = 7
  np.random.seed(seed)
  
  TWEETS_FILE = '../data/twitter_adr.tsv'
  POS_TWEETS = '../data/twitter_adr_pos.txt'
  REFERENCE_WE = '../data/we/reference_paper_we.txt'
  TANG_WE = '../data/we/sswe-u_tang.txt'
  ADR_LEXICON = '../data/taskSpecific/ADR_lexicon.tsv'
  SENT_POS = '../data/taskSpecific/bingliuposs.txt'
  SENT_NEG = '../data/taskSpecific/bingliunegs.txt'
  
  NUM_FILTERS = 32
  NUM_WORDS = (2,3)
  BATCH_SIZE = 64
  NUM_EPOCHS = 3 
  
  logger.info("\nLoading data...\n")
  
  tweet_data = load_data(TWEETS_FILE,POS_TWEETS)
  labels = list(tweet_data['adr'].values)
  
  svm_linear = svm.LinearSVC(class_weight = 'balanced')
  
  CNN_ADR = CNN(embeddings_dim= 150, num_filters= NUM_FILTERS,vocab_size = 5000, num_words= NUM_WORDS,
            batch_size= BATCH_SIZE,num_epochs= NUM_EPOCHS)

  
  CNN_SSWE = CNN(embeddings_dim= 50, num_filters= NUM_FILTERS, vocab_size = 7000, num_words= NUM_WORDS,
            batch_size= BATCH_SIZE,num_epochs= NUM_EPOCHS)
  
  exp1 = experiment1(tweet_data,labels,CNN_ADR,CNN_SSWE,REFERENCE_WE,TANG_WE)
  
  experiment_validation(svm_linear,labels,exp1)
  
  exp2 = experiment2(exp1,tweet_data,labels,CNN_ADR,REFERENCE_WE,SENT_POS,SENT_NEG,ADR_LEXICON)
  
  experiment_validation(svm_linear,labels,exp2)
  
  exp3 = experiment3(tweet_data,labels,CNN_ADR,CNN_SSWE,REFERENCE_WE,TANG_WE)
  
  experiment_validation(svm_linear,labels,exp3)

