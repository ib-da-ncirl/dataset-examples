# -*- coding: utf-8 -*-
"""Convert the Yelp Dataset Challenge dataset from json format to csv.

For more information on the Yelp Dataset Challenge please visit http://yelp.com/dataset_challenge

-------------------------------------------------------------------------------------------------
Original source provided by Yelp and available from
https://github.com/Yelp/dataset-examples/blob/master/json_to_csv_converter.py
Updated to:
- Decode json objects embedded as strings
- Display processed metrics
- Added verbose, regex and skip lines arguments
- Added time_count argument to replace 'YYYY-MM-DD HH:MM:SS' text with a count representing number of timestamps

Example usage:
- python3 json_to_csv_converter yelp_dataset/yelp_academic_dataset_review.json
- python3 json_to_csv_converter yelp_dataset/yelp_academic_dataset_tip.json
- python3 json_to_csv_converter yelp_dataset/yelp_academic_dataset_user.json
- python3 json_to_csv_converter -tc yelp_dataset/yelp_academic_dataset_checkin.json
- python3 json_to_csv_converter yelp_photos/photos.json
- python3 json_to_csv_converter -r yelp_dataset/yelp_academic_dataset_business.json
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


def read_and_write_file(json_file_path, csv_file_path, column_names, skip_l=0, regex_lc=True, time_lc=False, crlf=False):
    """Read in the json dataset file and write it out to a csv file, given the column names."""
    with open(csv_file_path, 'w', encoding='utf-8') as fout:
        csv_file = csv.writer(fout, quoting=csv.QUOTE_MINIMAL)
        csv_file.writerow(list(column_names))
        with open(json_file_path) as fin:
            count = 1
            for line in fin:
                if skip_l <= 0:
                    line_contents = get_line_contents(line, regex_contents=regex_lc, time_count=time_lc, crlf=crlf)
                    csv_file.writerow(get_row(line_contents, column_names))
                    if count % 100 == 0:
                        print(f"Line: {count}", end="\r", flush=True)
                else:
                    skip_l -= 1
                count += 1
            print(f"Processed {count} lines")


def process(content, res, regex_contents=True, time_count=False, crlf=False):
    """ Process a dictionary of json key/value pairs """
    for k, v in content:
        if isinstance(v, collectionsAbc.MutableMapping):
            res[k] = {}
            process(v.items(), res[k], regex_contents=regex_contents, time_count=time_count)
        elif isinstance(v, str):
            if re.match(r"^\{.*[:].*\}$", v):
                # looks like a string encoded json object
                if regex_contents:
                    # convert json entries like ['validated': False] to ["validated": "False"]
                    v = re.sub(r"\'([\w]+)\':", lambda m: r'"' + m.group(1) + r'":', v)
                    v = re.sub(r": (True|False|None)", lambda m: r':"' + m.group(1) + r'"', v)

                    # convert json entries like ['dairy-free':] to ["dairy-free":]
                    v = re.sub(r"\'(\w+)-(\w+)\':", lambda m: r'"' + m.group(1) + '-' + m.group(2) + r'":', v)

                    # convert json entries like ["WiFi":"u'no'"] to ["WiFi":"no"]
                    v = re.sub(r"\"u'(\w+)'\"", lambda m: '"' + m.group(1) + '"', v)

                    # convert json entries like ["Alcohol":"'none'"] to ["Alcohol":"none"]
                    v = re.sub(r"'(\w+)'", lambda m: m.group(1), v)

                res[k] = get_line_contents(v, regex_contents=regex_contents, time_count=time_count, crlf=crlf)
            else:
                # replace cr/lf by spaces as they cause problems for pandas when reading large csv files
                if crlf:
                    v = re.sub(r"[\n]+", " ", v)
                    v = re.sub(r"[\r]+", " ", v)

                if regex_contents:
                    # convert json entries like ["WiFi":"u'no'"] to ["WiFi":"no"]
                    v = re.sub(r"u'(\w+)'", lambda m: m.group(1), v)
                    v = re.sub(r"'(\w+)'", lambda m: m.group(1), v)

                if time_count:
                    # replace all 'YYYY-MM-DD HH:MM:SS' entries with a single total count
                    match = re.findall(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[, ]{0,2}", v)
                    if match:
                        v = re.sub(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[, ]{0,2})+", lambda m: str(len(match)), v)

                res[k] = v
        else:
            res[k] = v


def get_line_contents(raw_line, regex_contents=True, time_count=False, crlf=False):
    """ Standardise the json format in the string """
    line_contents = json.loads(raw_line)

    result = {}
    process(line_contents.items(), result, regex_contents=regex_contents, time_count=time_count, crlf=crlf)

    return result


def get_superset_of_column_names_from_file(json_file_path, skip_l=0, regex_lc=True, time_lc=False, crlf=False):
    """Read in the json dataset file and return the superset of column names."""
    column_names = set()
    with open(json_file_path) as fin:
        count = 1
        for line in fin:
            if skip_l <= 0:
                line_contents = get_line_contents(line, regex_contents=regex_lc, time_count=time_lc, crlf=crlf)
                column_names.update(
                        set(get_column_names(line_contents).keys())
                        )
                if count % 100 == 0:
                    print(f"Scanning: {count}", end="\r", flush=True)
            else:
                skip_l -= 1
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
        '-v', '--verbose',
        help='Verbose mode',
        action='store_true'
    )
    parser.add_argument(
        '-s', '--skip',
        type=int,
        help='Skip lines',
        default=0,
        # required=False
    )
    parser.add_argument(
        '-tc', '--time_count',
        action='store_true',
        help="Replace 'YYYY-MM-DD HH:MM:SS' text with a count representing number of timestamps",
    )
    parser.add_argument(
        '-r', '--regex',
        action='store_true',
        help='Enable regex',
    )
    parser.add_argument(
        '-c', '--crlf',
        action='store_false',
        help='Disable CR/LF replacement',
    )

    args = parser.parse_args()

    json_file = args.json_file
    csv_filename = '{0}.csv'.format(json_file.split('.json')[0])

    print(f"Converting '{json_file}' to '{csv_filename}'")

    if args.verbose:
        print(f"Arguments: {args}")

    # args.skip = 5724400
    if args.skip > 0:
        print(f"Skipping {args.skip} lines")

    print("Retrieving column names")
    column_names = get_superset_of_column_names_from_file(
        json_file, skip_l=args.skip, regex_lc=args.regex, time_lc=args.time_count, crlf=args.crlf)
    print(f"{len(column_names)} column names identified")
    if args.verbose:
        print(f"{column_names}")

    print("Processing json file")
    read_and_write_file(json_file, csv_filename, column_names, skip_l=args.skip, regex_lc=args.regex,
                        time_lc=args.time_count, crlf=args.crlf)
