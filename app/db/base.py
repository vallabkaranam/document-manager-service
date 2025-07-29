from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from app.db.models import document
from app.db.models import tag
from app.db.models import document_tag
from app.db.models import summary
from app.db.models import document_embedding