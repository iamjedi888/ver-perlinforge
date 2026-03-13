
-- Run once to add room columns
-- Paste into Oracle DB console or run via python

ALTER TABLE members ADD (room_theme VARCHAR2(32) DEFAULT '');
ALTER TABLE members ADD (tickets NUMBER DEFAULT 0);
