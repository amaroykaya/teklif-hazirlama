import json
from pathlib import Path

import yaml

from teklif_hazirlama.core.models import HitapKisi
from teklif_hazirlama.infrastructure.storage import CustomerRepository, LocalStore, load_hitap_list


def test_builtin_customers_only_roketsan():
    repo = CustomerRepository()
    names = {c.code for c in repo.list_customers()}
    assert names == {"roketsan"}


def test_save_custom_customer(tmp_path):
    repo = CustomerRepository(
        customers_dir=Path("config/customers"),
        user_customers_dir=tmp_path / "customers",
    )
    customer = repo.load("roketsan")
    customer.code = "yeni_musteri"
    customer.name = "Yeni Müşteri A.Ş."
    repo.save(customer)

    loaded = repo.load("yeni_musteri")
    assert loaded.name == "Yeni Müşteri A.Ş."
    assert (tmp_path / "customers" / "yeni_musteri.yaml").exists()


def test_hitap_list_loaded_from_yaml(tmp_path):
    hitap_dir = tmp_path / "hitap"
    hitap_dir.mkdir()
    (hitap_dir / "roketsan.yaml").write_text(
        yaml.safe_dump(
            {
                "musteri_kodu": "roketsan",
                "kisiler": [
                    {"ad": "İremsu Yazıcı", "telefon": "111"},
                    {"ad": "Ali Veli", "telefon": "222"},
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    store = LocalStore(path=tmp_path / "local.json", hitap_dir=hitap_dir)
    contacts = store.get_hitap_kisileri("roketsan")
    assert len(contacts) == 2
    assert contacts[0].ad == "İremsu Yazıcı"
    assert contacts[0].telefon == "111"
    assert contacts[1].ad == "Ali Veli"


def test_hitap_telefon_override(tmp_path):
    hitap_dir = tmp_path / "hitap"
    hitap_dir.mkdir()
    (hitap_dir / "roketsan.yaml").write_text(
        yaml.safe_dump(
            {"musteri_kodu": "roketsan", "kisiler": [{"ad": "İremsu Yazıcı", "telefon": "111"}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    store = LocalStore(path=tmp_path / "local.json", hitap_dir=hitap_dir)
    store.save_hitap_kisi(HitapKisi(ad="İremsu Yazıcı", musteri_kodu="roketsan", telefon="Tel: 999"))

    contacts = store.get_hitap_kisileri("roketsan")
    assert len(contacts) == 1
    assert contacts[0].telefon == "Tel: 999"


def test_hitap_migration_from_legacy_format(tmp_path):
    path = tmp_path / "local.json"
    hitap_dir = tmp_path / "hitap"
    hitap_dir.mkdir()
    (hitap_dir / "roketsan.yaml").write_text(
        yaml.safe_dump(
            {
                "musteri_kodu": "roketsan",
                "kisiler": [
                    {"ad": "İremsu Yazıcı", "telefon": ""},
                    {"ad": "Başka Kişi", "telefon": ""},
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    path.write_text(
        json.dumps(
            {
                "hitap_kisileri": [
                    {
                        "ad": "İremsu Yazıcı",
                        "musteri_kodu": "roketsan",
                        "adres_satirlari": ["Adres 1"],
                        "telefon": "Tel: 123",
                    },
                    {
                        "ad": "Başka Kişi",
                        "musteri_kodu": "roketsan",
                        "adres_satirlari": ["Silinecek"],
                        "telefon": "Tel: 456",
                    },
                ],
                "hazirlayanlar": [],
                "teslimatlar": [],
                "teslimat_sekilleri": [],
                "odeme_sekilleri": [],
                "ozel_sartlar": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    store = LocalStore(path=path, hitap_dir=hitap_dir)
    contacts = store.get_hitap_kisileri("roketsan")
    assert len(contacts) == 2
    assert contacts[0].telefon == "Tel: 123"
    assert contacts[1].telefon == "Tel: 456"

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "hitap_kisileri" not in saved
    assert len(saved["hitap_overrides"]) == 2


def test_load_hitap_list_builtin_roketsan():
    contacts = load_hitap_list("roketsan", Path("config/hitap"))
    assert len(contacts) >= 1
    assert contacts[0].ad == "İremsu Yazıcı"


def test_hitap_custom_add_and_delete(tmp_path):
    hitap_dir = tmp_path / "hitap"
    hitap_dir.mkdir()
    (hitap_dir / "roketsan.yaml").write_text(
        yaml.safe_dump(
            {"musteri_kodu": "roketsan", "kisiler": [{"ad": "İremsu Yazıcı", "telefon": ""}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    store = LocalStore(path=tmp_path / "local.json", hitap_dir=hitap_dir)
    store.save_hitap_kisi(HitapKisi(ad="Yeni Kişi", musteri_kodu="roketsan", telefon="555"))
    contacts = store.get_hitap_kisileri("roketsan")
    assert len(contacts) == 2
    assert contacts[-1].ad == "Yeni Kişi"

    store.delete_hitap_kisi("roketsan", "Yeni Kişi")
    contacts = store.get_hitap_kisileri("roketsan")
    assert len(contacts) == 1


def test_hitap_builtin_delete_hides(tmp_path):
    hitap_dir = tmp_path / "hitap"
    hitap_dir.mkdir()
    (hitap_dir / "roketsan.yaml").write_text(
        yaml.safe_dump(
            {"musteri_kodu": "roketsan", "kisiler": [{"ad": "İremsu Yazıcı", "telefon": ""}]},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    store = LocalStore(path=tmp_path / "local.json", hitap_dir=hitap_dir)
    store.delete_hitap_kisi("roketsan", "İremsu Yazıcı")
    assert store.get_hitap_kisileri("roketsan") == []


def test_list_item_crud(tmp_path):
    store = LocalStore(path=tmp_path / "local.json")
    store.add_list_item("hazirlayanlar", "Test Kişi")
    assert "Test Kişi" in store.get_list("hazirlayanlar")
    store.update_list_item("hazirlayanlar", "Test Kişi", "Güncel Kişi")
    assert "Güncel Kişi" in store.get_list("hazirlayanlar")
    store.remove_list_item("hazirlayanlar", "Güncel Kişi")
    assert "Güncel Kişi" not in store.get_list("hazirlayanlar")


def test_delete_custom_customer(tmp_path):
    repo = CustomerRepository(
        customers_dir=Path("config/customers"),
        user_customers_dir=tmp_path / "customers",
    )
    customer = repo.load("roketsan")
    customer.code = "yeni_musteri"
    customer.name = "Yeni Müşteri"
    repo.save(customer)
    repo.delete("yeni_musteri")
    assert not (tmp_path / "customers" / "yeni_musteri.yaml").exists()


def test_edit_and_delete_builtin_roketsan(tmp_path):
    repo = CustomerRepository(
        customers_dir=Path("config/customers"),
        user_customers_dir=tmp_path / "customers",
    )
    customer = repo.load("roketsan")
    customer.name = "Roketsan Güncel"
    customer.firma["telefon"] = "Tel: 111"
    repo.save(customer)

    loaded = repo.load("roketsan")
    assert loaded.name == "Roketsan Güncel"
    assert loaded.firma["telefon"] == "Tel: 111"
    assert (tmp_path / "customers" / "roketsan.yaml").exists()

    repo.delete("roketsan")
    codes = {c.code for c in repo.list_customers()}
    assert "roketsan" not in codes

