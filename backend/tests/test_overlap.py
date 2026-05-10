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
            ('anime', (('mal_id', 52991),)): [
                {'id': 1, 'name': 'Frieren', 'mal_id': 52991},
            ],
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


def test_orders_overlap_by_common_anime_count_and_status():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [{'id': 1, 'name': 'Frieren', 'mal_id': 52991}],
            ('characters', (('anime_id', 1),)): [
                {'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1},
                {'id': 101, 'name': 'Fern', 'photo': '', 'anime_id': 1},
                {'id': 102, 'name': 'Stark', 'photo': '', 'anime_id': 1},
            ],
            ('user_anime', (('user_id', 42),)): [
                {
                    'id': 1,
                    'user_id': 42,
                    'anime_id': 4,
                    'watch_status': 'plan_to_watch',
                },
                {'id': 2, 'user_id': 42, 'anime_id': 2, 'watch_status': 'completed'},
                {'id': 3, 'user_id': 42, 'anime_id': 5, 'watch_status': 'dropped'},
                {'id': 4, 'user_id': 42, 'anime_id': 3, 'watch_status': 'watching'},
            ],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100, 101, 102})): [
                {'character_id': 100, 'actor_id': 20},
                {'character_id': 101, 'actor_id': 10},
                {'character_id': 102, 'actor_id': 30},
            ],
            ('characters', 'anime_id', frozenset({2, 3, 4, 5})): [
                {'id': 200, 'name': 'Role A', 'photo': '', 'anime_id': 2},
                {'id': 201, 'name': 'Role B', 'photo': '', 'anime_id': 3},
                {'id': 202, 'name': 'Role C', 'photo': '', 'anime_id': 4},
                {'id': 203, 'name': 'Role D', 'photo': '', 'anime_id': 5},
                {'id': 204, 'name': 'Role E', 'photo': '', 'anime_id': 4},
            ],
            (
                'character_actors',
                'character_id',
                frozenset({200, 201, 202, 203, 204}),
            ): [
                {'character_id': 200, 'actor_id': 20},
                {'character_id': 201, 'actor_id': 20},
                {'character_id': 202, 'actor_id': 20},
                {'character_id': 203, 'actor_id': 10},
                {'character_id': 204, 'actor_id': 30},
            ],
            ('actors', 'id', frozenset({10, 20, 30})): [
                {'id': 10, 'name': 'Alpha Actor', 'photo': ''},
                {'id': 20, 'name': 'Beta Actor', 'photo': ''},
                {'id': 30, 'name': 'Charlie Actor', 'photo': ''},
            ],
            ('anime', 'id', frozenset({2, 3, 4, 5})): [
                {'id': 2, 'name': 'Completed Show', 'mal_id': 2},
                {'id': 3, 'name': 'Watching Show', 'mal_id': 3},
                {'id': 4, 'name': 'Planned Show', 'mal_id': 4},
                {'id': 5, 'name': 'Dropped Show', 'mal_id': 5},
            ],
        },
        by_id={},
    )

    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)

    assert [item['actor']['name'] for item in result] == [
        'Beta Actor',
        'Alpha Actor',
        'Charlie Actor',
    ]
    assert [anime['name'] for anime in result[0]['appears_in']] == [
        'Completed Show',
        'Watching Show',
        'Planned Show',
    ]
    assert [anime['watch_status'] for anime in result[0]['appears_in']] == [
        'completed',
        'watching',
        'plan_to_watch',
    ]


def test_orders_overlap_count_ignores_planned_anime():
    db = _make_db(
        by_table={
            ('anime', (('mal_id', 52991),)): [
                {'id': 1, 'name': 'Frieren', 'mal_id': 52991},
            ],
            ('characters', (('anime_id', 1),)): [
                {'id': 100, 'name': 'Frieren', 'photo': '', 'anime_id': 1},
                {'id': 101, 'name': 'Fern', 'photo': '', 'anime_id': 1},
            ],
            ('user_anime', (('user_id', 42),)): [
                {'id': 1, 'user_id': 42, 'anime_id': 2, 'watch_status': 'completed'},
                {'id': 2, 'user_id': 42, 'anime_id': 3, 'watch_status': 'plan_to_watch'},
                {'id': 3, 'user_id': 42, 'anime_id': 4, 'watch_status': 'plan_to_watch'},
            ],
        },
        by_ids={
            ('character_actors', 'character_id', frozenset({100, 101})): [
                {'character_id': 100, 'actor_id': 10},
                {'character_id': 101, 'actor_id': 20},
            ],
            ('characters', 'anime_id', frozenset({2, 3, 4})): [
                {'id': 200, 'name': 'Watched Role', 'photo': '', 'anime_id': 2},
                {'id': 201, 'name': 'Planned Role A', 'photo': '', 'anime_id': 3},
                {'id': 202, 'name': 'Planned Role B', 'photo': '', 'anime_id': 4},
            ],
            ('character_actors', 'character_id', frozenset({200, 201, 202})): [
                {'character_id': 200, 'actor_id': 20},
                {'character_id': 201, 'actor_id': 10},
                {'character_id': 202, 'actor_id': 10},
            ],
            ('actors', 'id', frozenset({10, 20})): [
                {'id': 10, 'name': 'Planned Actor', 'photo': ''},
                {'id': 20, 'name': 'Watched Actor', 'photo': ''},
            ],
            ('anime', 'id', frozenset({2, 3, 4})): [
                {'id': 2, 'name': 'Completed Show', 'mal_id': 2},
                {'id': 3, 'name': 'Planned Show A', 'mal_id': 3},
                {'id': 4, 'name': 'Planned Show B', 'mal_id': 4},
            ],
        },
        by_id={},
    )

    with patch('app.services.anime_actors.db', db):
        result = get_actor_overlap(52991, 42)

    assert [item['actor']['name'] for item in result] == [
        'Watched Actor',
        'Planned Actor',
    ]
