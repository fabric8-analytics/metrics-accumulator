"""Test the config file for metrics collector service."""
import os
from src.config import *
from collections import namedtuple


def test_config():
    """Test config file."""
    worker = {'pid': os.getpid()}
    wkr_struct = namedtuple('Struct', worker.keys())(*worker.values())
    child_exit('server', wkr_struct)
