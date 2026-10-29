"""Tests for the watchlist functionality."""

from datetime import datetime, timezone, timedelta

import pytest
from app import create_app, db
from models import User, Film, WatchlistEntry
from services.collection_service import FilmNotFoundError
from services.watchlist_service import (
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    AlreadyInWatchlistError, NotInWatchlistError,
)


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    """A user to use in tests."""
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    """A film to use in tests."""
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id

def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    """
    Adding a film_id that doesn't exist in the database should raise
    FilmNotFoundError, not a database integrity error.
    """
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)


def test_add_to_watchlist_defaults_to_private(app, sample_user, sample_film):
    """New additions persist and serialize the private visibility default."""
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)
        entry_id = entry.id
        db.session.expire_all()

        persisted = db.session.get(WatchlistEntry, entry_id)
        assert persisted.public is False
        assert persisted.to_dict()["public"] is False


def test_get_watchlist_returns_newest_first(app, sample_user):
    """Recent additions come first even when alphabetical order differs."""
    with app.app_context():
        older_film = Film(title="Alien", year=1979)
        newer_film = Film(title="Spirited Away", year=2001)
        db.session.add_all([older_film, newer_film])
        db.session.commit()

        later = datetime(2026, 1, 2, tzinfo=timezone.utc)
        earlier = later - timedelta(days=1)
        db.session.add_all([
            WatchlistEntry(
                user_id=sample_user, film_id=older_film.id, date_added=earlier,
            ),
            WatchlistEntry(
                user_id=sample_user, film_id=newer_film.id, date_added=later,
            ),
        ])
        db.session.commit()

        watchlist = get_watchlist(sample_user)

        assert [film["title"] for film in watchlist] == ["Spirited Away", "Alien"]


def test_remove_from_watchlist_preserves_other_users(app, sample_user, sample_film):
    with app.app_context():
        other = User(username="other", email="other@example.com")
        db.session.add(other)
        db.session.commit()
        add_to_watchlist(sample_user, sample_film)
        other_entry = add_to_watchlist(other.id, sample_film)
        other_entry_id = other_entry.id

        assert remove_from_watchlist(sample_user, sample_film) is True
        db.session.expire_all()
        assert WatchlistEntry.query.filter_by(user_id=sample_user).count() == 0
        assert db.session.get(WatchlistEntry, other_entry_id) is not None


def test_remove_from_watchlist_twice_raises(app, sample_user, sample_film):
    with app.app_context():
        add_to_watchlist(sample_user, sample_film)
        remove_from_watchlist(sample_user, sample_film)
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, sample_film)


def test_remove_from_watchlist_unknown_film_raises(app, sample_user):
    with app.app_context():
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, "00000000-0000-0000-0000-000000000000")


def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    """A repeated addition raises without creating an extra database row."""
    with app.app_context():
        original = add_to_watchlist(sample_user, sample_film)
        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(sample_user, sample_film)
        entries = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).all()
        assert len(entries) == 1
        assert entries[0].id == original.id
