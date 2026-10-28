# PR Response Doc — CineLog Watchlist Feature

## AI Usage

I used AI to inspect the codebase and review my responses. For Comment 4, I chose private-by-default and wrote the reasoning first; AI helped clarify the distinction between a stored visibility flag and access control, added a regression test, and updated the implementation and verification notes. My final position remains based on my expectation that saving a film records a personal viewing intention. For Comment 5, I chose newest-first and wrote my reasoning before AI assistance. AI preserved that decision, documented the ordering, and added a regression test using explicit timestamps and titles whose alphabetical order differs from their date-added order. Additional AI usage will be documented as the project continues.

## Comment 1 — Rename

**What I did:** I renamed the service function and updated its import and call in `routes/watchlist/watchlist.py`.

**How I verified:** I did a search for the name "save_to_watchlist" in the source files under services/ and routes/ and it returned no results, meaning I had successfully replaced every instance of the function in the code.

## Comment 2 — Deduplication

**What I did:** I amended the way `add_to_watchlist()` adds new films. Now, the watchlist does not allow duplicate entries. Similar to in `add_to_collection()`, it queries for an existing WatchlistEntry matching both the `user_id` and `film_id`. It raises `AlreadyInWatchlistError` (mirroring `AlreadyInCollectionError`) when a duplicate exists before inserting.

**How I verified:** The current tests don't exercise duplicate watchlist additions. Verification pending until I add the duplicate test.

## Comment 3 — Missing test

**What I did:** I wrote a test mirroring `test_add_to_collection_nonexistent_film_raises(app, sample_user):` but for my add_to_watchlist() function.

**How I verified:** I ran the test suite and all five tests including the new missing film test passed. I tested using:

```Shell
python -m pytest tests/ -v
```

## Comment 4 — Default visibility

**My position:** `WatchlistEntry.public` should default to `False`.

**Reasoning:** I believe that when a user adds something to their watchlist, it isn't something they are thinking will be publicized. What if a user was using their watchlist for their own personal use, and don't want to broadcast every movie they intend to watch, only ones that they did? I'd think saving a movie usually is intended as "save this for me, not publicly."

**Tradeoff acknowledged:** Users would lose the convenience of having their watchlist entries publicly visible immediately after adding them. If a user wants their watchlist public to be social, that would add an extra step to share entries on the user's end. CineLog is intended to be a social platform, and this does remove a level of sharing, but I think it's necessary for more user privacy and matching user assumptions closer.

**What I changed:** Changed `WatchlistEntry.public` in `models.py` from `default=True` to `default=False`. `add_to_watchlist()` omits visibility when constructing an entry, so new additions receive the model's private default when persisted. This applies to new entries; it does not change existing entries. The explicit visibility parameter is separate stretch work.

**How I verified:** Added `test_add_to_watchlist_defaults_to_private` in `tests/test_watchlist.py`. It adds a valid film through the service, expires the session's cached state, and verifies that the persisted entry and its serialized response both have `public=False`. Ran `python -m pytest tests/ -v`: all six tests passed.

**Current limitation:** The visibility flag records the intended sharing preference. The existing GET endpoint returns all entries for a supplied user ID and does not enforce private access. This default change alone does not prevent other callers from reading entries.

## Comment 5 — Sort order

**My position:** Sort by newest first.

**Reasoning:** It keeps the recently saved interests visible, and it also matches the collections behavior. However, known titles are harder to locate in long lists.

**Engagement with reviewer's point:** I would agree that most users would want to see what they added recently so they know what they wanted to see most recently. I think it will be easier for users to find movies in their watchlist by keeping their recent interests in the foreground of their mind as they search their watchlists.

**What I changed:** Changed `get_watchlist()` in `services/watchlist_service.py` to order by `WatchlistEntry.date_added.desc()` instead of `Film.title.asc()`, and documented newest-first behavior in its docstring. The existing GET endpoint uses this service, so it returns the same ordering.

**How I verified:** Added `test_get_watchlist_returns_newest_first` in `tests/test_watchlist.py`, following the collection sort-test pattern. It assigns fixed timestamps to an older Alien entry and a newer Spirited Away entry, then asserts that Spirited Away comes first. Alphabetical ordering would return the opposite result. Ran `python -m pytest tests/ -v`: all seven tests passed.

## Comment 6 — Rebase

**What conflicted: Pending**

**How I resolved it: Pending**

**How I verified no conflict remains: Pending**

## PR Description

### Default visibility decision

New watchlist entries default to private (`public=False`). Saving a film records a user's intention to watch it, which I do not consider an automatic decision to share that intention. For CineLog's community features, this reduces automatic discovery and requires an extra sharing step; I accept that tradeoff to better match the expectations described in Comment 4. This sets the stored visibility preference; access control is not implemented by this change.

### Sort-order decision

Watchlists return entries by date added, newest first. This follows the reviewer's suggestion to surface recent additions and matches the collection service. Recent saves act as reminders of current viewing interests. The tradeoff is that finding a known title in a long list is less convenient than with alphabetical ordering.

Feature overview and end-to-end manual testing steps are pending.
