"""Tests for the common functions"""
import builtins  # noqa # pylint: disable=unused-import
from smashctl import common


def test_run_command(mocker):
    mock_print = mocker.patch('builtins.print')
    mock_func = mocker.MagicMock()

    common.run_command(mock_func, 'args', 'storage')
    assert mock_func.called_once()
    assert mock_print.called_once()


def test_run_command_error(mocker):
    mock_exit = mocker.patch('sys.exit')
    mock_func = mocker.MagicMock(side_effect=common.AntismashRunError)
    common.run_command(mock_func, 'args', 'storage')
    assert mock_exit.called_with(1)
