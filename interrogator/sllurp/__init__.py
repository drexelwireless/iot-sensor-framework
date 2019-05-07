"""Low Level Reader Protocol implemtnation in pure Python
"""


from pkg_resources import get_distribution


__all__ = ('llrp', 'llrp_decoder', 'llrp_errors', 'llrp_proto', 'util')
           #, 'inventory') # mongan 5/6/19
__version__ = 1 # mongan 5/6/19 get_distribution('sllurp').version
