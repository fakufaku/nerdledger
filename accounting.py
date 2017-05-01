'''
Accounting
==========

This is a simple accounting software for home finances.

It is designed to take advantage of autocompletion in the ipython console and
to allow for batch processing for monthly payments.

>>> import accounting
>>> ledger = accounting.Ledger('my_ledger.db')
>>> ledger.a_light_and_heat.balance_sheet()
>>> ledger.transfer(250.30, ledger.a_bank, ledger.a_health_insurance, description='Monthly premiums')
'''

from __future__ import division, print_function

import dataset
import datetime

allowed_account_types = [
    'bank',
    'credit',
    'income',
    'expense',
    ]

class Account:
    '''
    Attributes
    ----------
    name: str
        name of the account
    db: sqlite db
        underlying database
    '''

    def __init__(self, name, db):
        '''
        Initialize account

        Parameters
        ----------
        name: str
            Unique name of the account
        db: dataset object
            Link to the sqlite database through dataset module
        '''

        self.name = name
        self.db = db

        # extract account info from the db
        itself = self.db['accounts'].find_one(name=self.name)

        # set type if available
        if 'type' in itself:
            self.type = itself['type']
        else:
            self.type = None

        # set balance if available
        if 'opening_balance' not in itself or itself['opening_balance'] is None:
            # set to zero if this was never done
            self.opening_balance = 0.
            self.db['accounts'].update(dict(name=self.name, opening_balance=0.), ['name'])
        else:
            self.opening_balance = itself['opening_balance']

    def set_type(self, account_type):
        ''' Updates the account type (account or expense) '''

        if account_type in allowed_account_types:
            data = dict(name=self.name, type=account_type)
            self.db['accounts'].update(data, ['name'])
            self.type = account_type
        else:
            raise ValueError("The account type can be 'income' or 'expense'.")

    def set_opening_balance(self, balance):
        ''' Updates the account opening balance '''

        self.opening_balance = balance
        data = dict(name=self.name, opening_balance=balance)
        self.db['accounts'].update(data, ['name'])

    def transactions(self):
        '''
        String representation of the account. We format and print all transactions
        '''
        # query the db for all transactions involving this account
        query_string = ( 
                         'SELECT * FROM transactions '
                       + 'WHERE transactions.source==\'{0}\' '
                       + 'OR transactions.destination==\'{0}\' '
                       + 'ORDER BY transactions.date' 
                       ).format(self.name)
        transactions = self.db.query(query_string)

        # keep track of account balance and number of transactions
        balance = self.opening_balance
        number_records = 0

        # add balance to transactions and store in list
        all_transactions = []
        for transaction in transactions:
            number_records += 1

            # This is wrong, we need to know if this is income or expanse account
            src = transaction['source']
            dst = transaction['destination']

            if self.name == src:
                balance -= transaction['amount']
            elif self.name == dst:
                balance += transaction['amount']

            transaction['balance'] = balance

            all_transactions.append(transaction)

        return all_transactions

    def balance(self, display=True):
        ''' 
        Computes balance of account. Optional display argument to use
        accounting sign convention (income and credit increase on withdrawal)
        '''
        if display:
            sign = -1 if self.type == 'credit' or self.type == 'income' else 1
        else:
            sign = 1
        return sign * round(self.transactions()[-1]['balance'],2)

    def balance_sheet(self, limit=None):

        # count lines form the most recent one when limiting
        if limit is not None:
            limit *= -1

        # Template for one line
        '''
        line = (u"{id:>5}  {date:10.10}  {description:40.40} "
              + u"{destination:30.30} {source:30.30} "
              + u"{amount: 8.2f} {balance: 8.2f}")
        '''

        line_in = (u"{id:>5}  {date:10.10}  {description:40.40} "
                + u"{0:30.30} "
              + u"{1: 8.2f}              "
              + u"{2: 8.2f}")
        line_out = (u"{id:>5}  {date:10.10}  {description:40.40} "
                + u"{0:30.30} "
              + u"             {1: 8.2f} "
              + u"{2: 8.2f}")

        s =  u'Account: {} (type: {})\n'.format(self.name, self.type)
        s += u''.join('-' for c in s) + '\n'

        # balance sign is inverted for income or credit account
        sign = -1 if self.type == 'income' or self.type == 'credit' else 1

        transactions = self.transactions()
        for transaction in transactions[limit:]:

            # identify account 2
            if transaction['source'] == self.name:
                account_2 = transaction['destination']
                direction = 'in' if transaction['amount'] < 0 else 'out'
            else:
                account_2 = transaction['source']
                direction = 'in' if transaction['amount'] > 0 else 'out'

            print(direction)

            if direction == 'in':
                s += line_in.format( account_2, abs(transaction['amount']), 
                        sign * transaction['balance'],
                        **transaction
                        ) + '\n'
            else:
                s += line_out.format( account_2, abs(transaction['amount']),
                        sign * transaction['balance'],
                        **transaction
                        ) + '\n'

        if limit is None:
            s += u'Number of transactions: {}'.format(len(transactions))

        return s

    def __str__(self):
        s = '{:30.30}  {:10.10}  {:8.2f}'.format(self.name, self.type, self.balance())
        return s

    def __repr__(self):
        return self.balance_sheet()


