import asyncio
from sqlalchemy import select, update
from database import async_session, engine, Base
from models import User
import sys

async def make_admin(username: str):
    async with async_session() as session:
        async with session.begin():
            # Find the user
            user_result = await session.execute(select(User).where(User.username == username))
            user = user_result.scalar_one_or_none()

            if user is None:
                print(f"User '{username}' not found.")
                return

            # Update the user's is_admin flag
            await session.execute(
                update(User)
                .where(User.username == username)
                .values(is_admin=True)
            )
            print(f"User '{username}' has been granted admin privileges.")

async def main():
    if len(sys.argv) != 2:
        print("Usage: python make_admin.py <username>")
        sys.exit(1)
    
    username = sys.argv[1]
    
    # Optional: Create tables if they don't exist. 
    # Usually, you'd handle this with Alembic or another migration tool.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await make_admin(username)

if __name__ == "__main__":
    asyncio.run(main())
