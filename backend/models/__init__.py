# Import all ORM models here so SQLAlchemy's mapper registry is fully
# populated before any relationship() string reference is resolved.
# This file runs whenever any `from models.X import Y` is executed,
# because Python always initialises the package before a submodule.
from models.database import Base  # noqa: F401
from models.perfume import Note, Perfume, PerfumeNote  # noqa: F401
from models.prediction import PredictionResult  # noqa: F401
from models.review import UserReview  # noqa: F401
