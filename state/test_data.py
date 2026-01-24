import duckdb
df = duckdb.sql("""
    SELECT DISTINCT original_category
    FROM '/home/dell/Desktop/fairserve-1/data/processed/live_stream/batch_20260124_141659_1c482c.parquet'
    LIMIT 10
""").df()
print(df.head())

dfs = duckdb.sql("""
    SELECT DISTINCT service_type
    FROM '/home/dell/Desktop/fairserve-1/data/processed/live_stream/batch_20260124_141659_1c482c.parquet'
    LIMIT 10
""").df()
print(dfs.head())