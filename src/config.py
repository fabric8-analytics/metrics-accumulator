"""Configuration file while starting server."""
from prometheus_client import multiprocess


def child_exit(server, worker):
    """Clear all the PID files for gauge series."""
    multiprocess.mark_process_dead(worker.pid)
