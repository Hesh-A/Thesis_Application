import pytest


class FakeQuery:
    def __init__(self, records):
        self.records = records

    def filter_by(self, **filters):
        return FakeQuery(
            [
                record
                for record in self.records
                if all(getattr(record, key) == value for key, value in filters.items())
            ]
        )

    def first(self):
        return self.records[0] if self.records else None

    def all(self):
        return self.records


class FakeDb:
    def __init__(self, tables=None):
        self.tables = tables or {}
        self.added = []

    def query(self, model):
        return FakeQuery(self.tables.get(model, []))

    def add(self, record):
        self.added.append(record)
        self.tables.setdefault(type(record), []).append(record)

    def commit(self):
        pass

    def refresh(self, record):
        pass


@pytest.fixture
def fake_db_factory():
    return FakeDb
