# -*- coding: utf-8 -*-
'''
Copyright (c) 2020 Victor Wåhlström

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
claim that you wrote the original software. If you use this software
in a product, an acknowledgment in the product documentation would be
appreciated but is not required.

2. Altered source versions must be plainly marked as such, and must not be
misrepresented as being the original software.

3. This notice may not be removed or altered from any source
'''

# Quick and dirty script to help modify custom spell data for the 5th Edition Spellbook app (https://play.google.com/store/apps/details?id=com.spellsdd5)

import os
import argparse
import json


_default_data = {'id': -1,
                 'name': 'aoeu',
                 'school': 'Abjuration Cantrip',
                 'level': -1,
                 'casting_time': '1 Action',
                 'range': 'None',
                 'components': '',
                 'duration': '1 Round',
                 'description': '<p>aeu<br></p>',
                 'description_high': '',
                 'book': '',
                 'note': '',
                 'classes': '',
                 'concentration': 'false',
                 'ritual': 'false',
                 'sound': '',
                 'is_edit': False}


class InvalidDataError(Exception):
    pass


def validate_data(data):
    '''
    Validates data. Raises InvalidDataError if with verbose information if an error was encountered

    :param data: loaded spellbook data
    '''

    # TODO: check more things, like version strings, etc.

    if len(data) < 3:
        raise InvalidDataError('Expected data to contain at least three entries')

    if 'data' not in data[2]:
        raise InvalidDataError('Expected dictionary with "data" key at index 2 in input data')

    internal_data = data[2]['data']

    keys = _default_data.keys()

    for item in internal_data:
        for key in keys:
            if key not in item:
                raise InvalidDataError("{} missing from {}".format(key, item))


def clean_classes(data, valid_classes, correct_partial_names=False):
    '''
    Clean the "classes" entries in input data according to valid_classes.
    Unknown classes will be stripped, and casing will be normalized according to valid_classes.
    The final output will be sorted according to the order in valid_classes

    :note: The patching is done in-place

    :note: This function is case insensitive

    :param data: loaded data to patch
    :param valid_classes: A list of class names for which all entries should be checked against
    '''

    def _to_list(classes):
        return [n.strip() for n in classes.split(',')]

    def _to_str(classes):
        return ', '.join(classes)

    def _lowercase_list(lst):
        return [n.lower() for n in lst]

    internal_data = data[2]['data']

    for item in internal_data:
        classes = item.get('classes')
        if classes:
            valid_classes_lowercase = _lowercase_list(valid_classes)

            # remove duplicates
            class_list = _lowercase_list(_to_list(classes))
            unique_classes = set(class_list)
            if len(class_list) != len(unique_classes):
                print('Removing duplicates from "{}"'.format(item.get('name')))

            # remove invalid classes
            invalid_classes = unique_classes - set(valid_classes_lowercase)

            if invalid_classes:
                if correct_partial_names:
                    for c in invalid_classes:
                        for vc in valid_classes_lowercase:
                            if c.startswith(vc):
                                print('WARNING: Replacing "{}" with "{}" in "{}"'.format(c, vc, item.get('name')))
                                unique_classes.remove(c)
                                unique_classes.add(vc)
                    invalid_classes = unique_classes - set(valid_classes_lowercase)

            if invalid_classes:
                print('WARNING: "{}" contains the following invalid classes: "{}". They will be removed'.format(item.get('name'), ', '.join(invalid_classes)))
                unique_classes = unique_classes - invalid_classes

            # sort classes according to the order of valid_classes
            classes = sorted(unique_classes, key=lambda k: valid_classes_lowercase.index(k))
            # match casing in valid_classes
            classes = [valid_classes[valid_classes_lowercase.index(n)] for n in classes]

            item['classes'] = _to_str(classes)


def patch_missing_fields(data):
    '''
    Adds missing fields with default values to input data, in-place

    :param data: loaded data to patch
    '''

    # index 2 contains actual data for each spell
    # update it with default data for each missing key
    internal_data = data[2]['data']

    for i, item in enumerate(internal_data):
        internal_data[i] = dict(_default_data, **item)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_data', required=True, type=str, help='Path to spellbook data that should be processed')
    parser.add_argument('--output_data', type=str, help='Path to output file to write')
    parser.add_argument('--pretty_print', action='store_true', help='Add indentation and newline to output file')
    parser.add_argument('--correct_partial_classnames', action='store_true', help='Optional argument for "clean_classes". Will replace classes entries with valid class names for entries that contain a partial match but is not exactly identical.')
    parser.add_argument('--valid_classes', required=False, nargs='*', help='A list of valid classes. Only required for options that process class data. Can be empty, in which case there are no valid classes.')
    parser.add_argument('--process_type', type=str, choices=['patch', 'clean_classes', 'validate'], default='validate',
                        help='What do you want to do with the data? Valid choices are: '
                             '"patch" [patches missing data fields], '
                             '"clean_classes" [Cleans up the "classes" field of each entry, removing duplicates, invalid entries, and sorting the result. If this option is chosen, please set --valid_classes] '
                             '"validate" [validates input data, does not write to output]')

    args = parser.parse_args()

    if not os.path.isfile(args.input_data):
        raise Exception('"{}" not found!'.format(args.input_data))

    with open(args.input_data, 'r', encoding='utf8') as f:
        data = json.loads(f.read())

    if args.process_type == 'validate':
        validate_data(data)
    elif args.process_type == 'patch':
        patch_missing_fields(data)
    elif args.process_type == 'clean_classes':
        if args.valid_classes is None:
            raise Exception('clean_classes option requires that a list of valid classes is provided via --valid_classes')
        clean_classes(data, args.valid_classes, correct_partial_names=args.correct_partial_classnames)
    else:
        raise NotImplementedError('process_type "{}" is not a valid choice'.format(args.process_type))

    if args.output_data:
        print('Writing "{}"'.format(os.path.abspath(args.output_data)))
        with open(args.output_data, 'w', encoding='utf8') as f:
            f.write(json.dumps(data, sort_keys=True, indent=4 if args.pretty_print else None, ensure_ascii=False))
