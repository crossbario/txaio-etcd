import uuid
import random
import datetime
from pprint import pformat
from typing import Optional, List, Dict

from txaioetcd import pmap


_USER_COUNTER = 0


class User(object):

    UUID = uuid.UUID(hex='fa1ed0fc-304e-4f66-8092-d901df1735e4')
    UUID_IDX_BY_NAME = uuid.UUID(hex='aa2754e5-a859-4986-8749-1299828dc6e1')

    PMAP = pmap.MapUuidCbor
    PMAP_IDX_BY_NAME = pmap.MapStringUuid

    NAME = 'users'
    DESC = """CFC global users table.

    The table holds all CFC users registered in this CFC instance.
    """

    oid: int
    name: str
    email: str
    birthday: datetime.date
    is_friendly: bool
    tags: Optional[List[str]]
    ratings: Dict[str, float] = {}
    friends: List[int] = []
    referred_by: int = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if other.oid != self.oid:
            return False
        if other.name != self.name:
            return False
        if other.email != self.email:
            return False
        if other.birthday != self.birthday:
            return False
        if other.is_friendly != self.is_friendly:
            return False
        if (self.tags and not other.tags) or (not self.tags and other.tags):
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '\n{}\n'.format(pformat(self.marshal()))

    def marshal(self):
        obj = {
            'oid': self.oid.hex if self.oid else None,
            'name': self.name,
            'email': self.email,
            'birthday': {
                'year': self.birthday.year if self.birthday else None,
                'month': self.birthday.month if self.birthday else None,
                'day': self.birthday.day if self.birthday else None,
            },
            'is_friendly': self.is_friendly,
            'tags': self.tags,
            'ratings': self.ratings,
            'friends': self.friends,
            'referred_by': self.referred_by,
        }
        return obj

    @staticmethod
    def parse(obj):
        user = User()
        if 'oid' in obj:
            user.oid = uuid.UUID(hex=obj['oid'])
        user.name = obj.get('name', None)
        user.email = obj.get('email', None)
        if 'birthday' in obj:
            b = obj['birthday']
            user.birthday = datetime.date(b.get('year', None), b.get('month', None), b.get('day', None))
        user.is_friendly = obj.get('is_friendly', None)
        user.tags = obj.get('tags', None)
        user.ratings = obj.get('ratings', {})
        user.friends = obj.get('friends', [])
        user.referred_by = obj.get('referred_by', None)
        return user

    @staticmethod
    def create_test_user(oid=None, name=None):
        global _USER_COUNTER

        user = User()
        user.oid = oid or uuid.uuid4()
        if name:
            user.name = name
        else:
            _USER_COUNTER += 1
            user.name = 'user{}'.format(_USER_COUNTER)
        user.email = '{}@github.com'.format(user.name)
        user.tags = random.sample(['geek', 'sudoko', 'yellow', 'dronepilot', 'drwho'], 2)
        user.birthday = datetime.date(1930 + random.randint(0, 80), random.randint(1, 12), random.randint(1, 28))
        user.is_friendly = True
        for j in range(10):
            user.ratings['rating{}'.format(j)] = random.random()
        user.friends = [random.randint(0, 9007199254740992) for _ in range(10)]
        user.referred_by = random.randint(0, 9007199254740992)
        return user
