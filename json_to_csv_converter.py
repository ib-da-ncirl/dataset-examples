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


def read_and_write_file(json_file_path, csv_file_path, column_names, skip=0):
    """Read in the json dataset file and write it out to a csv file, given the column names."""
    with open(csv_file_path, 'w', encoding='utf8') as fout:
        csv_file = csv.writer(fout)
        csv_file.writerow(list(column_names))
        with open(json_file_path) as fin:
            count = 1
            for line in fin:
                if skip <= 0:
                    line_contents = get_line_contents(line)
                    csv_file.writerow(get_row(line_contents, column_names))
                    if count % 100 == 0:
                        print(f"Line: {count}", end="\r", flush=True)
                else:
                    skip -= 1
                count += 1
            print()


def temp_replace(raw_line, temp_repl, gen_pattern, gen_repl, undo_repl):
    """
    Do temporary replacement of patterns which should not be changed
    :param raw_line:
    :param temp_repl: tuple/tuple list of temporary regex pattern and replacement
    :param gen_pattern:
    :param gen_repl:
    :param undo_repl: tuple/tuple list of regex pattern and replacement to undo temporary
    :return:
    """
    # do temp replacement
    if isinstance(temp_repl, list):
        temp_repl_list = temp_repl
        undo_repl_list = undo_repl
    else:
        temp_repl_list = [temp_repl]
        undo_repl_list = [undo_repl]
    wip_line = raw_line
    for pattern, repl in temp_repl_list:
        wip_line = re.sub(pattern, repl, wip_line)
    # go general sub
    wip_line = re.sub(gen_pattern, gen_repl, wip_line)
    # undo temp replacement
    for pattern, repl in undo_repl_list:
        wip_line = re.sub(pattern, repl, wip_line)
    return wip_line


