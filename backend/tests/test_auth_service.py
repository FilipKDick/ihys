from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.services.auth import create_session, delete_session, get_current_user


def make_db(get_records=None, insert=None, delete=None):
    db = MagicMock()
    db.get_records.return_value = get_records or []
    db.insert_record.return_value = insert
    db.delete_record.return_value = delete
    return db


def test_create_session_inserts_and_returns_token():
    db = make_db(insert={'token': 'abc', 'user_id': 1, 'expires_at': 'x', 'created_at': 'y'})
    with patch('app.services.auth.db', db):
        token = create_session(user_id=1)
    assert isinstance(token, str)
    assert len(token) > 20
    call_args = db.insert_record.call_args
    assert call_args[0][0] == 'sessions'
    data = call_args[0][1]
    assert data['user_id'] == 1
    assert data['token'] == token


def test_get_current_user_returns_user_for_valid_token():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    db = MagicMock()
    db.get_records.return_value = [{'token': 'tok', 'user_id': 7, 'expires_at': future}]
    db.get_record_by_id.return_value = {'id': 7, 'mal_username': 'testuser'}

    from fastapi import Request
    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'tok'}

    with patch('app.services.auth.db', db):
        user = get_current_user(request)

    assert user['id'] == 7


def test_get_current_user_accepts_database_datetime_for_expires_at():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    db = MagicMock()
    db.get_records.return_value = [
        {'token': 'tok', 'user_id': 7, 'expires_at': future},
    ]
    db.get_record_by_id.return_value = {'id': 7, 'mal_username': 'testuser'}

    from fastapi import Request
    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'tok'}

    with patch('app.services.auth.db', db):
        user = get_current_user(request)

    assert user['id'] == 7


def test_get_current_user_raises_401_for_missing_cookie():
    from fastapi import HTTPException, Request
    request = MagicMock(spec=Request)
    request.cookies = {}

    with pytest.raises(HTTPException) as exc:
        get_current_user(request)
    assert exc.value.status_code == 401


def test_get_current_user_raises_401_for_unknown_token():
    from fastapi import HTTPException, Request
    db = MagicMock()
    db.get_records.return_value = []

    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'unknown-token'}

    with patch('app.services.auth.db', db):
        with pytest.raises(HTTPException) as exc:
            get_current_user(request)
    assert exc.value.status_code == 401


def test_get_current_user_raises_401_for_expired_token():
    from fastapi import HTTPException, Request
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    db = MagicMock()
    db.get_records.return_value = [{'token': 'tok', 'user_id': 7, 'expires_at': past}]

    request = MagicMock(spec=Request)
    request.cookies = {'session_id': 'tok'}

    with patch('app.services.auth.db', db), patch('app.services.auth.delete_session'):
        with pytest.raises(HTTPException) as exc:
            get_current_user(request)
    assert exc.value.status_code == 401


def test_delete_session_removes_row():
    pool = MagicMock()
    conn = MagicMock()
    cur = MagicMock()
    pool.connection.return_value.__enter__ = MagicMock(return_value=conn)
    pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch('app.services.auth.get_pool', return_value=pool):
        delete_session('tok')

    cur.execute.assert_called_once_with('DELETE FROM sessions WHERE token = %s', ('tok',))
