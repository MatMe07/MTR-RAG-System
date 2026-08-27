from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    EXPERT = "expert"
    AUDITOR = "auditor"
    ADMIN = "admin"


class RequestStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    REQUIRES_EXPERT = "requires_expert"
    UNCLEAR = "unclear"
    NOT_FOUND = "not_found"


class SearchMode(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class OcrStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class MatchStatus(str, Enum):
    MATCHES = "соответствует"
    POTENTIAL = "потенциальный аналог"
    NO_MATCH = "не соответствует"
    NO_DATA = "нет данных"
    REQUIRES_CHECK = "требует проверки"
    REQUIRES_EXPERT = "требует экспертной проверки"


class DetailLevel(str, Enum):
    BASIC = "basic"
    WITH_STOCK = "with_stock"
    FULL = "full"


BLOCKER_FIELDS = {"dn", "pn", "item_type", "material", "medium"}
