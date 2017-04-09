'''
This is a simple accounting software for home finances
'''

from __future__ import division, print_function

import dataset
import datetime

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

        self.name = name
        self.db = db

        itself = self.db['accounts'].find_one(name=self.name)

        if 'type' in itself:
            self.type = itself['type']
        else:
            self.type = None

        if 'opening_balance' in itself:
            if itself['opening_balance'] is None:
                self.opening_balance = 0.
                self.db['accounts'].update(dict(name=self.name, opening_balance=0.), ['name'])
            else:
                self.opening_balance = itself['opening_balance']
        else:
            self.opening_balance = 0.

        self.record_template = (u"{id:>5}  {date:10.10}  {description:40.40} "
                              + u"{destination:30.30} {source:30.30} "
                              + u"{amount: 8.2f} {0: 8.2f}")

    def set_type(self, account_type):
        ''' Updates the account type (account or expense) '''

        if account_type == 'income' or account_type == 'expense' or account_type == 'credit':
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

    def balance(self, make_str=False):
        '''
        String representation of the account. We format and print all transactions
        '''

        if make_str:
            s =  u'Account: {} (type: {})\n'.format(self.name, self.type)
            s += u''.join('-' for c in s) + '\n'

        # get the account types
        accounts_rec = self.db['accounts'].all()
        account_types = dict()
        for acc in accounts_rec:
            account_types[acc['name']] = acc['type']


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

        for transaction in transactions:
            number_records += 1

            # This is wrong, we need to know if this is income or expanse account
            src = transaction['source']
            dst = transaction['destination']

            if account_types[dst] == 'credit':
                transaction['amount'] *= -1

            if self.name == src:
                balance -= transaction['amount']
            elif self.name == dst:
                balance += transaction['amount']

            if make_str:
                s += self.record_template.format(balance, **transaction) + '\n'

        if make_str:
            s += u'Number of transactions: {}'.format(number_records)
            return s
        else:
            return balance

    def __str__(self):
        s = '{:30.30}  {:10.10}  {:8.2f}'.format(self.name, self.type, self.balance())
        return s

    def __repr__(self):
        return self.balance(make_str=True)


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
            raise ValueErro('No such account')

        return getattr(self, 'a_' + account_name)

    def __repr__(self):
        ''' This will print the balances of all accounts '''

        s =  u'List of accounts:\n'
        s += u''.join('-' for c in s) + '\n'
        for account in sorted(self.accounts):
            s += self[account].__str__() + '\n'

        return s

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
            description=None, date=None):
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
        date:  str or datetime.datetime
            Date of the transaction
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

        # we probably want to sent back a string with last few rows of both accounts
