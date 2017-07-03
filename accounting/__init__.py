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

from .accounting import *
from .from_csv import *
