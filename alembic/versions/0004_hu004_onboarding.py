"""Additive HU-004 onboarding persistence and catalog seed."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence, Union
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFINITIONS = (
    (
        "basico",
        "Básico",
        Decimal("199.00"),
        5,
        50,
        5,
        10,
        UUID("00000000-0000-4000-8000-000000000001"),
    ),
    (
        "profesional",
        "Profesional",
        Decimal("449.00"),
        15,
        200,
        20,
        40,
        UUID("00000000-0000-4000-8000-000000000002"),
    ),
    (
        "empresarial",
        "Empresarial",
        Decimal("899.00"),
        50,
        1000,
        100,
        150,
        UUID("00000000-0000-4000-8000-000000000003"),
    ),
)

_PLANS = sa.table(
    "plan",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("codigo", sa.String(20)),
    sa.column("nombre", sa.String(60)),
    sa.column("precio_bob", sa.Numeric(10, 2)),
    sa.column("max_agents", sa.Integer),
    sa.column("cuota_almacenamiento_gb", sa.Integer),
    sa.column("cuota_inmuebles", sa.Integer),
    sa.column("cuota_reconstrucciones_mes", sa.Integer),
    sa.column("activo", sa.Boolean),
)


def _matches(row: sa.RowMapping, plan: tuple, legacy: bool = False) -> bool:
    return (
        row["nombre"] == plan[1]
        and Decimal(str(row["precio_bob"])) == plan[2]
        and (row["max_agents"] == plan[3] or (legacy and row["max_agents"] is None))
        and row["cuota_almacenamiento_gb"] == plan[4]
        and row["cuota_inmuebles"] == plan[5]
        and row["cuota_reconstrucciones_mes"] == plan[6]
        and bool(row["activo"])
    )


def _seed_plans() -> None:
    conn = op.get_bind()
    for plan in _DEFINITIONS:
        code = plan[0]
        by_code = conn.execute(sa.select(_PLANS).where(_PLANS.c.codigo == code)).mappings().all()
        if len(by_code) > 1:
            raise RuntimeError(f"Más de un plan usa el código {code}")
        if by_code:
            if not _matches(by_code[0], plan):
                raise RuntimeError(f"El plan {code} tiene datos comerciales incompatibles")
            continue
        by_name = conn.execute(sa.select(_PLANS).where(_PLANS.c.nombre == plan[1])).mappings().all()
        if len(by_name) > 1:
            raise RuntimeError(f"Colisión de adopción para el plan {code}")
        if by_name:
            if not _matches(by_name[0], plan, legacy=True):
                raise RuntimeError(f"Discrepancia de adopción para el plan {code}")
            conn.execute(
                _PLANS.update()
                .where(_PLANS.c.id == by_name[0]["id"])
                .values(codigo=code, max_agents=plan[3])
            )
            continue
        conn.execute(
            _PLANS.insert().values(
                id=plan[7],
                codigo=code,
                nombre=plan[1],
                precio_bob=plan[2],
                max_agents=plan[3],
                cuota_almacenamiento_gb=plan[4],
                cuota_inmuebles=plan[5],
                cuota_reconstrucciones_mes=plan[6],
                activo=True,
            )
        )


def upgrade() -> None:
    op.add_column("plan", sa.Column("codigo", sa.String(20), nullable=True))
    op.add_column("plan", sa.Column("max_agents", sa.Integer(), nullable=True))
    op.create_table(
        "checkout_intencion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plan.id"), nullable=False
        ),
        sa.Column("nombre_empresa", sa.String(120), nullable=False),
        sa.Column("correo_admin", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("invitacion", sa.Column("consumido_en", sa.DateTime(timezone=True)))
    op.add_column("evento_facturacion", sa.Column("checkout_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_evento_facturacion_checkout",
        "evento_facturacion",
        "checkout_intencion",
        ["checkout_id"],
        ["id"],
    )
    op.add_column("evento_facturacion", sa.Column("payload_hash", sa.CHAR(64), nullable=True))
    _seed_plans()
    op.create_unique_constraint("uq_plan_codigo", "plan", ["codigo"])
    op.create_index(
        "uq_evento_facturacion_checkout",
        "evento_facturacion",
        ["checkout_id"],
        unique=True,
        postgresql_where=sa.text("checkout_id IS NOT NULL"),
    )


def _has_data(conn: sa.Connection, table: sa.TableClause, condition: Any = None) -> bool:
    query = sa.select(sa.func.count()).select_from(table)
    return bool(conn.scalar(query if condition is None else query.where(condition)))


def downgrade() -> None:
    conn = op.get_bind()
    checkout = sa.table("checkout_intencion", sa.column("id", postgresql.UUID(as_uuid=True)))
    event = sa.table(
        "evento_facturacion",
        sa.column("checkout_id", postgresql.UUID(as_uuid=True)),
        sa.column("payload_hash", sa.CHAR(64)),
    )
    invitation = sa.table("invitacion", sa.column("consumido_en", sa.DateTime(timezone=True)))
    if _has_data(conn, checkout):
        raise RuntimeError("No se puede degradar con checkouts de HU-004")
    if _has_data(
        conn, event, sa.or_(event.c.checkout_id.is_not(None), event.c.payload_hash.is_not(None))
    ):
        raise RuntimeError("No se puede degradar con eventos de HU-004")
    if _has_data(conn, invitation, invitation.c.consumido_en.is_not(None)):
        raise RuntimeError("No se puede degradar con activaciones consumidas")
    op.drop_index("uq_evento_facturacion_checkout", table_name="evento_facturacion")
    op.drop_constraint("fk_evento_facturacion_checkout", "evento_facturacion", type_="foreignkey")
    op.drop_column("evento_facturacion", "payload_hash")
    op.drop_column("evento_facturacion", "checkout_id")
    op.drop_column("invitacion", "consumido_en")
    op.drop_table("checkout_intencion")
    op.drop_constraint("uq_plan_codigo", "plan", type_="unique")
    op.drop_column("plan", "max_agents")
    op.drop_column("plan", "codigo")
