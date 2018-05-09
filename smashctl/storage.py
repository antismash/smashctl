"""Database access functions"""
import redis


class AntismashStorageError(RuntimeError):
    """Error thrown when accessing the storage fails"""
    pass


def get_storage(uri):
    """Get a redis connection to the specified URI"""
    if uri.startswith('redis://'):
        return redis.Redis.from_url(uri, encoding='utf-8', decode_responses=True)
    else:
        raise AntismashStorageError('Unknown storage schema {!r}'.format(uri))
