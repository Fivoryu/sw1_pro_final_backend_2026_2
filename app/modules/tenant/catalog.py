from dataclasses import dataclass
from decimal import Decimal

from app.modules.tenant.models import Plan


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    codigo: str
    nombre: str
    precio_bob: Decimal
    max_agents: int
    cuota_almacenamiento_gb: int
    cuota_inmuebles: int
    cuota_reconstrucciones_mes: int


APPROVED_PLAN_DEFINITIONS = (
    PlanDefinition("basico", "Básico", Decimal("199.00"), 5, 50, 5, 10),
    PlanDefinition("profesional", "Profesional", Decimal("449.00"), 15, 200, 20, 40),
    PlanDefinition("empresarial", "Empresarial", Decimal("899.00"), 50, 1000, 100, 150),
)
APPROVED_PLAN_CODES = frozenset(d.codigo for d in APPROVED_PLAN_DEFINITIONS)


def is_approved_active_plan(plan: Plan) -> bool:
    definition = next((d for d in APPROVED_PLAN_DEFINITIONS if d.codigo == plan.codigo), None)
    return bool(
        plan.activo
        and definition
        and plan.nombre == definition.nombre
        and Decimal(str(plan.precio_bob)) == definition.precio_bob
        and plan.max_agents == definition.max_agents
        and plan.cuota_almacenamiento_gb == definition.cuota_almacenamiento_gb
        and plan.cuota_inmuebles == definition.cuota_inmuebles
        and plan.cuota_reconstrucciones_mes == definition.cuota_reconstrucciones_mes
    )
