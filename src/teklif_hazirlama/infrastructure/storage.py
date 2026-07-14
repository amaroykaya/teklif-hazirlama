from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

from teklif_hazirlama.core.models import CustomerConfig, HitapKisi
from teklif_hazirlama.paths import CUSTOMERS, HITAP

BUILTIN_CUSTOMER_CODES = {"roketsan"}


def _normalize_person_name(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s")
    text = text.replace("ö", "o").replace("ç", "c").replace("İ", "i")
    return " ".join(text.split())


def slugify_code(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s")
    text = text.replace("ö", "o").replace("ç", "c")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "musteri"


def load_hitap_list(musteri_kodu: str, hitap_dir: Path | None = None) -> list[HitapKisi]:
    directory = hitap_dir or HITAP
    path = directory / f"{musteri_kodu}.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    contacts: list[HitapKisi] = []
    for item in data.get("kisiler", []):
        ad = str(item.get("ad", "")).strip()
        if not ad:
            continue
        contacts.append(
            HitapKisi(
                ad=ad,
                musteri_kodu=musteri_kodu,
                telefon=str(item.get("telefon", "")).strip(),
            )
        )
    return contacts


class CustomerRepository:
    def __init__(self, customers_dir: Path | None = None, user_customers_dir: Path | None = None):
        self.customers_dir = customers_dir or CUSTOMERS
        appdata = Path(os.environ.get("APPDATA", Path.home()))
        self.user_customers_dir = user_customers_dir or appdata / "TeklifHazirlama" / "customers"
        self.user_customers_dir.mkdir(parents=True, exist_ok=True)

    def _hidden_path(self) -> Path:
        return self.user_customers_dir / "_hidden.json"

    def _load_hidden(self) -> set[str]:
        path = self._hidden_path()
        if not path.exists():
            return set()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {str(item) for item in data.get("codes", [])}
        except (json.JSONDecodeError, OSError, TypeError):
            return set()

    def _save_hidden(self, codes: set[str]) -> None:
        path = self._hidden_path()
        path.write_text(
            json.dumps({"codes": sorted(codes)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_customers(self) -> list[CustomerConfig]:
        hidden = self._load_hidden()
        configs: dict[str, CustomerConfig] = {}
        for path in sorted(self.customers_dir.glob("*.yaml")):
            if path.stem in BUILTIN_CUSTOMER_CODES and path.stem not in hidden:
                configs[path.stem] = self._load_file(path)
        for path in sorted(self.user_customers_dir.glob("*.yaml")):
            if path.stem.startswith("_"):
                continue
            if path.stem in hidden:
                continue
            configs[path.stem] = self._load_file(path)
        return [configs[key] for key in sorted(configs)]

    def load(self, code: str) -> CustomerConfig:
        user_path = self.user_customers_dir / f"{code}.yaml"
        if user_path.exists():
            return self._load_file(user_path)
        path = self.customers_dir / f"{code}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Müşteri bulunamadı: {code}")
        return self._load_file(path)

    def save(self, customer: CustomerConfig) -> None:
        path = self.user_customers_dir / f"{customer.code}.yaml"
        data = customer.model_dump()
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        hidden = self._load_hidden()
        if customer.code in hidden:
            hidden.discard(customer.code)
            self._save_hidden(hidden)

    def delete(self, code: str) -> None:
        user_path = self.user_customers_dir / f"{code}.yaml"
        if user_path.exists():
            user_path.unlink()
        # Varsayılan (roketsan) silinince şablon dosyası kalır; listeden gizlenir.
        if code in BUILTIN_CUSTOMER_CODES or (self.customers_dir / f"{code}.yaml").exists():
            hidden = self._load_hidden()
            hidden.add(code)
            self._save_hidden(hidden)

    def is_builtin(self, code: str) -> bool:
        return code in BUILTIN_CUSTOMER_CODES

    def _load_file(self, path: Path) -> CustomerConfig:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return CustomerConfig.model_validate(data)


class LocalStore:
    def __init__(self, path: Path | None = None, hitap_dir: Path | None = None):
        appdata = Path(os.environ.get("APPDATA", Path.home()))
        self.path = path or appdata / "TeklifHazirlama" / "local.json"
        self.hitap_dir = hitap_dir or HITAP
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _default_data(self) -> dict:
        return {
            "hitap_overrides": [],
            "hitap_custom": [],
            "hitap_hidden": [],
            "hazirlayanlar": ["Alican Uzun"],
            "teslimatlar": ["Yurtiçi Kargo"],
            "teslimat_sekilleri": ["Kapı Teslim"],
            "odeme_sekilleri": [],
            "ozel_sartlar": [],
            "son_hitap": {},
        }

    def _load(self) -> dict:
        if not self.path.exists():
            return self._default_data()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        migrated, changed = self._migrate(data)
        if changed:
            self.path.write_text(json.dumps(migrated, ensure_ascii=False, indent=2), encoding="utf-8")
        return migrated

    def _migrate(self, data: dict) -> tuple[dict, bool]:
        changed = False
        defaults = self._default_data()
        for key, value in defaults.items():
            if key not in data:
                data[key] = value
                changed = True

        if "hitap_kisileri" in data:
            overrides = data.setdefault("hitap_overrides", [])
            for item in data.get("hitap_kisileri", []):
                if isinstance(item, str):
                    payload = {"ad": item, "musteri_kodu": "", "telefon": ""}
                else:
                    payload = {
                        "ad": item.get("ad", ""),
                        "musteri_kodu": item.get("musteri_kodu", ""),
                        "telefon": item.get("telefon", ""),
                    }
                if payload["ad"]:
                    overrides.append(payload)
            del data["hitap_kisileri"]
            changed = True

        return data, changed

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_list(self, key: str) -> list[str]:
        return list(self._data.get(key, []))

    def add_unique(self, key: str, value: str) -> None:
        value = value.strip()
        if not value:
            return
        items = self._data.setdefault(key, [])
        if value not in items:
            items.append(value)
            self.save()

    def add_list_item(self, key: str, value: str) -> None:
        value = value.strip()
        if not value:
            return
        items = self._data.setdefault(key, [])
        if value in items:
            raise ValueError("Bu kayıt zaten mevcut.")
        items.append(value)
        self.save()

    def update_list_item(self, key: str, old_value: str, new_value: str) -> None:
        old_value = old_value.strip()
        new_value = new_value.strip()
        if not new_value:
            raise ValueError("Değer boş olamaz.")
        items = self._data.setdefault(key, [])
        if new_value != old_value and new_value in items:
            raise ValueError("Bu kayıt zaten mevcut.")
        for index, item in enumerate(items):
            if item == old_value:
                items[index] = new_value
                self.save()
                return
        raise ValueError("Kayıt bulunamadı.")

    def remove_list_item(self, key: str, value: str) -> None:
        value = value.strip()
        items = self._data.setdefault(key, [])
        if value in items:
            items.remove(value)
            self.save()

    def _hidden_set(self, musteri_kodu: str) -> set[str]:
        return {
            _normalize_person_name(item.get("ad", ""))
            for item in self._data.get("hitap_hidden", [])
            if item.get("musteri_kodu") == musteri_kodu and item.get("ad")
        }

    def _override_map(self, musteri_kodu: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in self._data.get("hitap_overrides", []):
            if item.get("musteri_kodu") != musteri_kodu:
                continue
            ad = str(item.get("ad", "")).strip()
            if ad:
                result[_normalize_person_name(ad)] = str(item.get("telefon", "")).strip()
        return result

    def _custom_contacts(self, musteri_kodu: str) -> list[HitapKisi]:
        contacts: list[HitapKisi] = []
        for item in self._data.get("hitap_custom", []):
            if item.get("musteri_kodu") != musteri_kodu:
                continue
            ad = str(item.get("ad", "")).strip()
            if not ad:
                continue
            contacts.append(
                HitapKisi(
                    ad=ad,
                    musteri_kodu=musteri_kodu,
                    telefon=str(item.get("telefon", "")).strip(),
                )
            )
        return contacts

    def is_builtin_hitap(self, musteri_kodu: str, ad: str) -> bool:
        key = _normalize_person_name(ad)
        for person in load_hitap_list(musteri_kodu, self.hitap_dir):
            if _normalize_person_name(person.ad) == key:
                return True
        return False

    def get_hitap_kisileri(self, musteri_kodu: str | None = None) -> list[HitapKisi]:
        if not musteri_kodu:
            return []
        builtin = load_hitap_list(musteri_kodu, self.hitap_dir)
        hidden = self._hidden_set(musteri_kodu)
        overrides = self._override_map(musteri_kodu)
        contacts: list[HitapKisi] = []
        seen: set[str] = set()

        for person in builtin:
            key = _normalize_person_name(person.ad)
            if key in hidden:
                continue
            telefon = overrides.get(key, person.telefon)
            contacts.append(
                HitapKisi(
                    ad=person.ad,
                    musteri_kodu=musteri_kodu,
                    telefon=telefon,
                )
            )
            seen.add(key)

        for person in self._custom_contacts(musteri_kodu):
            key = _normalize_person_name(person.ad)
            if key in seen:
                continue
            telefon = overrides.get(key, person.telefon)
            contacts.append(
                HitapKisi(
                    ad=person.ad,
                    musteri_kodu=musteri_kodu,
                    telefon=telefon,
                )
            )
            seen.add(key)

        return contacts

    def save_hitap_kisi(self, contact: HitapKisi, original_ad: str | None = None) -> None:
        ad = contact.ad.strip()
        if not ad:
            raise ValueError("Hitap kişisi adı zorunludur.")
        orig = (original_ad or contact.ad).strip()
        orig_key = _normalize_person_name(orig)
        new_key = _normalize_person_name(ad)

        if self.is_builtin_hitap(contact.musteri_kodu, orig) and orig_key == new_key:
            self._save_hitap_override(contact)
            return

        custom = self._data.setdefault("hitap_custom", [])
        payload = {
            "ad": ad,
            "musteri_kodu": contact.musteri_kodu,
            "telefon": contact.telefon.strip(),
        }
        for index, item in enumerate(custom):
            if item.get("musteri_kodu") == contact.musteri_kodu and _normalize_person_name(item.get("ad", "")) == orig_key:
                custom[index] = payload
                self._remove_hitap_override(contact.musteri_kodu, orig)
                if orig_key != new_key:
                    self._save_hitap_override(contact)
                self.save()
                return
        custom.append(payload)
        self.save()

    def delete_hitap_kisi(self, musteri_kodu: str, ad: str) -> None:
        key = _normalize_person_name(ad)
        custom = self._data.setdefault("hitap_custom", [])
        before = len(custom)
        custom[:] = [
            item
            for item in custom
            if not (item.get("musteri_kodu") == musteri_kodu and _normalize_person_name(item.get("ad", "")) == key)
        ]
        self._remove_hitap_override(musteri_kodu, ad)
        if len(custom) < before:
            self.save()
            return
        if self.is_builtin_hitap(musteri_kodu, ad):
            hidden = self._data.setdefault("hitap_hidden", [])
            if not any(
                item.get("musteri_kodu") == musteri_kodu and _normalize_person_name(item.get("ad", "")) == key
                for item in hidden
            ):
                hidden.append({"ad": ad.strip(), "musteri_kodu": musteri_kodu})
            self.save()

    def delete_hitap_for_customer(self, musteri_kodu: str) -> None:
        self._data["hitap_custom"] = [
            item for item in self._data.get("hitap_custom", []) if item.get("musteri_kodu") != musteri_kodu
        ]
        self._data["hitap_overrides"] = [
            item for item in self._data.get("hitap_overrides", []) if item.get("musteri_kodu") != musteri_kodu
        ]
        self._data["hitap_hidden"] = [
            item for item in self._data.get("hitap_hidden", []) if item.get("musteri_kodu") != musteri_kodu
        ]
        son_hitap = self._data.get("son_hitap", {})
        if musteri_kodu in son_hitap:
            del son_hitap[musteri_kodu]
        self.save()

    def _save_hitap_override(self, contact: HitapKisi) -> None:
        overrides = self._data.setdefault("hitap_overrides", [])
        payload = {
            "ad": contact.ad.strip(),
            "musteri_kodu": contact.musteri_kodu,
            "telefon": contact.telefon.strip(),
        }
        key = _normalize_person_name(contact.ad)
        for index, item in enumerate(overrides):
            if item.get("musteri_kodu") == contact.musteri_kodu and _normalize_person_name(item.get("ad", "")) == key:
                overrides[index] = payload
                self.save()
                return
        overrides.append(payload)
        self.save()

    def _remove_hitap_override(self, musteri_kodu: str, ad: str) -> None:
        key = _normalize_person_name(ad)
        overrides = self._data.setdefault("hitap_overrides", [])
        filtered = [
            item
            for item in overrides
            if not (item.get("musteri_kodu") == musteri_kodu and _normalize_person_name(item.get("ad", "")) == key)
        ]
        if len(filtered) != len(overrides):
            self._data["hitap_overrides"] = filtered

    def get_son_hitap(self, musteri_kodu: str) -> str | None:
        value = self._data.get("son_hitap", {}).get(musteri_kodu)
        return value.strip() if value else None

    def set_son_hitap(self, musteri_kodu: str, ad: str) -> None:
        son_hitap = self._data.setdefault("son_hitap", {})
        son_hitap[musteri_kodu] = ad.strip()
        self.save()

    def remember_quote_fields(self, header_fields: dict) -> None:
        mapping = {
            "hazirlayan": "hazirlayanlar",
            "teslimat": "teslimatlar",
            "teslimat_sekli": "teslimat_sekilleri",
        }
        for field, store_key in mapping.items():
            self.add_unique(store_key, header_fields.get(field, ""))
