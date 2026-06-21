import os
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool


# Sample: DB_URI = "postgresql://user:password@host:5432/dbname"
DB_URI = (
    f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
)


pool = ConnectionPool(conninfo=DB_URI, max_size=20, kwargs={"autocommit": True})

checkpointer = PostgresSaver(pool)
# Required once, to create the checkpoint tables
checkpointer.setup()
