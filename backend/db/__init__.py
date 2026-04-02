from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .models import (
    ApiGroups, User, ApiSettings, GroupSettings, GroupSubjects,
    PlaybookTemplates, SubjectSources, SubjectSourceRuns,
    Analyses, Reports,
    Conversations, ConversationMessages,
)
