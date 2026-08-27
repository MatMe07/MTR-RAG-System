import json
from sqlalchemy import TypeDecorator, String, Text, Integer, BigInteger
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, ARRAY as PG_ARRAY, UUID as PG_UUID
from app.db.session import _is_sqlite


class JSONBCompat(TypeDecorator):
    """JSONB для PostgreSQL, JSON для SQLite."""
    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        self.as_json = kwargs.pop("as_json", False)
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False, default=str)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

    class comparator_factory(TypeDecorator.Comparator):
        def __getitem__(self, key):
            return self.expr

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return PG_JSONB()
        return Text()


class ARRAYCompat(TypeDecorator):
    """ARRAY для PostgreSQL, JSON-массив для SQLite."""
    impl = Text
    cache_ok = True

    def __init__(self, item_type=None, *args, **kwargs):
        self.item_type = item_type
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(list(value), ensure_ascii=False)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value or []

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return PG_ARRAY(self.item_type or String())
        return Text()


def UUID_column(**kwargs):
    """UUID колонка: native UUID в PostgreSQL, String в SQLite."""
    from app.db.session import _is_sqlite
    if _is_sqlite:
        return String(36, **kwargs)
    return PG_UUID(as_uuid=True, **kwargs)


def PKColType():
    """Primary key type: Integer для SQLite, BigInteger для PostgreSQL."""
    if _is_sqlite:
        return Integer()
    return BigInteger()
