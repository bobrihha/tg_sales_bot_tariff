"""
Каталог операторов и тарифов с хранением в JSON.
"""
import copy
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


_STORE_PATH = Path(__file__).resolve().parent / "store.json"
_LOCK = threading.Lock()
_UNSET = object()


@dataclass
class Operator:
    """Модель оператора"""
    id: int
    name: str


@dataclass
class Tariff:
    """Модель тарифа"""
    id: int
    operator_id: int
    name: str
    description: str
    monthly_fee: Optional[int]
    connection_price: int
    is_public: bool


@dataclass
class PaymentMethod:
    """Модель способа оплаты (банк/карта)"""
    id: int
    name: str           # Название банка
    details: str        # Реквизиты (номер карты, ФИО и т.д.)
    is_active: bool     # Активен ли способ оплаты


_DEFAULT_OPERATORS = [
    {"id": 1, "name": "MTS"},
    {"id": 2, "name": "Megafon"},
    {"id": 3, "name": "Beeline"},
    {"id": 4, "name": "T2"},
    {"id": 5, "name": "Yota"},
]

_DEFAULT_STORE = {
    "operators": _DEFAULT_OPERATORS,
    "tariffs": [],
    "payment_methods": [],
    "next_operator_id": 6,
    "next_tariff_id": 1,
    "next_payment_method_id": 1,
}


def _save_store(store: dict) -> None:
    with _STORE_PATH.open("w", encoding="utf-8") as file:
        json.dump(store, file, ensure_ascii=True, indent=2)


def _next_id(items: List[dict]) -> int:
    max_id = 0
    for item in items:
        value = item.get("id")
        if isinstance(value, int) and value > max_id:
            max_id = value
    return max_id + 1


def _normalize_store(store: dict) -> dict:
    changed = False
    if not store:
        store = copy.deepcopy(_DEFAULT_STORE)
        changed = True

    if "operators" not in store:
        store["operators"] = copy.deepcopy(_DEFAULT_OPERATORS)
        changed = True
    if "tariffs" not in store:
        store["tariffs"] = []
        changed = True
    if "payment_methods" not in store:
        store["payment_methods"] = []
        changed = True
    if "next_operator_id" not in store:
        store["next_operator_id"] = _next_id(store.get("operators", []))
        changed = True
    if "next_tariff_id" not in store:
        store["next_tariff_id"] = _next_id(store.get("tariffs", []))
        changed = True
    if "next_payment_method_id" not in store:
        store["next_payment_method_id"] = _next_id(store.get("payment_methods", []))
        changed = True

    if changed:
        _save_store(store)
    return store


def _load_store() -> dict:
    if not _STORE_PATH.exists():
        store = copy.deepcopy(_DEFAULT_STORE)
        _save_store(store)
        return store

    with _STORE_PATH.open("r", encoding="utf-8") as file:
        store = json.load(file)

    return _normalize_store(store)


def get_all_operators() -> List[Operator]:
    """Получить список операторов"""
    with _LOCK:
        store = _load_store()
        return [Operator(**operator) for operator in store["operators"]]


def get_operator_by_id(operator_id: int) -> Optional[Operator]:
    """Получить оператора по ID"""
    with _LOCK:
        store = _load_store()
        for operator in store["operators"]:
            if operator.get("id") == operator_id:
                return Operator(**operator)
    return None


def add_operator(name: str) -> Operator:
    """Добавить оператора"""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("operator name is empty")

    with _LOCK:
        store = _load_store()
        operator = {"id": store["next_operator_id"], "name": clean_name}
        store["next_operator_id"] += 1
        store["operators"].append(operator)
        _save_store(store)
        return Operator(**operator)


def delete_operator(operator_id: int) -> bool:
    """Удалить оператора и его тарифы"""
    with _LOCK:
        store = _load_store()
        operators_before = len(store["operators"])
        store["operators"] = [
            operator for operator in store["operators"]
            if operator.get("id") != operator_id
        ]
        if len(store["operators"]) == operators_before:
            return False

        store["tariffs"] = [
            tariff for tariff in store["tariffs"]
            if tariff.get("operator_id") != operator_id
        ]
        _save_store(store)
        return True


def get_tariffs_by_operator(
    operator_id: int,
    include_hidden: bool = False,
) -> List[Tariff]:
    """Получить список тарифов оператора"""
    with _LOCK:
        store = _load_store()
        tariffs = []
        for tariff in store["tariffs"]:
            if tariff.get("operator_id") != operator_id:
                continue
            if not include_hidden and not tariff.get("is_public", False):
                continue
            tariffs.append(Tariff(**tariff))
        return tariffs


def get_tariff_by_id(tariff_id: int) -> Optional[Tariff]:
    """Получить тариф по ID"""
    with _LOCK:
        store = _load_store()
        for tariff in store["tariffs"]:
            if tariff.get("id") == tariff_id:
                return Tariff(**tariff)
    return None


def add_tariff(
    operator_id: int,
    name: str,
    description: str,
    monthly_fee: Optional[int],
    connection_price: int,
    is_public: bool,
) -> Tariff:
    """Добавить тариф"""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("tariff name is empty")

    with _LOCK:
        store = _load_store()
        tariff = {
            "id": store["next_tariff_id"],
            "operator_id": operator_id,
            "name": clean_name,
            "description": description.strip(),
            "monthly_fee": monthly_fee,
            "connection_price": connection_price,
            "is_public": bool(is_public),
        }
        store["next_tariff_id"] += 1
        store["tariffs"].append(tariff)
        _save_store(store)
        return Tariff(**tariff)


