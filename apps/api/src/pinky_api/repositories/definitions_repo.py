"""Definition repository — CRUD for runtime definition overrides."""


from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from pinky_api.models.extensibility import Definition
from pinky_api.repositories.base import BaseRepository


class DefinitionRepository(BaseRepository):
    async def list(self, kind: str | None = None, limit: int = 50, cursor: str | None = None) -> dict:
        stmt = select(Definition)
        if kind:
            stmt = stmt.where(Definition.kind == kind)
        return await self.paginate(stmt, Definition, limit=limit, cursor=cursor)

    async def get(self, kind: str, name: str) -> Definition | None:
        result = await self.session.execute(
            select(Definition).where(Definition.kind == kind, Definition.name == name)
        )
        return result.scalar_one_or_none()

    async def upsert(self, kind: str, name: str, version: str, frontmatter: dict, body: str, created_by: str | None = None) -> Definition:
        existing = await self.get(kind, name)
        if existing:
            existing.version = version
            existing.frontmatter = frontmatter
            existing.body = body
            await self.session.flush()
            return existing

        defn = Definition(kind=kind, name=name, version=version, frontmatter=frontmatter, body=body)
        self.session.add(defn)
        await self.session.flush()
        return defn

    async def delete(self, kind: str, name: str) -> bool:
        existing = await self.get(kind, name)
        if existing is None:
            return False
        await self.session.execute(
            sa_delete(Definition).where(Definition.kind == kind, Definition.name == name)
        )
        return True
