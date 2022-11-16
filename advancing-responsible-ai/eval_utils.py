import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from collections import defaultdict
from dataset_utils import create_dataloader_from_df, create_dataloader_from_df_with_groups

import dataset_utils as dataset_utils

# TODO: remove when no longer editting these files
import importlib
importlib.reload(dataset_utils)


class GroupStatisticTracker(object):
    """
    Class to facilitate computing the subgroup error rates for a particular group class (e.g. digit)
    """

    def __init__(self, group_name):
        self.group_name = group_name
        self.correct_counts = defaultdict(int)
        self.total_counts = defaultdict(int)

    def incr_correct(self, subgroup):
        self.correct_counts[subgroup] += 1
        self.total_counts[subgroup] += 1

    def incr_incorrect(self, subgroup):
        self.total_counts[subgroup] += 1

    def report_statistics(self):
        """
        Prints the aggregated statistics after incrementing the counters
        """
        print(f'\nEvaluation Report for groups defined by {self.group_name.capitalize()}')
        for subgroup_id in sorted(self.total_counts.keys()):
            acc = self.correct_counts[subgroup_id] / self.total_counts[subgroup_id]
            print(f'\tAccuracy on Group {subgroup_id}: '
                  f'{acc} = {self.correct_counts[subgroup_id]}/{self.total_counts[subgroup_id]}')

        self.report_bias_statistics()

    def report_bias_statistics(self):
        d = self._get_accuracies_for_each_group()
        # Sort the dict items by their value
        sorted_accs = sorted(d.items(), key=lambda x: x[1])
        min_idx, min_acc = sorted_accs[0]
        max_idx, max_acc = sorted_accs[-1]
        print(f'The maximum accuracy is achieved on group {max_idx} with value {max_acc}.')
        print(f'The minimum accuracy is achived on group {min_idx} with value {min_acc}.')
        print(f'The ratio of min to max accuracy is {min_acc / max_acc} and the difference is {max_acc - min_acc}')

    def _get_accuracies_for_each_group(self):
        """
        Returns a dictionary mapping {g: acc} for each group g.
        """
        d = {}
        for g in sorted(self.total_counts.keys()):
            d[g] = self.correct_counts[g] / self.total_counts[g]
        return d

    def get_dataframe_summary(self):
        """
        Returns a dataframe with one row for each group and the three columns
            group
            correct_count
            total_count
        :return:
        """
        data = [
            (
                subgroup_id,
                self.correct_counts[subgroup_id],
                self.total_counts[subgroup_id]
            )
            for subgroup_id in sorted(self.total_counts.keys())
        ]
        return pd.DataFrame.from_records(data, columns=['group', 'correct_count', 'total_count'])


def run_model(model, df, img_col, label_col, dataset_name, pred_col='pred', print_acc=False):
    """
    Runs the model and returns a new dataframe that has an additional column (default name 'preds') corresponding to
    the model vector predictions for each of the images.
    """
    new_df = df.copy()
    # We hardcode the data shuffle seed to 0 because there is no effect on evaluation results
    test_loader = create_dataloader_from_df(df, img_col, label_col, dataset_name, data_shuffle_seed=0, train=False)
    _, preds = run_model_from_dataloader(model, test_loader, dataset_name, print_acc)
    new_df[pred_col] = preds
    return new_df


def run_model_from_dataloader(model, test_loader, dataset_name, print_acc=False):
    """
    Runs the model and returns the accuracy and the predictions.

    :param model:
    :param test_loader:
    :param dataset_name:
    :param print_acc:
    :return:
    """
    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    model.eval()

    predictions = []

    test_loss = 0
    correct = 0
    loss_fn = nn.CrossEntropyLoss()

    with torch.no_grad():
        # NOTE: these are vectors of the entire batch. We need to break these batches down by group
        for data, target, *_ in test_loader:
            data, target = data.to(device), target.to(device)  # .float()
            output = model(data)
            test_loss += loss_fn(output, target)  # sum up batch loss
            preds = torch.argmax(output, dim=1)  # get the index of the max probability class
            correct += (target == preds).sum()  # sum over batch when target == pred

            # Append each (class) prediction to a list
            for pred in preds:
                # print(f'Adding {len(preds)} objects')
                predictions.append(pred.item())

    test_loss /= len(test_loader.dataset)

    if print_acc:
        print('\nPerformance on {}: Average loss: {:.4f}, Accuracy: {}/{} ({:.2f}%)\n'.format(
            dataset_name, test_loss, correct, len(test_loader.dataset),
            100. * correct / len(test_loader.dataset)))

    return (100. * correct / len(test_loader.dataset)), predictions
    # return 100. * correct / len(test_loader.dataset)


def eval_model(df, label_col, pred_col, dataset_name):
    """
    Returns a tuple of the total accuracy and a new dataframe with the preds attached
    """
    correct = sum(df[label_col].eq(df[pred_col]))
    total = len(df)
    accuracy = 100. * correct / total
    print(f'\n Accuracy on {dataset_name}: {correct}/{total} ({accuracy:.2f}%)\n')


def eval_model_on_groups(df, label_col, pred_col, dataset_name, group_names, print_output=False):
    """
    Evaluates the model. TODO: add in the group evaluation here...

    :param df: dataframe of dataset
    :param label_col: column name of the label
    :param pred_col: column the prediction
    :param dataset_name: dataset name for printing
    :param group_names: names of the column headers of the groups we want to group by
    :return:
    """
    n_groups = len(group_names)
    # Initialize an instance of our custom class to track the statistics for each group we are looking at
    group_stat_trackers = [GroupStatisticTracker(name) for name in group_names]

    for target, pred, *group_tuple in zip(df[label_col], df[pred_col], *(df[group] for group in group_names)):

        # Correct classification
        if pred == target:
            # For each group type, add this instance to the stat tracker
            for idx, subgroup in enumerate(group_tuple):
                s = subgroup  # Unpack tensor(d) into the digit d
                group_stat_trackers[idx].incr_correct(s)
        else:
            for idx, subgroup in enumerate(group_tuple):
                s = subgroup  # Unpack tensor(d) into the digit d
                group_stat_trackers[idx].incr_incorrect(s)

    # Print the results
    if print_output:
        print(f'Group-based results for {dataset_name} dataset')
    out = {}
    for tracker in group_stat_trackers:
        if print_output:
            tracker.report_statistics()
        # Add the dataframe to the output dictionary
        out[tracker.group_name] = tracker.get_dataframe_summary()

    return out
