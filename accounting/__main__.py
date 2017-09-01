'''
This script imports a database file into a ledger.
Its single argument is the name of the database file.
'''
import argparse
import accounting

# parse arguments
parser = argparse.ArgumentParser(description='Start accounting in ipython.')
parser.add_argument('db_file', type=str,
                    help='the accounting database file')

args = parser.parse_args()

# load the database
ledger = accounting.Ledger(args.db_file)

# print a friendly message
print('')
print('********==================================********')
print('Welcome to Accounting. A simple accounting system!')
print('********==================================********')
print('')
print('As a start here''s what your accounts looks like:')
print('')
print(ledger)
