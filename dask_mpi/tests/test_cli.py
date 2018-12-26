from __future__ import print_function, division, absolute_import
import os
import sys

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess
from time import sleep

import pytest
pytest.importorskip('mpi4py')

import requests

from distributed import Client
from distributed.metrics import time
from distributed.utils import tmpfile
from distributed.utils_test import popen
from distributed.utils_test import loop  # noqa: F401

FNULL = open(os.devnull, 'w') # hide output of subprocess

@pytest.mark.parametrize('nanny', ['--nanny', '--no-nanny'])
def test_basic(loop, nanny):
    with tmpfile(extension='json') as fn:
        with popen(['mpirun', '--np', '4', 'dask-mpi', '--scheduler-file', fn, nanny], stdin=FNULL):
            with Client(scheduler_file=fn) as c:
                start = time()
                n_workers = len(c.scheduler_info()['workers'])
                while n_workers != 3:
                    n_workers = len(c.scheduler_info()['workers'])
                    print('n_workers = ', n_workers)
                    assert time() < start + 10
                    sleep(0.2)

                assert c.submit(lambda x: x + 1, 10, workers='mpi-rank-1').result() == 11


def test_no_scheduler(loop):
    with tmpfile(extension='json') as fn:
        with popen(['mpirun', '--np', '2', 'dask-mpi', '--scheduler-file', fn], stdin=FNULL):
            with Client(scheduler_file=fn) as c:

                start = time()
                while len(c.scheduler_info()['workers']) != 1:
                    assert time() < start + 10
                    sleep(0.2)

                assert c.submit(lambda x: x + 1, 10).result() == 11
                with popen(['mpirun', '--np', '1', 'dask-mpi', '--scheduler-file', fn, '--no-scheduler']):

                    start = time()
                    while len(c.scheduler_info()['workers']) != 2:
                        assert time() < start + 10
                        sleep(0.2)

@pytest.mark.skip
def test_bokeh(loop):
    with tmpfile(extension='json') as fn:
        with popen(['mpirun', '--np', '2', 'dask-mpi', '--scheduler-file', fn,
                    '--bokeh-port', '59583', '--bokeh-worker-port', '59584'],
                   stdin=subprocess.DEVNULL):

            for port in [59853, 59584]:
                start = time()
                while True:
                    try:
                        response = requests.get('http://localhost:%d/status/' % port)
                        assert response.ok
                        break
                    except Exception:
                        sleep(0.1)
                        assert time() < start + 20

        with pytest.raises(Exception):
            requests.get('http://localhost:59583/status/')