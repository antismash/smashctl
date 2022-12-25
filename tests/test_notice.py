import argparse
from datetime import date, datetime, time
import uuid

from antismash_models import SyncNotice as Notice
import pytest

from smashctl import notice


@pytest.fixture
def args() -> argparse.Namespace:
    new_args = argparse.Namespace()
    new_args.pretty = "verbose"
    new_args.category = "all"
    return new_args


@pytest.fixture
def notices(db) -> list[Notice]:
    start = datetime.strptime("2023-01-01 00:00:00", notice.DATE_FORMAT)
    end = datetime.strptime("2023-01-01 12:00:00", notice.DATE_FORMAT)
    n1 = Notice(
        db,
        "fake_notice",
        teaser="Fake notice now available",
        text="We're happy to announce that fake notices are now available",
        show_from=start,
        show_until=end,
    )
    n1.commit()  # type: ignore

    n2 = Notice(
        db,
        "other_fake_notice",
        category="error",
        teaser="Other fake notice also ready",
        text="A second fake notice is available for your convenience",
        show_from=start,
        show_until=end,
    )
    n2.commit()  # type: ignore

    return [n1, n2]


def test_format_notice(notices):
    expected_short = (
        "fake_notice\tinfo\tFake notice now available\t"
        "We're happy to announce that fake notice...\t"
        "2023-01-01 00:00:00\t2023-01-01 12:00:00"
    )
    expected_long = """info: Fake notice now available
ID: fake_notice
From: 2023-01-01 00:00:00
To: 2023-01-01 12:00:00

We're happy to announce that fake notices are now available
"""
    assert expected_short == notice._format_notice(notices[0], "simple")
    assert expected_long == notice._format_notice(notices[0], "verbose")

    with pytest.raises(ValueError, match="Invalid format option bob"):
        notice._format_notice(notices[0], "bob")


def test_parsedate():
    year = 2023
    month = 1
    day = 2
    hour = 12
    minute = 23
    second = 45
    tdate = f"{year}-{month:02d}-{day:02d}"
    ttime = f"{hour:02d}:{minute:02d}:{second:02d}"
    expected = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)

    assert expected == notice._parsedate(f"{tdate} {ttime}")

    expected = datetime(year=year, month=month, day=day)
    assert expected == notice._parsedate(tdate)

    expected = datetime.combine(date.today(), time(hour=hour, minute=minute, second=second))
    assert expected == notice._parsedate(ttime)

    with pytest.raises(argparse.ArgumentTypeError, match="'bob' can not be parsed as a date"):
        notice._parsedate("bob")


def test_list_all(args, db, notices):
    expected_short = "\n".join(
        map(lambda x: notice._format_notice(x, "simple"), notices)
    )
    expected_long = "\n".join(
        map(lambda x: notice._format_notice(x, "verbose"), notices)
    )

    assert expected_long == notice.notice_list(args, db)

    args.pretty = "simple"
    assert expected_short == notice.notice_list(args, db)

    for n in notices:
        n.delete()

    assert "No notices to display" == notice.notice_list(args, db)


def test_list_specific(args, db, notices):
    expected = notice._format_notice(notices[1], "simple")
    args.pretty = "simple"
    args.category = "error"

    assert expected == notice.notice_list(args, db)

    args.category = "warning"
    assert "No notices to display" == notice.notice_list(args, db)


def test_show(args, db, notices):
    expected_short = notice._format_notice(notices[0], "simple")
    expected_long = notice._format_notice(notices[0], "verbose")
    args.notice_id = notices[0].notice_id

    assert expected_long == notice.show(args, db)

    args.pretty = "simple"
    assert expected_short == notice.show(args, db)

    expected = (
        "Notice bob not found in database: "
        "No SyncNotice with ID notice:bob in database, can't fetch"
    )
    args.notice_id = "bob"
    assert expected == notice.show(args, db)


def test_add(args, db, mocker):
    start = datetime.strptime("2023-01-01 00:00:00", notice.DATE_FORMAT)
    end = datetime.strptime("2023-01-01 12:00:00", notice.DATE_FORMAT)
    mocker.patch("uuid.uuid4", return_value="also-fake")
    args.teaser = "Test notice"
    args.text = "A text for the test notice"
    args.show_from = start
    args.show_until = end
    args.category = "warning"

    ret = notice.add(args, db)
    assert ["notice:also-fake"] == db.keys("notice:also-fake")
    uuid.uuid4.assert_called_once_with()

    new_notice = notice.Notice(db, "also-fake").fetch()
    assert ret == "Created new notice:\n" + notice._format_notice(new_notice, "verbose")


def test_remove(args, db, notices):
    assert len(notices) == len(db.keys("notice:*"))
    args.notice_id = notices[0].notice_id
    expected = f"Removed notice: {notices[0].teaser}"

    assert expected == notice.remove(args, db)

    expected = (
        "Notice bob not found in database: "
        "No SyncNotice with ID notice:bob in database, can't fetch"
    )
    args.notice_id = "bob"
    assert expected == notice.remove(args, db)
