import os
from datetime import datetime

import pandas as pd
import spacy
from sklearn import svm, preprocessing
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

from load_data import split_data, get_baseline, difference_in_length, first_word_same, jaccard_sim, cosine
from load_data import train_and_test_classifiers

folder = 'C:\\Users\\syim\\Documents\\ELEXIS\\codalab\\public_dat\\train'


def add_column_names(df):
    column_names = ['word', 'pos', 'def1', 'def2', 'relation']
    df.columns = column_names


def load_data(file_path):
    loaded_data = pd.read_csv(file_path, sep='\t', header=None)
    add_column_names(loaded_data)

    return loaded_data


def load_training_data():
    combined_set = {}

    for filename in os.listdir(folder):
        if filename.endswith(".tsv"):
            combined_set[filename.split('.')[0]] = load_data(folder + '/' + filename)

    return combined_set


def spacy_nlp(sentence):
    return nlp(sentence)


def sentence2vec(row):
    return row['processed_1'].similarity(row['processed_2'])


def extract_features(data, feats_to_scale):
    feat = pd.DataFrame()

    feat['similarities'] = data.apply(lambda row: sentence2vec(row), axis=1)
    feat['first_word_same'] = data.apply(lambda row: first_word_same(row), axis=1)
    feat['len_diff'] = data.apply(lambda row: difference_in_length(row), axis=1)
    feat['jaccard'] = data.apply(lambda row: jaccard_sim(row), axis=1)
    feat['cos'] = data.apply(lambda row: cosine(row), axis=1)

    for c_name in feats_to_scale:
        feat[c_name] = preprocessing.scale(feat[c_name])

    return feat


def convert_to_nltk_dataset(features, labels):
    converted = []
    for index, row in features.iterrows():
        converted.append((row.to_dict(), labels[index]))
    return converted


def prepare_data(df_features, labels):
    data_holder = {'nltk': {}, 'pd': {}}

    features_nltk = convert_to_nltk_dataset(df_features, labels)
    data_holder['nltk']['trainset'], data_holder['nltk']['testset'] = split_data(features_nltk)
    data_holder['pd']['x_trainset'], data_holder['pd']['x_testset'] = split_data(df_features)
    data_holder['pd']['y_trainset'], data_holder['pd']['y_testset'] = split_data(labels)

    return data_holder


def run_cv_with_dataset(model, trainset, y_train):
    scores = cross_val_score(model, trainset, y_train, cv=5)
    print('Cross validation scores for model' + model.__class__.__name__)
    scores
    print("Accuracy: %0.4f (+/- %0.4f)" % (scores.mean(), scores.std() * 2))


def cross_val_models(models, x_train, y_train):
    for estimator in models['unscaled']:
        run_cv_with_dataset(estimator, x_train, y_train)

    # for estimator in models['scaled']:
    #     run_cv_with_dataset(estimator, all_training_set['scaled'], y_train)


def get_baseline_df(y_test):
    TP = 0
    for index in y_test.index:
        if y_test[index] == 'none':
            TP += 1

    return float(TP / len(y_test))


def train_models_sklearn(X_train, y_train, y_test):
    lr = LogisticRegression(solver='lbfgs', multi_class='multinomial') \
        .fit(X_train, y_train)
    # lr_scaled = LogisticRegression( solver = 'lbfgs', multi_class = 'multinomial').fit(X_train_scaled, y_train)

    ## Linear kernal won't work very well, experiment with nonlinear ones.
    svm_model = svm.LinearSVC(C=1.0) \
        .fit(X_train, y_train)
    # svm_scaled = svm.LinearSVC().fit(X_train_scaled, y_train)

    rf = RandomForestClassifier(max_depth=5, random_state=0) \
        .fit(X_train, y_train)
    # rf_scaled = RandomForestClassifier(max_depth = 5, random_state=0).fit(X_train_scaled, y_train)

    models = {}
    models['unscaled'] = [lr, svm_model, rf]
    # models['scaled'] = [lr_scaled, svm_scaled, rf_scaled]

    return models


def is_not_none(df):
    return df['relation'] != 'none'


def is_none(df):
    return df['relation'] == 'none'


def balance_dataset(imbalanced_set):
    none = imbalanced_set[is_none(imbalanced_set) == True]
    second_biggest = imbalanced_set.groupby('relation').count().word.sort_values(ascending=False)[1]
    balanced = imbalanced_set.drop(none.index[second_biggest:])

    return balanced.sample(frac=1)


def compare_on_testset(models, testset_x, testset_y, testset_x_scaled):
    print('Model Evaluation on Testset: ' + '\n')
    print('\t' + 'BASELINE: ' + str(get_baseline_df(testset_y)) + '\n')

    for estimator in models['unscaled']:
        estimator.predict(testset_x)
        print('\t' + estimator.__class__.__name__)
        score = estimator.score(testset_x, testset_y)
        print('\t\t' + "Accuracy: %0.4f (+/- %0.4f)" % (score.mean(), score.std() * 2) + '\n')

        estimator.predict(testset_x_scaled)
        score = estimator.score(testset_x_scaled, testset_y)
        print('\t\t' + "Accuracy for scaled featureset: %0.4f (+/- %0.4f)" % (score.mean(), score.std() * 2) + '\n')


if __name__ == '__main__':
    now = datetime.now()
    report = open(now.strftime("%Y%m%d%H%M%S") + ".txt", "a")

    nlp = spacy.load('en_core_web_lg')
    pd.set_option('display.max_colwidth', -1)

    all_data = load_training_data()
    en_data = all_data['english_kd']
    balanced_en_data = balance_dataset(en_data)

    balanced_en_data['processed_1'] = balanced_en_data['def1'].map(spacy_nlp)
    balanced_en_data['processed_2'] = balanced_en_data['def2'].map(spacy_nlp)

    report.write((str(balanced_en_data.groupby('relation').count().word.sort_values(ascending=False)) + '\n'))

    features = extract_features(balanced_en_data, ['similarities'])
    all_train_and_testset = prepare_data(features, balanced_en_data['relation'])

    train_and_test_classifiers(all_train_and_testset['nltk']['trainset'], all_train_and_testset['nltk']['testset'])

    trained_models = train_models_sklearn(all_train_and_testset['pd']['x_trainset'],
                                          all_train_and_testset['pd']['y_trainset'],
                                          all_train_and_testset['pd']['y_testset'])

    cross_val_models(trained_models, all_train_and_testset['pd']['x_trainset'],
                     all_train_and_testset['pd']['y_trainset'])

    compare_on_testset(trained_models, all_train_and_testset['pd']['x_testset'],
                       all_train_and_testset['pd']['y_testset'], all_train_and_testset['pd']['x_testset'])
