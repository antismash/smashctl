"""Job management logic"""
from antismash_models import SyncJob as Job
from email.mime.text import MIMEText

from smashctl.common import AntismashRunError
from smashctl.mail import send_mail, MailConfig


def register(subparsers):  # pragma: no cover
    """Register job subcommands"""
    p_job = subparsers.add_parser('job', help='Show and manipulate jobs')

    job_subparsers = p_job.add_subparsers(title='job-related commands')

    p_show = job_subparsers.add_parser('show', help='Show a job')
    p_show.add_argument('job_id', help="ID of the job to show")
    p_show.set_defaults(func=show)

    p_list = job_subparsers.add_parser('list', help='List jobs')
    p_list.add_argument('-q', '--queue', default='queued',
                        help="What queue to list jobs for (default: %(default)s)")
    p_list.set_defaults(func=joblist)

    p_restart = job_subparsers.add_parser('restart', help='Restart a job')
    p_restart.add_argument('job_id', help="ID of the job to restart")
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


def show(args, storage):
    """Handle smashctl job show"""
    try:
        job = Job(storage, args.job_id)
        job.fetch()
    except ValueError as e:
        raise AntismashRunError('Job {} not found in database, {}!'.format(args.job_id, e))

    template = "{job.job_id}\t{job.dispatcher}\t{job.added}\t{job.last_changed}\t{job.email}\t{job.state}\t{job.status}"

    return template.format(job=job)


def joblist(args, storage):
    """Handle listing jobs"""
    queue_key = 'jobs:{}'.format(args.queue)

    template = '{job.job_id}\t{job.jobtype}\t{job.dispatcher}\t{job.email}\t{job.added}\t{job.last_changed}\t' \
               '{job.filename}{job.download}\t{job.state}\t{job.status}'

    result_lines = []

    jobs = storage.lrange(queue_key, 0, -1)
    for job_id in jobs:
        try:
            job = Job(storage, job_id)
            job.fetch()
            result_lines.append(template.format(job=job))
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
    if job.download:
        job.filename = ''

    job.commit()

    new_queue = "jobs:queued"
    storage.lrem(old_queue, value=job.job_id, count=-1)
    storage.rpush(new_queue, job.job_id)
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

    if args.send_mail:
        ret += '\n'
        ret += dispatch_mail(args, job)

    return ret


def notify(args, storage):
    """Send email notification about a given job"""
    try:
        job = Job(storage, args.job_id)
        job.fetch()
    except ValueError as e:
        raise AntismashRunError('Job {} not found in database, {}!'.format(args.job_id, e))

    return dispatch_mail(args, job)


def dispatch_mail(args, job):
    """Dispatch the actual email for a job."""
    if not job.email:
        return "No email configured for job {}".format(job.job_id)
    mail_conf = MailConfig.from_args(args)

    send_mail(mail_conf, job)
    return "Mail sent for job {j.job_id} ({j.state})".format(j=job)

