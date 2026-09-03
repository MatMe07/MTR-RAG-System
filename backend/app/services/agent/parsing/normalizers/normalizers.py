# query_parser/normalizers.py



def normalize_decimal(value: str) -> float:
    value = value.replace(",", ".")
    return float(value)



def normalize_steel(value: str) -> str:
    return value.upper()


def normalize_strength_class(value: str) -> str:
    return value.upper().replace(" ", "")
