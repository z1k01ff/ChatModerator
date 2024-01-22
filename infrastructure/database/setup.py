from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


def create_engine(path_to_db: str, echo=False):
    db_url = f"sqlite+aiosqlite:///{path_to_db}"
    engine = create_async_engine(
        db_url,
        echo=echo,
    )
    return engine


def create_session_pool(engine):
    session_pool = async_sessionmaker(bind=engine, expire_on_commit=False)
    return session_pool
