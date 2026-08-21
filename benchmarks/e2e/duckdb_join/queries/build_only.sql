SET threads=8;
SET memory_limit='200GB';
CREATE TABLE b AS SELECT i::BIGINT AS k, (i*7)::BIGINT AS payload FROM range(2000000) t(i);
CREATE TABLE p AS SELECT (hash(i) % 2000000)::BIGINT AS k FROM range(100000000) t(i);
SET threads=1;
.timer on



SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;
