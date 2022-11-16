
import torch.nn as nn
import numpy as np
from math import sqrt
from random import choice
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
import pandas as pd
from eval_utils import eval_model_on_groups

def plot_dataset_digits(df, data_col='img', label_col='digit'):
    """
    Plots a sample of digits from the dataframe
    """
    fig = plt.figure(figsize=(13, 8))
    columns = 6
    rows = 3
    # ax enables access to manipulate each of subplots
    ax = []

    for i in range(columns * rows):
        # Choose a random index at each stage, so we don't get only the same digit
        idx = choice(range(len(df)))
        img, label = df.iloc[idx][[data_col, label_col]]
        if img.shape[0] == 1:
            pass

        # create subplot and append to ax
        ax.append(fig.add_subplot(rows, columns, i + 1))
        ax[-1].set_title("Label: " + str(label))  # set title
        plt.imshow(img)

    plt.show()  # finally, render the plot


# Plot a histogram of color values for all the images where 'label' == label
def plot_color_for_label(df, dig):
    '''
    Plot a histogram of color values for all the images where 'label' == label
    '''
    df.loc[df['label']==dig].color.value_counts().plot(kind='bar', xlabel='Color', ylabel="Count", rot=0)
    

def plot_one_each(df, data_col='img', label_col='digit'):
    """
    Choose one example of each value from label_col and render its data from data_col in the DataFrame df.
    """
    fig = plt.figure(figsize=(13, 8))
    columns = 5
    rows = 2
    ax = []  # ax enables access to manipulate each of subplots

    # keep track of how many items we have plotted
    # Loop through the values for label_col
    for i, label in enumerate(df[label_col].unique()):
        # Grab an item from the subset of the df where label_col==label 
        items = df.loc[df[label_col] == label]
        idx = choice(range(len(items)))
        img = items.iloc[idx][data_col]

        if img.shape[0] == 1:
            pass

        # create subplot and append to ax
        ax.append(fig.add_subplot(rows, columns, i + 1))
        ax[-1].set_title("Label: " + str(label))  # set title
        plt.imshow(img)
    plt.show()


def plot_confusion_matrix(df, label_col, pred_col, dataset_name):
    """
    Renders a confusion matrix from a dataframe
    """
    y_true = df[label_col]
    y_pred = df[pred_col]

    cm = confusion_matrix(y_true, y_pred)  #, labels=labels_names)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm)  #, display_labels=target_names)
    disp.plot(cmap=plt.cm.Blues, values_format='g')
    plt.title(f'{dataset_name} Confusion Matrix')
    plt.show()


def plot_confusion_matrices(train_df, test_df, label_col, pred_col, dataset_name):
    """
    Renders a confusion matrix from a dataframe
    """
    y_true_train = train_df[label_col]
    y_pred_train = train_df[pred_col]

    y_true_test = test_df[label_col]
    y_pred_test = test_df[pred_col]

    cm_train = confusion_matrix(y_true_train, y_pred_train)
    cm_test = confusion_matrix(y_true_test, y_pred_test)

    class_names = y_true_train.unique()

    # Add train to figure
    fig = plt.figure(figsize=(13, 8))
    train_ax = fig.add_subplot(1, 2, 1)
    train_ax.set_title('Train')  # set title
    disp_train = ConfusionMatrixDisplay(confusion_matrix=cm_train, display_labels=class_names)
    disp_train.plot(cmap=plt.cm.Blues, values_format='g', ax=train_ax)
    # Add test to figure
    test_ax = fig.add_subplot(1, 2, 2)
    test_ax.set_title('Test')  # set title
    disp_test = ConfusionMatrixDisplay(confusion_matrix=cm_test, display_labels=class_names)
    disp_test.plot(cmap=plt.cm.Blues, values_format='g', ax=test_ax)

    plt.suptitle(f'Confusion Matrices for {dataset_name}')
    plt.show()



def plot_confidence_intervals_train_and_test(train_dict_of_dfs,
                                              test_dict_of_dfs,
                                              group_name,
                                              dataset_name,
                                              x_ticklabels=None,
                                              use_legend=True,
                                              figsize=(12, 6),
                                              fontsize=16,
                                              tick_spacing=1):
    """
    Plots confidence intervals from each subgroup given a df with the columns: 'group', 'correct_count', 'total_count'
    """

    train_df = train_dict_of_dfs[group_name]
    train_ci_dict = compute_wald_intervals(train_df)

    n_groups = len(train_ci_dict)

    test_df = test_dict_of_dfs[group_name]
    test_ci_dict = compute_wald_intervals(test_df)

    fig, axes = plt.subplots(figsize=figsize, nrows=1, ncols=2, sharey=True)
    title = f'Confidence Intervals for {dataset_name} Dataset Grouped by {group_name.capitalize()}'
    fig.suptitle(title, fontsize=fontsize)
    # fig.suptitle(title, fontsize=fontsize)

    # Plot the training intervals on the left
    for group_id, ((p, eps), n) in train_ci_dict.items():
        # print(f'p: {p}, eps: {eps:.4f}, n: {n}')
        axes[0].errorbar(y=[p], yerr=eps, x=[group_id], markersize=12,
                         capsize=12, fmt='o-', label=str(group_id) + f'(n = {n})')

    # axes[0].xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    axes[0].set_title('Train')
    if use_legend:
        axes[0].legend()
    if x_ticklabels:
        axes[0].set_xticks(range(n_groups), labels=x_ticklabels)

    # Plot the intervals for test on the right
    for group_id, ((p, eps), n) in test_ci_dict.items():
        # print(f'p: {p}, eps: {eps:.4f}, n: {n}')
        axes[1].errorbar(y=[p], yerr=eps, x=[group_id], markersize=12,
                         capsize=12, fmt='o-', label=str(group_id) + f'(n = {n})')

    axes[1].set_title('Test')
    # axes[1].xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    if use_legend:
        axes[1].legend()
    if x_ticklabels:
        axes[1].set_xticks(range(n_groups), labels=x_ticklabels)

    plt.tight_layout()
    # plt.set_cmap('colorblind')
    plt.show()


