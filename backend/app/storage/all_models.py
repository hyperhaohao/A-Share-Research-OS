"""Central model registry: importing this module registers every ORM table
into ``Base.metadata`` for Alembic autogenerate."""

from app.storage.orm import Base, WatchlistORM  # noqa: F401
from app.storage.instrument_repo import InstrumentRegistryORM  # noqa: F401
from app.storage.research_orm import ClaimORM, CorporateEventORM, ThesisORM  # noqa: F401
from app.storage.quality_orm import QualityGateResultORM  # noqa: F401
from app.storage.agent_repo import AnalystBriefORM, ResearchRequestORM  # noqa: F401
from app.services.debate_engine import DebateRoundORM, ScenarioORM  # noqa: E402, F401
from app.storage.valuation_repo import ValuationORM  # noqa: F401
from app.storage.report_repo import ReportORM  # noqa: F401
from app.storage.manifest_repo import ReportVersionORM, RunManifestORM  # noqa: F401
from app.storage.revision_repo import RevisionProposalORM  # noqa: F401
from app.storage.prediction_repo import PredictionORM, ValidationORM  # noqa: F401
from app.api.regression import RegressionReviewORM, ResearchExperienceORM  # noqa: F401
from app.scheduler.tasks import ResearchTaskORM  # noqa: F401
from app.services.monitor import MaterialityDecisionORM  # noqa: F401
from app.application.artifacts import ArtifactORM, ProvenanceEdgeORM  # noqa: F401
from app.application.run_events import RunEventORM  # noqa: F401
from app.application.handoff import HandoffORM  # noqa: F401
from app.application.experience import (  # noqa: F401
    ExperienceCardORM,
    ExperienceCardVersionORM,
    ExperienceValidationORM,
)
from app.application.conversation import (  # noqa: F401
    ConversationSessionORM,
    ConversationTurnORM,
    ResearchPlanORM,
)
from app.services.report_qa import ReportAskORM  # noqa: F401

_ = Base
