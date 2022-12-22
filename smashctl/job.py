"""Job management logic"""
import argparse

from antismash_models import SyncJob as Job

from smashctl.common import AntismashRunError, default_action
from smashctl.mail import send_mail, MailConfig


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):  # pragma: no cover
    """Register job subcommands"""
    p_job = subparsers.add_parser('job', help='Show and manipulate jobs')
    p_job.set_defaults(func=default_action(joblist, queue="running", pretty="oneline"))

    job_subparsers = p_job.add_subparsers(title='job-related commands')

    p_show = job_subparsers.add_parser('show', help='Show a job')
    p_show.add_argument('job_id', help="ID of the job to show")
    p_show.add_argument('-p', '--pretty', choices=["oneline", "verbose"], default="oneline",
                        help="Show job in one line or verbose mode (default: %(default)s)")
    p_show.set_defaults(func=show)

    p_list = job_subparsers.add_parser('list', help='List jobs')
    p_list.add_argument('-q', '--queue', default='running',
                        help="What queue to list jobs for (default: %(default)s)")
    p_list.add_argument('-p', '--pretty', choices=["oneline", "verbose"], default="oneline",
                        help="Show jobs in one line per job or verbose mode (default: %(default)s)")
    p_list.set_defaults(func=joblist)

    p_restart = job_subparsers.add_parser('restart', help='Restart a job')
    p_restart.add_argument('job_id', help="ID of the job to restart")
    p_restart.add_argument('-q', '--queue', default="jobs:queued",
                           help="Queue to send the job to (default: %(default)s).")
    p_restart.set_defaults(func=restart)

    p_cancel = job_subparsers.add_parser('cancel', help='Cancel a job')
    p_cancel.add_argument('job_id', help="ID of the job to cancel")
    p_cancel.add_argument('-f', '--force', action="store_true", default=False,
                          help="Force a job to be canceled regardless of status.")
    p_cancel.add_argument('--notify', action="store_true", default=False,
                          help="If user provided an email, send an email notification")
    p_cancel.add_argument('-r', '--reason', default="Manual interrupt",
                          help="Give a reason for canceling the job (default: %(default)s).")
    p_cancel.add_argument('-s', '--state', default="failed", choices=Job.VALID_STATES,
                          help="Set a state for the job (default: %(default)s).")
    p_cancel.set_defaults(func=cancel)

    p_notify = job_subparsers.add_parser('notify', help='Notify user about the job outcome')
    p_notify.add_argument('job_id', help="ID of the job to notify for")
    p_notify.set_defaults(func=notify)


def _format_job(job: Job, format: str = "oneline") -> str:
    """Format a job for printing"""

    if format == "oneline":
        template = '{job.job_id}\t{job.jobtype}\t{job.dispatcher}\t{job.email}\t{job.added}\t{job.last_changed}\t' \
               '{job.filename}{job.download}\t{job.state}\t{job.status}'
    elif format == "verbose":
        template = "{job.job_id}\n"
        for var in sorted(Job.PROPERTIES + Job.ATTRIBUTES):
            template += f"{var} = {{job.{var}}}\n"
    else:
        raise ValueError(f"Invalid format: {format}")

    return template.format(job=job)


def show(args, storage):
    """Handle smashctl job show"""
    try:
        job = Job(storage, args.job_id)
        job.fetch()
    except ValueError as e:
        raise AntismashRunError('Job {} not found in database, {}!'.format(args.job_id, e))

    return _format_job(job, args.pretty)


def joblist(args, storage):
    """Handle listing jobs"""
    queue_key = 'jobs:{}'.format(args.queue)
    result_lines = []

    jobs = storage.lrange(queue_key, 0, -1)
    for job_id in jobs:
        try:
            job = Job(storage, job_id)
            job.fetch()
            result_lines.append(_format_job(job, args.pretty))
        except ValueError:
            pass

    if not result_lines:
        return "No jobs in queue {!r}".format(args.queue)

    return "\n".join(result_lines)


def restart(args, storage):
    """Restart a given job"""
    try:
        job = Job(storage, args.job_id)
        job.fetch()
    except ValueError as e:
        raise AntismashRunError('Job {} not found in database, {}!'.format(args.job_id, e))

    if job.state not in ('queued', 'running', 'done', 'failed'):
        raise AntismashRunError('Job {job.job_id} in state {job.state} cannot be restarted'.format(job=job))

    old_queue = "jobs:{}".format(job.state)
    job.state = 'queued'
    job.status = 'restarted'
    job.dispatcher = ''
    job.target_queues = [args.queue]
    if job.download:
        job.needs_download = True
        job.target_queues.append("jobs:downloads")

    storage.lrem(old_queue, value=job.job_id, count=-1)
    storage.rpush(job.target_queues.pop(), job.job_id)

    job.commit()
    return "Restarted job {}".format(job.job_id)


def cancel(args, storage):
    """Cancel a job."""
    try:
        job = Job(storage, args.job_id)
        job.fetch()
    except ValueError as e:
        raise AntismashRunError('Job {} not found in database, {}!'.format(args.job_id, e))

    if job.state not in ('created', 'downloading', 'validating', 'waiting', 'queued'):
        if not args.force:
            return "Cannot cancel job in state {}".format(job.state)

    old_state = job.state
    job.state = args.state
    job.status = "{}: {}".format(args.state, args.reason)

    storage.lrem('jobs:{}'.format(old_state), value=job.job_id, count=-1)
    storage.lpush('jobs:{}'.format(job.state), job.job_id)

    ret = "Canceled job {j.job_id} ({j.state})".format(j=job)

    if args.notify:
        ret += '\n'
        ret += dispatch_mail(job)

    return ret


def notify(args, storage):
    """Send email notification about a given job"""
    try:
        job = Job(storage, args.job_id)
        job.fetch()
    except ValueError as e:
        raise AntismashRunError('Job {} not found in database, {}!'.format(args.job_id, e))

    return dispatch_mail(job)


def dispatch_mail(job):
    """Dispatch the actual email for a job."""
    if not job.email:
        return "No email configured for job {}".format(job.job_id)
    mail_conf = MailConfig.from_env()

    send_mail(mail_conf, job)
    return "Mail sent for job {j.job_id} ({j.state})".format(j=job)
