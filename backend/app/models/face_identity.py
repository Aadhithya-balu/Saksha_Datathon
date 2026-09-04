"""DEMO face-identity records for the isolated face-recognition feature.

Issue #228 keeps the face-recognition capability fully isolated: it never
touches crime-case / FIR / evidence tables. These records hold *metadata only*
(demo ID, display name, dataset label, created timestamp) plus a reference to
the synthetic image set. The actual synthetic images live on the filesystem /
object store, not as raw binaries in the database, so this table stays tiny and
can later be swapped for an authorized production dataset without changing the
recognition service (see ``app/ai/face/repository.py``).

Every record is explicitly labelled ``dataset_type = DEMO`` and is populated
from fictional, consented, synthetic subjects — never real criminal/photograph
data.
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.postgres import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class FaceIdentity(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "face_identities"

    # Stable public demo identifier, e.g. "DEMO-001".
    demo_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    # Display name for the demo subject.
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Synthetic image set reference. A relative storage key / directory under the
    # face dataset root (not an absolute path, never exposed to the UI).
    image_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    # Number of synthetic images registered for this identity (4-5 per subject).
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Always "DEMO" for this prototype dataset. Enables a later authorized
    # production dataset to be distinguished cleanly.
    dataset_type: Mapped[str] = mapped_column(String(16), nullable=False, default="DEMO", index=True)
