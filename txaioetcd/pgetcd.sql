CREATE SCHEMA pgetcd
;


REVOKE ALL ON SCHEMA pgetcd FROM public
;

GRANT USAGE ON SCHEMA pgetcd TO public
;


DROP FUNCTION IF EXISTS pgetcd.upgrade
(
)
;

CREATE FUNCTION pgetcd.upgrade
(
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS
$$
DECLARE
    l_now           TIMESTAMP := now();
    l_rec           RECORD;
BEGIN
    IF NOT EXISTS
        (SELECT tablename FROM pg_catalog.pg_tables
            WHERE schemaname = 'pgetcd' AND tablename = 'transactions')
    THEN
        EXECUTE 'CREATE TABLE transactions (id BIGINT)';
    END IF;
    FOR l_rec IN (SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'pgetcd')
    LOOP
        NULL;
    END LOOP;
    RETURN;
END
$$
;

REVOKE ALL ON FUNCTION pgetcd.upgrade
(
) FROM public
;

GRANT EXECUTE ON FUNCTION pgetcd.upgrade
(
) TO public
;

COMMENT ON FUNCTION pgetcd.upgrade
(
) IS
'
If there is an upgrade to the database schema pending, including an initial
setup of database tables in an empty target PostgreSQL database, perform
a database schema upgrade (or installation) of tables, views and stored procedures.
'
;


DROP FUNCTION IF EXISTS pgetcd.submit
(
    JSONB,
    INT
)
;

CREATE FUNCTION pgetcd.submit
(
    p_transaction       JSONB,
    p_timeout           INT         DEFAULT NULL
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS
$$
DECLARE
    l_now           TIMESTAMP := now();
BEGIN
    RETURN 0;
END
$$
;

REVOKE ALL ON FUNCTION pgetcd.submit
(
    JSONB,
    INT
) FROM public
;

GRANT EXECUTE ON FUNCTION pgetcd.submit
(
    JSONB,
    INT
) TO public
;

COMMENT ON FUNCTION pgetcd.submit
(
    JSONB,
    INT
) IS
'
Submit an etcd database transaction to PostgreSQL. The etcd guards are processed,
and the respective transaction outcome actions (for success or failure) are stored.
'
;


DROP FUNCTION IF EXISTS pgetcd.get
(
    BYTEA,
    INT
)
;

CREATE FUNCTION pgetcd.get
(
    p_key               BYTEA,
    p_timeout           INT         DEFAULT NULL
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS
$$
DECLARE
    l_now           TIMESTAMP := now();
BEGIN
    RETURN NULL;
END
$$
;

REVOKE ALL ON FUNCTION pgetcd.get
(
    BYTEA,
    INT
) FROM public
;

GRANT EXECUTE ON FUNCTION pgetcd.get
(
    BYTEA,
    INT
) TO public
;

COMMENT ON FUNCTION pgetcd.get
(
    BYTEA,
    INT
) IS
'
Get a value by key.
'
;


DO LANGUAGE plpgsql
$$
DECLARE
    l_now TEXT := TO_CHAR(now(), 'YYYYMMDDHH24MISS');
BEGIN
    NULL;
    --EXECUTE 'CREATE TABLE svc_sqlbalancer_backup.t_job_' || l_now || ' AS SELECT * FROM svc_sqlbalancer.t_job';
END;
$$;
