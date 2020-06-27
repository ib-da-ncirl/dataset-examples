# -*- coding: utf-8 -*-
"""Convert the Yelp Dataset Challenge dataset from json format to csv.

For more information on the Yelp Dataset Challenge please visit http://yelp.com/dataset_challenge

"""
import argparse
import collections
import csv
import simplejson as json
import re

try:
    collectionsAbc = collections.abc
except AttributeError:
    collectionsAbc = collections


def read_and_write_file(json_file_path, csv_file_path, column_names):
    """Read in the json dataset file and write it out to a csv file, given the column names."""
    with open(csv_file_path, 'w', encoding='utf8') as fout:
        csv_file = csv.writer(fout)
        csv_file.writerow(list(column_names))
        with open(json_file_path) as fin:
            count = 1
            for line in fin:
                line_contents = get_line_contents(line)
                csv_file.writerow(get_row(line_contents, column_names))
                if count % 100 == 0:
                    print(f"Line: {count}", end="\r", flush=True)
                count += 1
            print()


def get_line_contents(raw_line):
    """ Standardise the json format in the string """
    # convert json entries like ['validated': False] to ["validated": "False"]
    wip_line = raw_line.replace(": True", ': "True"')
    wip_line = wip_line.replace(": False", ': "False"')
    wip_line = re.sub(r"'(\w+)':", lambda m: '"' + m.group(1) + '":', wip_line)

    # convert json entries like ['dairy-free':] to ["dairy-free":]
    wip_line = re.sub(r"'(\w+)-(\w+)':", lambda m: '"' + m.group(1) + '-' + m.group(2) + '":', wip_line)

    # convert json entries like ["{]/[}"] to [{]/[}]
    wip_line = re.sub(r"\"{", "{", wip_line)
    # wip_line = re.sub(r"}\"", "}", wip_line)

    # but need to handle case like ["name":"Small Flower {floral studio}"]
    # do temp replacement
    wip_line = re.sub(r"(\"name\":\"[\w ]+)\{([\w ]+)\}(\")",
                      lambda m: m.group(1) + "x{x" + m.group(2) + "x}x" + m.group(3), wip_line)

    wip_line = re.sub(r"}\"([,}])", lambda m: '}' + m.group(1), wip_line)

    # undo temp replacement
    wip_line = re.sub(r"(\"name\":\"[\w ]+)x\{x([\w ]+)x\}x(\")",
                      lambda m: m.group(1) + "{" + m.group(2) + "}" + m.group(3), wip_line)

    # convert json entries like ["WiFi":"u'no'"] to ["WiFi":"no"]
    wip_line = re.sub(r"\"u'(\w+)'\"", lambda m: '"' + m.group(1) + '"', wip_line)

    # convert json entries like ["Alcohol":"'none'"] to ["Alcohol":"none"]
    wip_line = re.sub(r"'(\w+)'", lambda m: m.group(1), wip_line)

    # convert json entries like ["xyz": None] to ["xyz": "None"]
    wip_line = re.sub(r"(?<!\")None([,}])", lambda m: '"None"' + m.group(1), wip_line)

    line_contents = json.loads(wip_line)

    return line_contents


def get_superset_of_column_names_from_file(json_file_path):
    """Read in the json dataset file and return the superset of column names."""
    column_names = set()
    with open(json_file_path) as fin:
        for line in fin:
            line_contents = get_line_contents(line)
            column_names.update(
                    set(get_column_names(line_contents).keys())
                    )
    return column_names


def get_column_names(line_contents, parent_key=''):
    """Return a list of flattened key names given a dict.

    Example:

        line_contents = {
            'a': {
                'b': 2,
                'c': 3,
                },
        }

        will return: ['a.b', 'a.c']

    These will be the column names for the eventual csv file.

    """
    column_names = []
    for k, v in line_contents.items():
        column_name = "{0}.{1}".format(parent_key, k) if parent_key else k
        if isinstance(v, collectionsAbc.MutableMapping):
            column_names.extend(
                    get_column_names(v, column_name).items()
                    )
        else:
            column_names.append((column_name, v))
    return dict(column_names)


def get_nested_value(d, key):
    """Return a dictionary item given a dictionary `d` and a flattened key from `get_column_names`.
    
    Example:

        d = {
            'a': {
                'b': 2,
                'c': 3,
                },
        }
        key = 'a.b'

        will return: 2
    
    """
    if d is None:
        return None
    if '.' not in key:
        if key not in d:
            return None
        return d[key]
    base_key, sub_key = key.split('.', 1)
    if base_key not in d:
        return None
    sub_dict = d[base_key]
    return get_nested_value(sub_dict, sub_key)


def get_row(line_contents, column_names):
    """Return a csv compatible row given column names and a dict."""
    row = []
    for column_name in column_names:
        line_value = get_nested_value(
                        line_contents,
                        column_name,
                        )
        if isinstance(line_value, str):
            row.append('{0}'.format(line_value))
        elif line_value is not None:
            row.append('{0}'.format(line_value))
        else:
            row.append('')
    return row


if __name__ == '__main__':
    """Convert a yelp dataset file from json to csv."""

    parser = argparse.ArgumentParser(
        description='Convert Yelp Dataset Challenge data from JSON format to CSV.',
    )

    parser.add_argument(
        'json_file',
        type=str,
        help='The json file to convert.',
    )
    parser.add_argument(
        '-v',
        type=bool,
        help='Verbose mode',
        default=False,
        required=False
    )

    args = parser.parse_args()

    json_file = args.json_file
    csv_file = '{0}.csv'.format(json_file.split('.json')[0])

    print(f"Converting '{json_file}' to '{csv_file}'")

    print(f"Retrieving column names")
    column_names = get_superset_of_column_names_from_file(json_file)
    print(f"{len(column_names)} column names identified")
    if args.v:
        print(f"{column_names}")

    print(f"Processing json file")
    read_and_write_file(json_file, csv_file, column_names)
