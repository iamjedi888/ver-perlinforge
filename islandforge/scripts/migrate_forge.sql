
-- Run once in Oracle console

-- Expand island_saves with new columns
ALTER TABLE island_saves ADD (display_name VARCHAR2(128));
ALTER TABLE island_saves ADD (config       CLOB);
ALTER TABLE island_saves ADD (verse_data   CLOB);
ALTER TABLE island_saves ADD (stickers     VARCHAR2(2048));
ALTER TABLE island_saves ADD (is_public    NUMBER(1) DEFAULT 1);

-- New: island presets library
CREATE TABLE island_presets (
    id            NUMBER        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    epic_id       VARCHAR2(64),
    display_name  VARCHAR2(128),
    name          VARCHAR2(64),
    config        CLOB,
    is_public     NUMBER(1)     DEFAULT 1,
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);