def update_tariff(
    tariff_id: int,
    *,
    name: object = _UNSET,
    description: object = _UNSET,
    monthly_fee: object = _UNSET,
    connection_price: object = _UNSET,
    is_public: object = _UNSET,
) -> Optional[Tariff]:
    """Обновить тариф"""
    with _LOCK:
        store = _load_store()
        for tariff in store["tariffs"]:
            if tariff.get("id") != tariff_id:
                continue

            if name is not _UNSET:
                clean_name = str(name).strip()
                if not clean_name:
                    raise ValueError("tariff name is empty")
                tariff["name"] = clean_name

            if description is not _UNSET:
                tariff["description"] = str(description).strip()

            if monthly_fee is not _UNSET:
                tariff["monthly_fee"] = monthly_fee

            if connection_price is not _UNSET:
                tariff["connection_price"] = connection_price

            if is_public is not _UNSET:
                tariff["is_public"] = bool(is_public)

            _save_store(store)
            return Tariff(**tariff)
    return None


def delete_tariff(tariff_id: int) -> bool:
    """Удалить тариф"""
    with _LOCK:
        store = _load_store()
        tariffs_before = len(store["tariffs"])
        store["tariffs"] = [
            tariff for tariff in store["tariffs"]
            if tariff.get("id") != tariff_id
        ]
        if len(store["tariffs"]) == tariffs_before:
            return False
        _save_store(store)
        return True


def toggle_tariff_visibility(tariff_id: int) -> Optional[Tariff]:
    """Переключить видимость тарифа"""
    with _LOCK:
        store = _load_store()
        for tariff in store["tariffs"]:
            if tariff.get("id") == tariff_id:
                tariff["is_public"] = not tariff.get("is_public", False)
                _save_store(store)
                return Tariff(**tariff)
    return None


def format_tariff_info(tariff: Tariff, operator_name: Optional[str] = None) -> str:
    """Форматирование информации о тарифе"""
    lines = [f"<b>{tariff.name}</b>"]
    if operator_name:
        lines.append(f"📡 Оператор: <b>{operator_name}</b>")
    lines.append("")

    if tariff.description:
        lines.append(tariff.description)
        lines.append("")

    if tariff.monthly_fee:
        lines.append(f"📅 Абонплата: <b>{tariff.monthly_fee:,} ₽/мес</b>")
    lines.append(f"💳 Стоимость подключения: <b>{tariff.connection_price:,} ₽</b>")
    return "\n".join(lines)


# ============== PaymentMethod CRUD ==============

def get_all_payment_methods() -> List[PaymentMethod]:
    """Получить все способы оплаты"""
    with _LOCK:
        store = _load_store()
        return [PaymentMethod(**pm) for pm in store.get("payment_methods", [])]


def get_active_payment_methods() -> List[PaymentMethod]:
    """Получить только активные способы оплаты"""
    with _LOCK:
        store = _load_store()
        methods = []
        for pm in store.get("payment_methods", []):
            if pm.get("is_active", False):
                methods.append(PaymentMethod(**pm))
        return methods


def get_payment_method_by_id(method_id: int) -> Optional[PaymentMethod]:
    """Получить способ оплаты по ID"""
    with _LOCK:
        store = _load_store()
        for pm in store.get("payment_methods", []):
            if pm.get("id") == method_id:
                return PaymentMethod(**pm)
    return None


def add_payment_method(name: str, details: str) -> PaymentMethod:
    """Добавить способ оплаты"""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("payment method name is empty")

    with _LOCK:
        store = _load_store()
        payment_method = {
            "id": store["next_payment_method_id"],
            "name": clean_name,
            "details": details.strip(),
            "is_active": True,
        }
        store["next_payment_method_id"] += 1
        store["payment_methods"].append(payment_method)
        _save_store(store)
        return PaymentMethod(**payment_method)


def update_payment_method(
    method_id: int,
    *,
    name: object = _UNSET,
    details: object = _UNSET,
) -> Optional[PaymentMethod]:
    """Обновить способ оплаты"""
    with _LOCK:
        store = _load_store()
        for pm in store.get("payment_methods", []):
            if pm.get("id") != method_id:
                continue

            if name is not _UNSET:
                clean_name = str(name).strip()
                if not clean_name:
                    raise ValueError("payment method name is empty")
                pm["name"] = clean_name

            if details is not _UNSET:
                pm["details"] = str(details).strip()

            _save_store(store)
            return PaymentMethod(**pm)
    return None


def delete_payment_method(method_id: int) -> bool:
    """Удалить способ оплаты"""
    with _LOCK:
        store = _load_store()
        methods_before = len(store.get("payment_methods", []))
        store["payment_methods"] = [
            pm for pm in store.get("payment_methods", [])
            if pm.get("id") != method_id
        ]
        if len(store["payment_methods"]) == methods_before:
            return False
        _save_store(store)
        return True


def toggle_payment_method(method_id: int) -> Optional[PaymentMethod]:
    """Переключить активность способа оплаты"""
    with _LOCK:
        store = _load_store()
        for pm in store.get("payment_methods", []):
            if pm.get("id") == method_id:
                pm["is_active"] = not pm.get("is_active", False)
                _save_store(store)
                return PaymentMethod(**pm)
    return None

