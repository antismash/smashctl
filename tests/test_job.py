from antismash_models import SyncJob as Job
from argparse import Namespace
import pytest

from smashctl.common import AntismashRunError
from smashctl import job


def test_show_simple(db):
    j = Job(db, 'bacteria-fake')
    j.commit()
    args = Namespace(job_id='bacteria-fake')

    expected = "{job.job_id}\t{job.dispatcher}\t{job.added}\t{job.last_changed}\t{job.email}\t{job.state}\t{job.status}".format(job=j)
    assert job.show(args, db) == expected

    args.job_id = 'bacteria-nonexisting'
    with pytest.raises(AntismashRunError):
        job.show(args, db)


def test_joblist_simple(db):
    running_jobs = [
        Job(db, 'bacteria-1'),
        Job(db, 'bacteria-2'),
    ]

    queued_jobs = [
        Job(db, 'bacteria-3'),
        Job(db, 'bacteria-4'),
        Job(db, 'bacteria-5'),
    ]

    expected_lines_running = []
    expected_lines_queued = []

    for j in running_jobs:
        j.commit()
        db.lpush('jobs:running', j.job_id)
        expected_lines_running.insert(0, '{job.job_id}\t{job.jobtype}\t{job.dispatcher}\t{job.email}\t{job.added}\t{job.last_changed}\t{job.filename}{job.download}\t{job.state}\t{job.status}'.format(job=j))

    db.lpush('jobs:running', 'bacteria-fake')

    for j in queued_jobs:
        j.commit()
        db.lpush('jobs:queued', j.job_id)
        expected_lines_queued.insert(0, '{job.job_id}\t{job.jobtype}\t{job.dispatcher}\t{job.email}\t{job.added}\t{job.last_changed}\t{job.filename}{job.download}\t{job.state}\t{job.status}'.format(job=j))

    args = Namespace(queue='queued')
    expected = '\n'.join(expected_lines_queued)
    assert job.joblist(args, db) == expected

    args = Namespace(queue='running')
    expected = '\n'.join(expected_lines_running)
    assert job.joblist(args, db) == expected

    args = Namespace(queue='fake')
    assert job.joblist(args, db) == "No jobs in queue 'fake'"


def test_restart(db):
    j = Job(db, 'bacteria-1')
    j.filename = 'foo.gbk'
    j.commit()
    db.lpush('jobs:running', j.job_id)

    args = Namespace(job_id=j.job_id, queue="jobs:queued")

    # Jobs in 'created' state can't be restarted
    with pytest.raises(AntismashRunError):
        job.restart(args, db)

    j.state = 'running'
    j.commit()

    assert job.restart(args, db) == "Restarted job {}".format(j.job_id)

    assert db.llen('jobs:running') == 0
    assert db.llen('jobs:queued') == 1
    assert db.rpoplpush('jobs:queued', 'jobs:queued') == j.job_id
    j.fetch()
    assert j.state == 'queued'
    assert j.status == 'restarted'
    print(j.to_dict())

    args = Namespace(job_id='bacteria-fake')
    with pytest.raises(AntismashRunError):
        job.restart(args, db)


def test_notify(mocker, db):
    j = Job(db, 'bacteria-fake')
