from unittest.mock import MagicMock, patch

from app.services.anime_actors import get_actor_overlap


def _make_db(by_table: dict, by_ids: dict, by_id: dict) -> MagicMock:
    mock = MagicMock()

    def get_records(table: str, filters: dict | None = None) -> list:
        return by_table.get((table, tuple(sorted((filters or {}).items()))), [])

    def get_records_by_ids(table: str, column: str, ids: list) -> list:
        return by_ids.get((table, column, frozenset(ids)), [])

    def get_record_by_id(table: str, record_id: int) -> dict | None:
        return by_id.get((table, record_id))

    mock.get_records.side_effect = get_records
    mock.get_records_by_ids.side_effect = get_records_by_ids
    mock.get_record_by_id.side_effect = get_record_by_id
    return mock


def test_returns_shared_actor():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [{'id': 1, 'user_id': 42, 'anime_id': 2}],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
            ('characters', 'anime_id', frozenset({2})): [{'id': 200, 'name': 'Eren', 'photo': '', 'anime_id': 2}],
            ('character_actors', 'character_id', frozenset({200})): [{'character_id': 200, 'actor_id': 10}],
            ('actors', 'id', frozenset({10})): [{'id': 10, 'name': 'Atsumi Tanezaki', 'photo': 'http://photo.jpg'}],
            ('anime', 'id', frozenset({2})): [{'id': 2, 'name': 'Attack on Titan', 'mal_id': 16498}],
        },
        by_id={},
    )

    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)

    assert len(result) == 1
    assert result[0]['actor']['name'] == 'Atsumi Tanezaki'
    assert result[0]['character_in_new_anime']['name'] == 'Frieren'
    assert result[0]['appears_in'][0]['name'] == 'Attack on Titan'


def test_returns_empty_when_anime_not_in_db():
    db = _make_db(
        by_table={('anime', (('mal_id', 99999),)): []},
        by_ids={},
        by_id={},
    )
    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(99999, 42)
    assert result == []


def test_returns_empty_when_no_shared_actors():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [{'id': 1, 'user_id': 42, 'anime_id': 2}],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
            ('characters', 'anime_id', frozenset({2})): [{'id': 200, 'name': 'Eren', 'photo': '', 'anime_id': 2}],
            ('character_actors', 'character_id', frozenset({200})): [{'character_id': 200, 'actor_id': 99}],
            ('actors', 'id', frozenset()): [],
        },
        by_id={},
    )
    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)
    assert result == []


def test_returns_empty_when_user_has_no_history():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
            ('actors', 'id', frozenset({10})): [{'id': 10, 'name': 'Atsumi Tanezaki', 'photo': ''}],
        },
        by_id={},
    )
    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)
    assert result == []


def test_excludes_selected_anime_from_watch_history_overlap():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 38668),)): [{'id': 1, 'name': 'Dorohedoro', 'mal_id': 38668}],
            ('characters', (('anime_id', 1),)): [{'id': 100, 'name': 'Caiman', 'photo': '', 'anime_id': 1}],
            ('user_anime', (('user_id', 42),)): [{'id': 1, 'user_id': 42, 'anime_id': 1}],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100})): [{'character_id': 100, 'actor_id': 10}],
            ('characters', 'anime_id', frozenset({1})): [{'id': 100, 'name': 'Caiman', 'photo': '', 'anime_id': 1}],
            ('actors', 'id', frozenset({10})): [{'id': 10, 'name': 'Takagi, Wataru', 'photo': ''}],
            ('anime', 'id', frozenset({1})): [{'id': 1, 'name': 'Dorohedoro', 'mal_id': 38668}],
        },
        by_id={},
    )

    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(38668, 42)

    assert result == []
