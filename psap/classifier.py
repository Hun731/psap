import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from random import sample
from tqdm.notebook import tqdm
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from joblib import dump, load


def preprocess_and_scaledata(data, instance):
    # try:
    #    data = data.drop(["uniprot_id", "PRDaa"], axis=1)
    # except KeyError:
    #    data = data.drop(["uniprot_id"], axis=1)
    data = data.fillna(value=0)
    print(
        "Number of phase separating proteins in dataset: "
        + str(data.loc[data[instance] == 1].shape[0])
    )
    scaler = MinMaxScaler()
    df = data.copy()
    processed_data = df.fillna(0)
    processed_data = preprocess_data(processed_data, scaler, instance)
    # processed_data = remove_correlating_features(processed_data, cutoff=.95)
    # processed_data = remove_low_variance_features(processed_data, variance_cutoff=0.08)
    return processed_data


def preprocess_data(df, scaler, instance):
    info = df.select_dtypes(include=["object"])
    y = df[instance]
    X = df.drop([instance], axis=1)
    X = X._get_numeric_data()
    columns = X.columns
    X = scaler.fit_transform(X)
    X = pd.DataFrame(X, columns=columns)
    X[instance] = y
    X = X.merge(info, how="outer", left_index=True, right_index=True)
    return X


def get_test_train_indexes(data, label, ratio=1, randomized=False):
    """
    Function: Will oversample the positive data with randomly selected negative samples.
    Returns: List with indexes which contain positive and negative samples.
    """
    positive_instances = set(data.loc[data[label] == 1].index)
    negative_instances = set(data.loc[data[label] == 0].index)
    n_positives = data.loc[data[label] == 1].shape[0]
    indexes = list()
    while len(negative_instances) >= 1:
        if len(negative_instances) > n_positives * ratio:
            sample_set = sample(negative_instances, (n_positives * ratio))
        else:
            sample_set = list(negative_instances)
            size = len(sample_set)
            short = (len(positive_instances) * ratio) - size
            shortage = sample(set(data.loc[data[label] == 0].index), short)
            sample_set = sample_set + shortage
        indexes.append((list(positive_instances) + list(sample_set)))
        negative_instances.difference_update(set(sample_set))
    return indexes


def plot_feature_importance(fi_data, analysis_name, out_dir=""):
    fi_data["mean"] = fi_data.select_dtypes([np.number]).mean(axis=1)
    fi_data = fi_data.sort_values("mean", ascending=False).reset_index(drop=True)
    fi_data[["variable", "mean"]]

    # Set matplotlib parameters
    sns.set(rc={"figure.figsize": (8, 6)})
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    fi_data[0:15].plot.bar(x="variable", y="mean", rot=45, color="#CD6155")
    plt.ylabel("Fraction of impact")
    plt.xlabel("Feature")
    plt.title("Mean feature importances")
    plt.savefig(f"{out_dir}/feature_importances.pdf", transparent=True)
    plt.show()


def predict_other_df(clf, processed_data, second_df, analysis_name, out_dir):
    prediction, fi_data = predict_proteome(
        processed_data,
        clf,
        instance="llps",
        testing_size=0.2,
        # remove_training=True,
        second_df=second_df,
    )
    prediction.to_csv(f"{out_dir}/full_prediction.csv")


def predict_proteome(
    df,
    clf,
    ccol,
    testing_size,
    feature_imp=True,
    remove_training=False,
    second_df=pd.DataFrame(),
):
    pd.set_option("mode.chained_assignment", None)
    prediction = df.select_dtypes(include="object")
    df = df.select_dtypes([np.number])
    if len(second_df) > 0:
        prediction = second_df.select_dtypes(include="object")
        second_df = second_df.select_dtypes([np.number])
    indexes = get_test_train_indexes(df, ccol)
    count = 0
    fi_data = None
    for index in tqdm(indexes):
        df_fraction = df.loc[index]
        # Also consider X_test index for prediction in the proteome
        X = df_fraction.drop(ccol, axis=1)
        y = df_fraction[ccol]
        clf.fit(X, y)
        # Feature importance
        if feature_imp:
            # X = df_fraction.drop('llps', axis=1)
            fi = clf.feature_importances_
            fi = pd.DataFrame(fi).transpose()
            fi.columns = X.columns
            fi = fi.melt()
            fi = fi.sort_values("value", ascending=False)
            if fi_data is None:
                fi_data = fi
            else:
                fi_data = pd.merge(fi_data, fi, on="variable")
        # Make prediction
        if len(second_df) > 0:
            probability = clf.predict_proba(second_df.drop(ccol, axis=1))[:, 1]
            prediction["probability_" + str(count)] = probability
        else:
            probability = clf.predict_proba(df.drop(ccol, axis=1))[:, 1]
            prediction["probability_" + str(count)] = probability
        # Removing prediction that were used in the train test set.
        if remove_training:
            for i in index:
                prediction.loc[i, "probability_" + str(count)] = np.nan
        count += 1
    if feature_imp:
        return prediction, fi_data
    else:
        return prediction


def train_model(training_data, prefix="", out_dir=""):
    # Make directory for output.
    try:
        os.mkdir(f"{out_dir}")
    except:
        print(
            f"Directory {prefix} already exists. Please choose another analysis name, or remove the directory {prefix}."
        )
    data = pd.read_pickle(training_data)
    data_ps = preprocess_and_scaledata(data, "llps")
    data_numeric = data_ps.select_dtypes([np.number])
    X = data_numeric.drop("llps", axis=1)
    y = data_numeric["llps"]
    clf = RandomForestClassifier(
        n_jobs=32,
        class_weight="balanced",
        n_estimators=1200,
        criterion="entropy",
        random_state=42,
    )
    clf.fit(X, y)
    psap_prediction = pd.DataFrame(index=data["protein_name"])
    psap_prediction["PSAP_score"] = clf.predict_proba(X)[:, 1]
    psap_prediction["llps"] = y.values
    psap_prediction["rank"] = 0
    rank = psap_prediction.loc[psap_prediction["llps"] == 0, "PSAP_score"].rank(
        ascending=False
    )
    psap_prediction["rank"] = rank
    # Serialize trained model
    dump(clf, f"{out_dir}/psap_prediction_{prefix}.joblid")
    psap_prediction.to_csv(f"{out_dir}/prediction_{prefix}.csv")


def psap_predict(test_data, model, prefix="", out_dir=""):
    clf = load(model)
    data = pd.read_pickle(test_data)
    print(data)
    # Make directory for output.
    try:
        os.mkdir(f"{out_dir}")
    except:
        print(
            f"Directory {prefix} already exists. Please choose another analysis name, or remove the directory {prefix}."
        )
    data_ps = preprocess_and_scaledata(data, "llps")
    data_numeric = data_ps.select_dtypes([np.number])
    X = data_numeric.drop("llps", axis=1)
    y = data_numeric["llps"]
    psap_prediction = pd.DataFrame(index=data["protein_name"])
    psap_prediction["PSAP_score"] = clf.predict_proba(X)[:, 1]
    psap_prediction["llps"] = y.values
    psap_prediction["rank"] = 0
    rank = psap_prediction.loc[psap_prediction["llps"] == 0, "PSAP_score"].rank(
        ascending=False
    )
    psap_prediction["rank"] = rank
    psap_prediction.to_csv(f"{out_dir}/prediction_{prefix}.csv")