def get_line_contents(raw_line):
    """ Standardise the json format in the string """
    # convert json entries like ['validated': False] to ["validated": "False"]
    # - handle case like ["text":"etc. \nJohn: True etc."]
    wip_line = temp_replace(raw_line,
                            (r"(\"text\":\"[\w\W]+)\\n(\w+): True",
                                lambda m: m.group(1) + r"\n" + m.group(2) + ": #True#"),
                            r": True([,}])", lambda m: ': "True"' + m.group(1),
                            (r"(\"text\":\"[\w\W]+)\\n(\w+): #True#",
                                lambda m: m.group(1) + r"\n" + m.group(2) + ": True"))

    wip_line = re.sub(r": False([,}])", lambda m: ': "False"' + m.group(1), wip_line)
    # - handle case like ["text":"My dad etc. etc. Roasted Red Pepper 'Htipiti': barrel-aged feta, etc."]
    wip_line = temp_replace(wip_line,
                            (r"(\"text\":\"[\w\W]+)'(\w+)':", lambda m: m.group(1) + "#'#" + m.group(2) + "#'#:"),
                            r"'(\w+)':", lambda m: '"' + m.group(1) + '":',
                            (r"(\"text\":\"[\w\W]+)#'#(\w+)#'#:", lambda m: m.group(1) + "'" + m.group(2) + "':"))

    # convert json entries like ['dairy-free':] to ["dairy-free":]
    # - handle case like ["text":"etc. 'double-pita': etc."]
    wip_line = temp_replace(wip_line,
                            (r"(\"text\":\"[\w\W]+)'(\w+)-(\w+)':",
                                lambda m: m.group(1) + "#'#" + m.group(2) + '-' + m.group(3) + "#'#:"),
                            r"'(\w+)-(\w+)':", lambda m: '"' + m.group(1) + '-' + m.group(2) + '":',
                            (r"(\"text\":\"[\w\W]+)#'#(\w+)-(\w+)#'#:",
                             lambda m: m.group(1) + "'" + m.group(2) + '-' + m.group(3) + "':"))

    # convert json entries like ["{]/[}"] to [{]/[}], i.e. start end of json objects embedded as strings
    # - handle case like ["text":"{{First off, etc.}} etc."]
    # - handle case like ["text":"{Cà Phê Sa Đá ~ Vietnamese Ice Coffee with Condense Milk} etc."]
    # - handle case like ["text":"{just etc."]
    # - handle case like ["caption": "{.: clockwise .:} etc."]
    # TODO - handle case like ["text":"I etc. respose :\"{sigh}..what did you want...{frown\/look\/awkwardness}\". etc."]
    wip_line = temp_replace(wip_line,
                            [(r"(\"text\":\")\{{2}([\w ,.\\]+)", lambda m: m.group(1) + "#{{#" + m.group(2)),
                                (r"(\"text\":\")\{([\w\W]+)\}([\w\W]+)\"",
                                    lambda m: m.group(1) + "#{#" + m.group(2) + r"#}#" + m.group(3) + r'"'),
                                (r"(\"text\":\")\{([\w\W]+)\"", lambda m: m.group(1) + "#{#" + m.group(2) + r'"'),
                                (r"(\"caption\":\s*\")\{([.: ]+[\w\W]+[.: ]+)\}",
                                    lambda m: m.group(1) + "#{#" + m.group(2) + "#}#")],
                            r"\"{", "{",
                            [(r"(\"text\":\")#\{{2}#([\w ,.\\]+)", lambda m: m.group(1) + "{{" + m.group(2)),
                                (r"(\"text\":\")#\{#([\w\W]+)#\}#([\w\W]+)\"",
                                    lambda m: m.group(1) + "{" + m.group(2) + r"}" + m.group(3) + r'"'),
                                (r"(\"text\":\")#\{#([\w\W]+)\"", lambda m: m.group(1) + "{" + m.group(2) + r'"'),
                                (r"(\"caption\":\s*\")#\{#([.: ]+[\w\W]+[.: ]+)#\}#",
                                    lambda m: m.group(1) + "{" + m.group(2) + "}")])
    # - handle case like ["name":"Small Flower {floral studio}"]
    #                    ["text":"After etc. {Sorry but I forgot his name}"
    #                    ["caption": "Linquine {Schreiners sausage, clams, shrimp, tomato, artichoke}"]
    # - handle case like ["text":"I etc. :}"]
    #                    ["text":"I etc. :+}"]
    #                    ["text":"I etc. - }"]
    wip_line = temp_replace(wip_line,
                            [(r"\"(text|name|caption)(\":\s*\"[\w\W]+)\{([\w\W]+)\}\"",
                                lambda m: r'"' + m.group(1) + m.group(2) + r"#{#" + m.group(3) + r"#}#" + r'"'),
                                (r"(\"text\":\")([^{][\w\W]+)([: +-;^]+)\}\"",
                                    lambda m: m.group(1) + m.group(2) + m.group(3) + r"#}#" r'"')],
                            r"}\"([,}])", lambda m: '}' + m.group(1),
                            [(r"\"(text|name|caption)(\":\s*\"[\w\W]+)#\{#([\w\W]+)#\}#\"",
                                lambda m: r'"' + m.group(1) + m.group(2) + r"{" + m.group(3) + r'}"'),
                                (r"(\"text\":\")([^{][\w\W]+)([: +-;^]+)#\}#\"",
                                    lambda m: m.group(1) + m.group(2) + m.group(3) + r"}" r'"')])

    # convert json entries like ["WiFi":"u'no'"] to ["WiFi":"no"]
    wip_line = re.sub(r"\"u'(\w+)'\"", lambda m: '"' + m.group(1) + '"', wip_line)

    # convert json entries like ["Alcohol":"'none'"] to ["Alcohol":"none"]
    wip_line = re.sub(r"'(\w+)'", lambda m: m.group(1), wip_line)

    # convert json entries like ["xyz": None] to ["xyz": "None"]
    # - handle case like ["text":"5 Star Happy Hour. Bar None, one the etc."]
    # - handle case like ["text":"Restaurant etc. \nNone, etc."]
    #                    ["text":"etc. \nSeating: None, one the etc."]
    # - handle case like ["text":"etc. ins! None, one the etc."]
    wip_line = temp_replace(wip_line,
                            [(r"(\"text\":\"[\w\W]+)([.?,]+)([\w ]*)None,",
                                lambda m: m.group(1) + m.group(2) + m.group(3) + "None#,#"),
                                (r"(\"text\":\"[\w\W]+)\\n([\w: ]*)None,",
                                    lambda m: m.group(1) + r"\n" + m.group(2) + r"None#,#"),
                                (r"(\"text\":\"[\w\W]+)! None,", lambda m: m.group(1) + r"! None#,#")],
                            r"(?<!\")None([,}])", lambda m: '"None"' + m.group(1),
                            [(r"(\"text\":\"[\w\W]+)([.?,]+)([\w ]*)None#,#",
                                lambda m: m.group(1) + m.group(2) + m.group(3) + "None,"),
                                (r"(\"text\":\"[\w\W]+)\\n([\w: ]*)None#,#",
                                    lambda m: m.group(1) + r"\n" + m.group(2) + r"None,"),
                                (r"(\"text\":\"[\w\W]+)! None#,#", lambda m: m.group(1) + r"! None,")])

    line_contents = json.loads(wip_line)

    return line_contents


def get_superset_of_column_names_from_file(json_file_path, skip=0):
    """Read in the json dataset file and return the superset of column names."""
    column_names = set()
    with open(json_file_path) as fin:
        count = 1
        for line in fin:
            if skip <= 0:
                line_contents = get_line_contents(line)
                column_names.update(
                        set(get_column_names(line_contents).keys())
                        )
                if count % 100 == 0:
                    print(f"Scanning: {count}", end="\r", flush=True)
            else:
                skip -= 1
            count += 1
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
    parser.add_argument(
        '-s',
        type=int,
        help='Skip lines',
        default=0,
        required=False
    )

    args = parser.parse_args()

    json_file = args.json_file
    csv_file = '{0}.csv'.format(json_file.split('.json')[0])

    print(f"Converting '{json_file}' to '{csv_file}'")

    print(f"Retrieving column names")
    column_names = get_superset_of_column_names_from_file(json_file, 0) #2512200)
    print(f"{len(column_names)} column names identified")
    if args.v:
        print(f"{column_names}")

    print(f"Processing json file")
    read_and_write_file(json_file, csv_file, column_names)
