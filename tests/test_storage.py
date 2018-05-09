"""Storage access abstractions"""
import pytest
from smashctl.storage import get_storage, AntismashStorageError


def test_get_storage(mocker):
    redis_mock = mocker.patch('redis.Redis')
    redis_mock.from_url = mocker.MagicMock()
    get_storage('redis://fake')
    assert redis_mock.from_url.called_with('redis://fake', encoding='utf-8', decode_responses=True)

    with pytest.raises(AntismashStorageError):
        get_storage('fake://data')