def plot_confidence_intervals(dict_of_dfs,
                              group_name,
                              dataset_name,
                              x_ticklabels=None,
                              use_legend=True,
                              figsize=(12, 6),
                              fontsize=16,
                              tick_spacing=1):
    """
    Plots confidence intervals from each subgroup given a df with the columns: 'group', 'correct_count', 'total_count'
    """

    df = dict_of_dfs[group_name]
    ci_dict = compute_wald_intervals(df)
    n_groups = len(ci_dict)
    fig, ax = plt.subplots(figsize=figsize, nrows=1, ncols=1)
    title = f'Confidence Intervals for {dataset_name} Dataset Grouped by {group_name.capitalize()}'
    fig.suptitle(title, fontsize=fontsize)
    # fig.suptitle(title, fontsize=fontsize)

    # Plot the training intervals on the left
    for group_id, ((p, eps), n) in ci_dict.items():
        # print(f'p: {p}, eps: {eps:.4f}, n: {n}')
        ax.errorbar(y=[p], yerr=eps, x=[group_id], markersize=12,
                         capsize=12, fmt='o-', label=str(group_id) + f'(n = {n})')

    ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
    if use_legend:
        ax.legend()
    if x_ticklabels:
        ax.set_xticks(range(n_groups), labels=x_ticklabels)

    plt.tight_layout()
    # plt.set_cmap('colorblind')
    plt.show()


def plot_confidence_intervals_from_df(df_with_preds, label_col, pred_col, dataset_name, group_name, x_ticklabels=None,
                                      use_legend=True, figsize=(12, 6), fontsize=16, tick_spacing=1):
    """
    Plots confidence intervals directly from dataframe.
    """

    dict_of_dfs = eval_model_on_groups(df=df_with_preds, label_col=label_col, pred_col=pred_col,
                                       dataset_name=dataset_name, group_names=[group_name], print_output=False)

    plot_confidence_intervals(dict_of_dfs, group_name, dataset_name, x_ticklabels, use_legend, figsize,
                              fontsize, tick_spacing)


def plot_confidence_intervals_from_df_train_and_test(train_df_with_preds, test_df_with_preds,
                                                     label_col, pred_col, dataset_name, group_name,
                                                     x_ticklabels=None, use_legend=True, figsize=(12, 6),
                                                     fontsize=16, tick_spacing=1):
    """
    Plots confidence intervals directly from dataframe.
    """
    train_dict_of_dfs = eval_model_on_groups(df=train_df_with_preds, label_col=label_col, pred_col=pred_col,
                                             dataset_name=dataset_name, group_names=[group_name], print_output=False)

    test_dict_of_dfs = eval_model_on_groups(df=test_df_with_preds, label_col=label_col, pred_col=pred_col,
                                            dataset_name=dataset_name, group_names=[group_name], print_output=False)

    plot_confidence_intervals_train_and_test(train_dict_of_dfs, test_dict_of_dfs, group_name, dataset_name,
                                             x_ticklabels, use_legend, figsize, fontsize, tick_spacing)


def compute_wald_intervals(df):
    """
    We are given a dataframe with the columns: 'group', 'correct_count', 'total_count'
    For each unique group ID, we want one confidence interval that will be centered around correct_count / total_count.
    We will use the Wald approximation since we have a binary samples (correct or not).

    Specifically, our formula is p +- z * sqrt(p(1-p) / n)  with z = 1.96 for 95% confidence.

    Returns a dict of the form {group_id : (p, epsilon)}
    """
    ci_dict = {}

    for t in df.itertuples():
        group_id, correct_count, total_count = t.group, t.correct_count, t.total_count
        p = correct_count / total_count
        n = total_count
        eps = 1.96 * sqrt(p * (1-p) / n)
        # print(f'p: {p}, eps: {eps:.4f}, n: {n}')
        ci_dict[group_id] = ((p, eps), n)

    return ci_dict