class Ledger:
    '''
    This is the main class that implements our big accounting book
    '''

    def __init__(self, db_file):

        self.db_file = db_file
        self.db = dataset.connect('sqlite:///' + db_file)

        # keep track of valid account names
        self.accounts = set()

        # Each of the accounts is an attribute so that we can use ipython autocomplete
        # prefix with 'a_' to avoid confusion with regular attributes and methods
        for row in self.db['accounts']:
            self.accounts.add(row['name'])
            setattr(self, 'a_' + row['name'], Account(row['name'], self.db))

    def __getitem__(self, account_name):
        ''' Access accounts using the bracket operator too '''
        # error checking
        if account_name not in self.accounts:
            raise ValueError('No such account')

        return getattr(self, 'a_' + account_name)

    def __repr__(self):
        ''' This will print the balances of all accounts '''

        s =  u'List of accounts:\n'
        s += u''.join('-' for c in s) + '\n'

        # sort accounts by type
        a_by_t = dict()
        for a_type in allowed_account_types:
            a_by_t[a_type] = []
        for a in self.accounts:
            a_by_t[self[a].type].append(a)

        # Print each account category separately
        for a_type in allowed_account_types:
            s += a_type.upper() + ':\n'
            for a in sorted(a_by_t[a_type]):
                s += '  ' + '{:30.30}  {: 12.2f}'.format(self[a].name, self[a].balance()) + '\n'
            s += '\n'

        # remove final newline
        return s[:-1]

    def open_account(self, name, type='expense', balance=0.):
        ''' Create a new account '''

        if name in self.accounts:
            raise ValueError('Account name already exists')

        # add to database
        self.db['accounts'].insert(dict(name=name, type=type, balance=balance))

        # add to local lists
        self.accounts.add(name)
        setattr(self, 'a_' + name, Account(name, self.db))

    def transfer(self, 
            amount, source_account, destination_account,
            description=None, date=None,
            summary=True):
        ''' 
        Add a transaction in the ledger
        
        Parameters
        ----------
        amount: int or float
            Amount of transaction
        source: str or Account object
            Source account
        destination: str or Account object
            Destination account
        description: str, optional
            Description of the transaction
        date: str or datetime.datetime, optional
            Date of the transaction (default now)
        summary: boolean, optional
            Prints a summary of source and destination account (default True)
        '''

        if description is None:
            description = ''

        new_transaction = dict(amount=amount, description=description)

        # source account name. allow for strings or objects
        if isinstance(source_account, Account):
            new_transaction['source'] = source_account.name
        elif isinstance(source_account, str):
            if source_account not in self.accounts:
                raise ValueError('{}: no such account'.format(source_account))
            new_transaction['source'] = source_account
        else:
            raise ValueError('Accounts should be strings or Account objects')

        # destination account name. allow for strings or objects
        if isinstance(destination_account, Account):
            new_transaction['destination'] = destination_account.name
        elif isinstance(destination_account, str):
            if destination_account not in self.accounts:
                raise ValueError('{}: no such account'.format(destination_account))
            new_transaction['destination'] = destination_account
        else:
            raise ValueError('Accounts should be strings or Account objects')

        # parse the date
        if date is not None:
            if isinstance(date, datetime.datetime):
                new_transaction['date'] = date
            elif isinstance(destination_account, str):
                new_transaction['date'] = datetime.datetime.strptime(date, '%Y-%m-%d')
        else:
            new_transaction['date'] = datetime.datetime.now()

        # timestamp creation of transaction
        new_transaction['date_created'] = datetime.datetime.now()

        # write to db
        self.db['transactions'].insert(new_transaction)

        # Print summary of both accounts
        if summary:
            s = self[new_transaction['source']].balance_sheet(limit=5)
            s += self[new_transaction['destination']].balance_sheet(limit=5)
            print(s, end='')
