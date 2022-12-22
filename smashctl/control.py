"""dispatcher control logic"""

import argparse
from typing import List

from antismash_models import SyncControl as Control
from redis import Redis


def register(subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]"):  # pragma: no cover
    """Register control subcommands"""
    p_control = subparsers.add_parser('control', help='Show and manipulate dispatchers')

    control_subparsers = p_control.add_subparsers(title="dispatcher-related commands")

    p_control_list = control_subparsers.add_parser("list", help="List dispatchers")
    p_control_list.add_argument("--pretty",
                                dest="pretty", default="standard",
                                choices=["simple", "standard"],
                                help="Modify the output style")
    p_control_list.set_defaults(func=control_list)

    p_control_stop = control_subparsers.add_parser("stop", help="Stop dispatcher(s)")
    p_control_stop.add_argument("names", nargs="+", metavar="name",
                                help="Name(s) of dispatcher(s) to stop ('all' to stop everything)")
    p_control_stop.set_defaults(func=control_stop)


def control_list(args: argparse.Namespace, storage: Redis) -> str:
    """List running dispatchers"""
    lines: List[str] = []
    dispatcher_ids = _get_all_dispatcher_names(storage)
    for dispatcher_id in dispatcher_ids:
        d: Control = Control(storage, dispatcher_id, 0).fetch()  # type: ignore

        if args.pretty == "simple":
            lines.append(
                "\t".join([
                    f"{d.name:<16}",
                    f"{d.stop_scheduled}",
                    d.status,
                    d.version,
                    f"{d.max_jobs}",
                    f"{d.running_jobs}",
                ])
            )
            continue

        lines.append(f"""{d.name}
    running: {d.running}
    stopping: {d.stop_scheduled}
    status: {d.status}
    version: {d.version}
    max_jobs: {d.max_jobs}
    running_jobs: {d.running_jobs}""")

    return "\n".join(lines)


def control_stop(args: argparse.Namespace, storage: Redis) -> str:
    """Stop dispatcher(s)"""
    output: List[str] = []

    if "all" in args.names:
        args.names = _get_all_dispatcher_names(storage)

    for dispatcher_id in args.names:
        try:
            d = Control(storage, dispatcher_id, 0).fetch()  # type: ignore
            d.stop_scheduled = True
            d.commit()
            output.append(f"Stopping dispatcher {dispatcher_id}")
        except ValueError:
            output.append(f"Skipping noexistent dispatcher {dispatcher_id}")

    return "\n".join(output)


def _get_all_dispatcher_names(storage: Redis) -> List[str]:
    """Get all dispatcher names, sorted"""
    return list(map(lambda x: x.split(":")[-1], sorted(storage.keys("control:*"))))
