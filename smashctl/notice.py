"""website notification handling"""

import argparse
from datetime import date, datetime, timedelta, UTC
import uuid

from antismash_models import SyncNotice as Notice
from redis import Redis


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
SELECTABLE_CATEGORIES = ['error', 'warning', 'info']


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") \
        -> None:  # pragma: no cover
    """Register notice subcommands"""
    now = datetime.now(UTC)
    next_week = now + timedelta(days=7)

    p_notice = subparsers.add_parser("notice", help="Show and control notifications")
    p_notice.set_defaults(func=notice_list)

    notice_subparser = p_notice.add_subparsers(title="notice-related commands")

    p_list = notice_subparser.add_parser("list", help="List notices")
    p_list.add_argument("--pretty",
                        dest="pretty", default="simple",
                        choices=["simple", "verbose"],
                        help="Modify the output style")
    p_list.add_argument('--category', dest='category',
                        default='all', choices=SELECTABLE_CATEGORIES + ['all'],
                        help='Category of the notices to list')
    p_list.set_defaults(func=notice_list)

    p_show = notice_subparser.add_parser("show", help="Show a single notice")
    p_show.add_argument("notice_id", help="ID of the notice to show")
    p_show.add_argument("--pretty",
                        dest="pretty", default="verbose",
                        choices=["simple", "verbose"],
                        help="Modify the output style")
    p_show.set_defaults(func=show)

    p_add = notice_subparser.add_parser("add", help="Add a notice")
    p_add.add_argument("teaser", help="Teaser text for the notice")
    p_add.add_argument("text", help="")
    p_add.add_argument('--category', dest='category',
                       default='info', choices=SELECTABLE_CATEGORIES,
                       help='Category of the notice')
    p_add.add_argument('--show-from', dest='show_from',
                       default=now, type=_parsedate,
                       help="Time to start showing the notice in YYYY-MM-DD HH:MM:SS format")
    p_add.add_argument('--show-until', dest='show_until',
                       default=next_week, type=_parsedate,
                       help="Time to stop showing the notice in YYYY-MM-DD HH:MM:SS format")
    p_add.set_defaults(func=add)

    p_remove = notice_subparser.add_parser("remove", help="Remove a notice")
    p_remove.add_argument("notice_id", help="ID of notice to delete")
    p_remove.set_defaults(func=remove)


def _parsedate(datestring: str) -> datetime:
    try:
        return datetime.strptime(datestring, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    try:
        return datetime.strptime(datestring, "%Y-%m-%d")
    except ValueError:
        pass
    try:
        today = date.today()
        timepoint = datetime.strptime(datestring, "%H:%M:%S").time()
        return datetime.combine(today, timepoint)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{datestring!r} can not be parsed as a date")


CUTOFF = 40


def _format_notice(notice: Notice, pretty: str) -> str:
    """ Format a single notice """
    if pretty == "simple":
        text = notice.text
        if len(text) > CUTOFF:
            text = text[:CUTOFF] + "..."
        return "\t".join([
            notice.notice_id,
            notice.category,
            notice.teaser,
            text,
            notice.show_from.strftime(DATE_FORMAT),
            notice.show_until.strftime(DATE_FORMAT),
        ])

    if pretty == "verbose":
        return f"""{notice.category}: {notice.teaser}
ID: {notice.notice_id}
From: {notice.show_from.strftime(DATE_FORMAT)}
To: {notice.show_until.strftime(DATE_FORMAT)}

{notice.text}
"""
    raise ValueError(f"Invalid format option {pretty}")


def notice_list(args: argparse.Namespace, storage: Redis) -> str:
    """ List a selection of configured notices """
    notices: list[str] = storage.keys("notice:*")
    result_lines: list[str] = []

    for notice_id in notices:
        try:
            notice = Notice(storage, notice_id.rsplit(":", 1)[-1]).fetch()  # type: ignore
            if args.category == "all" or args.category == notice.category:
                result_lines.append(_format_notice(notice, args.pretty))
        except ValueError as err:  # pragma: no cover  # only happens on race conditions
            print(err)

    if not result_lines:
        return "No notices to display"

    return "\n".join(result_lines)


def show(args: argparse.Namespace, storage: Redis) -> str:
    """ Show a single notice """
    try:
        notice = Notice(storage, args.notice_id).fetch()  # type: ignore
    except ValueError as err:
        return f"Notice {args.notice_id} not found in database: {err}"

    return _format_notice(notice, args.pretty)


def add(args: argparse.Namespace, storage: Redis) -> str:
    """ Add a new notice """
    notice_id = str(uuid.uuid4())
    notice = Notice(storage, notice_id)
    notice.teaser = args.teaser
    notice.text = args.text
    notice.category = args.category
    notice.show_from = args.show_from
    notice.show_until = args.show_until
    notice.commit()  # type: ignore

    return "Created new notice:\n" + _format_notice(notice, "verbose")


def remove(args: argparse.Namespace, storage: Redis) -> str:
    """ Remove an existing notice """
    try:
        notice = Notice(storage, args.notice_id).fetch()  # type: ignore
        notice.delete()
    except ValueError as err:
        return f"Notice {args.notice_id} not found in database: {err}"

    return f"Removed notice: {notice.teaser}"
