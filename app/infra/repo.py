"""Repository — the only place that touches the DB for the Plan aggregate."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.plan import Plan, new_id
from app.infra.models import Plan as PlanORM


class PlanRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def find_by_id(self, plan_id: UUID) -> Plan | None:
        stmt = select(PlanORM).where(PlanORM.id == plan_id)
        r = (await self.s.execute(stmt)).scalar_one_or_none()
        return _row_to_plan(r) if r else None

    async def list_all(self) -> list[Plan]:
        stmt = select(PlanORM).order_by(PlanORM.plan_code)
        rows = (await self.s.execute(stmt)).scalars().all()
        return [_row_to_plan(r) for r in rows]

    async def find_by_code(self, plan_code: str) -> Plan | None:
        stmt = select(PlanORM).where(PlanORM.plan_code == plan_code)
        r = (await self.s.execute(stmt)).scalar_one_or_none()
        return _row_to_plan(r) if r else None

    async def upsert(self, p: Plan) -> Plan:
        existing = await self.find_by_code(p.plan_code)
        if existing is None:
            plan_id = p.id or new_id()
            orm = PlanORM(
                id=plan_id,
                plan_code=p.plan_code,
                name=p.name,
                type=p.type,
                metal_level=p.metal_level,
                attributes=p.attributes or {},
                version=1,
            )
            self.s.add(orm)
            await self.s.flush()
            p.id = plan_id
            p.version = 1
            return p
        stmt = (
            update(PlanORM)
            .where(PlanORM.id == existing.id)
            .values(
                name=p.name,
                type=p.type,
                metal_level=p.metal_level,
                attributes=p.attributes or {},
                version=PlanORM.version + 1,
            )
        )
        await self.s.execute(stmt)
        existing.name = p.name
        existing.type = p.type
        existing.metal_level = p.metal_level
        existing.attributes = p.attributes or {}
        existing.version += 1
        return existing


def _row_to_plan(r: Any) -> Plan:
    return Plan(
        id=r.id,
        plan_code=r.plan_code,
        name=r.name,
        type=r.type,
        metal_level=r.metal_level,
        attributes=dict(r.attributes) if r.attributes else {},
        version=r.version,
    )
