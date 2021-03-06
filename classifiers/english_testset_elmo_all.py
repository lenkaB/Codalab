import pickle

import pandas as pd

from classifier_config import ClassifierConfig
from feature_extractor import FeatureExtractor
from model_trainer import ModelTrainer
from wsa_classifier import WordSenseAlignmentClassifier

german_config = ClassifierConfig('en_core_web_lg', "english", 'data/test', balancing_strategy="none",
                                 testset_ratio=0.0, with_wordnet=True, dataset='english_nuig', logger = 'en_nuig',is_testdata=True)

feature_extractor = FeatureExtractor() \
    .diff_pos_count() \
    .ont_hot_pos() \
    .matching_lemma() \
    .count_each_pos() \
    .avg_count_synsets() \
    .difference_in_length() \
    .similarity_diff_to_target() \
    .max_dependency_tree_depth() \
    .target_word_synset_count() \
    .token_count_norm_diff() \
    .semicol_count() \
    .elmo_similarity()

model_trainer = ModelTrainer(german_config, german_config.logger)

german_classifier = WordSenseAlignmentClassifier(german_config, feature_extractor, model_trainer)
data = german_classifier.load_data().get_preprocessed_data()

feats = feature_extractor.extract(data, feats_to_scale = ['len_diff', 'pos_diff'])

x_trainset, x_testset = model_trainer.split_data(feats, 0.0)


with open('models/en_nuig_split_biggestRandomForestClassifier20200401-0306.pickle', 'rb') as pickle_file:
    clf = pickle.load(pickle_file)
    predicted = clf.predict(x_trainset)
    print(predicted)
    predicted_series= pd.Series(predicted)
    data['relation'] = predicted_series
    german_predicted = data[['word','pos','def1','def2','relation']]
    german_predicted.to_csv('english_nuig_20200401.csv',sep='\t', index = False)

