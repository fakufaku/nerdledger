'''
This defines a few importers to process CSV files
'''

import os
import datetime
import yaml
import pandas as pd
import accounting

def isnan(x):
    return x != x

def match(text, typ, rule):
    ''' Simple rule checkers. Some words should be in the text/type '''

    if not isnan(text):
        for word in rule['in_text']:
            if word not in text.lower():
                return False

    if not isnan(typ):
        for word in rule['in_type']:
            if word not in typ.lower():
                return False

    return True

def ubs_visa(filename, output=None, start_date=None, encoding='latin1', rule_file=None):

    # if no name is given, just reuse same location
    if output is None:
        output = os.path.splitext(filename)[0] + '.yml'

    if start_date is not None and not isinstance(start_date, datetime.datetime):
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')

    # the columns names in the UBS csv
    col_names = [
            'account_number',
            'card_number',
            'card_holder',
            'date_purchase',
            'text',
            'type',
            'amount',
            'original_currency',
            'rate',
            'currency',
            'debit',
            'credit',
            'date_written',
            ]

    # read the csv files
    csv = pd.read_csv(filename, sep=';', skiprows=2, header=None, encoding=encoding)
    csv.columns = col_names

    # now load the rules from yaml file
    rules = []
    if rule_file is not None:
        with open(rule_file, 'r') as stream:
            rules = yaml.load(stream)

    transactions = []

    for row in csv.iterrows():

        fields = row[1]

        date_purchase = datetime.datetime.strptime(fields['date_purchase'], '%d.%m.%Y')

        # skip if before start date (when provided)
        if start_date is not None and date_purchase < start_date:
            continue

        # let's only handle debit here
        if isnan(fields['debit']):
            continue

        # skip the balance report
        if fields['text'] == 'Report de solde':
            continue

        destination_account = '<TBA>'
        for rule in rules:
            if match(fields['text'], fields['type'], rule):
                destination_account = rule['to']
                break

        new_transactions = {
                'from':        'visa_credit_card',
                'to':          destination_account,
                'amount':      round(fields['debit'], 2),
                'description': '{} {}'.format(fields['text'], fields['type']),
                'date': date_purchase,
                }

        transactions.append(new_transactions)

    with open(output, 'w') as f:
        yaml.dump(transactions, stream=f, default_flow_style=False)
