-- 只在 PG 数据目录为空（首次初始化）时执行；data/pg 非空会自动跳过。
-- 注意：psql 不展开环境变量，库名/用户名在这里写死；改 .env 的 PG_DB 要同步改本文件。
CREATE SCHEMA IF NOT EXISTS app;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

GRANT ALL PRIVILEGES ON DATABASE smartdesk TO smartdesk;
GRANT ALL ON SCHEMA app TO smartdesk;
ALTER DATABASE smartdesk SET search_path TO app, public;

-- LangGraph checkpoint 表（checkpoints / checkpoint_blobs / checkpoint_writes）由 PostgresSaver.setup() 在后端首次启动时自动创建。