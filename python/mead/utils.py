import os
import json
from copy import deepcopy
from collections import OrderedDict
from baseline.utils import export, str2bool
from mead.mime_type import mime_type
import hashlib
import zipfile
import argparse

__all__ = []
exporter = export(__all__)


@exporter
def index_by_label(dataset_file):
    with open(dataset_file) as f:
        datasets_list = json.load(f)
        datasets = dict((x["label"], x) for x in datasets_list)
        return datasets


@exporter
def convert_path(path, loc=None):
    """If the provided path doesn't exist search for it relative to loc (or this file)."""
    if os.path.isfile(path):
        return path
    if path.startswith("$"):
        return path
    if loc is None:
        loc = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(loc, path)


def _infer_type_or_str(x):
    try:
        return str2bool(x)
    except:
        try:
            return float(x)
        except ValueError:
            return x


@exporter
def modify_reporting_hook_settings(reporting_settings, reporting_args_mead, reporting_hooks):
    reporting_arg_keys = []
    for x in reporting_hooks:
        for var in reporting_args_mead:
            if "{}:".format(x) in var:
                reporting_arg_keys.append(var)
    parser = argparse.ArgumentParser()
    for key in reporting_arg_keys:
        parser.add_argument(key, type=_infer_type_or_str)
    args = parser.parse_known_args()[0]
    for key in vars(args):
        this_hook, var = key.split(":")
        reporting_settings[this_hook].update({var: vars(args)[key]})


@exporter
def order_json(data):
    """Sort json to a consistent order.
    When you hash json that has the some content but is different orders you get
    different fingerprints.
    In:  hashlib.sha1(json.dumps({'a': 12, 'b':14}).encode('utf-8')).hexdigest()
    Out: '647aa7508f72ece3f8b9df986a206d95fd9a2caf'
    In:  hashlib.sha1(json.dumps({'b': 14, 'a':12}).encode('utf-8')).hexdigest()
    Out: 'a22215982dc0e53617be08de7ba9f1a80d232b23'
    This function sorts json by key so that hashes are consistent.
    Note:
        In our configs we only have lists where the order doesn't matter so we
        can sort them for consistency. This would have to change if we add a
        config field that needs order we will need to refactor this.
    :param data: dict, The json data.
    :returns:
        collections.OrderedDict: The data in a consistent order (keys sorted alphabetically).
    """
    new = OrderedDict()
    for (key, value) in sorted(data.items(), key=lambda x: x[0]):
        if isinstance(value, dict):
            value = order_json(value)
        elif isinstance(value, list):
            value = sorted(value)
        new[key] = value
    return new


KEYS = {
    ('conll_output',),
    ('visdom',),
    ('visdom_name',),
    ('model', 'gpus'),
    ('test_thresh',),
    ('reporting',),
    ('num_valid_to_show',),
    ('train', 'verbose'),
    ('train', 'model_base'),
    ('train', 'model_zip'),
    ('test_batchsz')
}


@exporter
def remove_extra_keys(config, keys=KEYS):
    """Remove config items that don't effect the model.
    When base most things off of the sha1 hash of the model configs but there
    is a problem. Some things in the config file don't effect the model such
    as the name of the `conll_output` file or if you are using `visdom`
    reporting. This strips out these kind of things so that as long as the model
    parameters match the sha1 will too.
    :param config: dict, The json data.
    :param keys: Set[Tuple[str]], The keys to remove.
    :returns:
        dict, The data with certain keys removed.
    """
    c = deepcopy(config)
    for key in keys:
        x = c
        for k in key[:-1]:
            x = x.get(k)
            if x is None:
                break
        else:
            _ = x.pop(key[-1], None)
    return c


@exporter
def hash_config(config):
    """Hash a json config with sha1.
    :param config: dict, The config to hash.
    :returns:
        str, The sha1 hash.
    """
    stripped_config = remove_extra_keys(config)
    sorted_config = order_json(stripped_config)
    json_bytes = json.dumps(sorted_config).encode('utf-8')
    return hashlib.sha1(json_bytes).hexdigest()
