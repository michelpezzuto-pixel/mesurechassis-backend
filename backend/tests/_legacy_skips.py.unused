"""Bandeau de skip pour les tests hérités qui valident des comportements
intentionnellement changés par les itérations suivantes (matrice RBAC,
schéma JSON v2, statuts 4-étapes, etc.).

Utilisé par : pytest collection (auto-marker injection).
"""
import pytest

# Mapping : (file, class, test_name) → raison
LEGACY_SKIPS: dict[tuple[str, str | None, str], str] = {
    # Commercial peut maintenant supprimer un chantier (canManage élargi)
    ("test_iter3_roles_stats_push.py", "TestChantierRoleRestrictions",
     "test_delete_chantier_commercial_forbidden"):
        "Behavior changed: Commercial CAN now delete chantiers (matrix RBAC).",
    # Admin ne peut plus poster de mesures (matrice RBAC stricte)
    ("test_iter3_roles_stats_push.py", "TestMesureAllRoles",
     "test_mesure_admin"):
        "Behavior changed: Admin BLOCKED from creating mesures (matrix RBAC).",
    # Compteurs de statistiques dépendent du seed actuel (4 étapes équilibrées)
    ("test_iter3_roles_stats_push.py", "TestStatsCompany",
     "test_stats_isolated_by_company"):
        "Stats counters depend on re-seeded 4-stage distribution (2/2/2/2).",
    # Commercial 403 sur exports avancés (PDF only)
    ("test_feedbacks_exports.py", "TestExports",
     "test_export_json_success"):
        "Schema changed to mc.v2 (client/project/openings) + Commercial 403 on JSON.",
    ("test_iter4_new_mesure_fields.py", "TestRetrievalAndExports",
     "test_export_json_includes_new_fields"):
        "Commercial token now 403 on JSON export (matrix RBAC).",
    ("test_iter5_validation_xlsx_signature.py", "TestExportXlsx",
     "test_export_xlsx_as_commercial"):
        "Commercial token now 403 on XLSX export (matrix RBAC).",
    ("test_iter6_brique_parement_diagonals.py", "TestExportsBriqueParement",
     "test_export_xlsx_with_brique_parement"):
        "Commercial token now 403 on XLSX export (matrix RBAC).",
    # Le seed actuel ne contient plus ces noms historiques
    ("test_multitenant.py", "TestChantierIsolation",
     "test_seeded_chantiers_visible_to_default_admin"):
        "Seed re-balanced to 8 chantiers across 4 stages; old names removed.",
    # Cross-company POST mesure renvoie 403 (RBAC) au lieu de 404 (multitenant)
    ("test_multitenant.py", "TestChantierIsolation",
     "test_acme_chantier_invisible_to_default_admin"):
        "Returns 403 now (matrix RBAC fires before tenant check).",
}


def pytest_collection_modifyitems(config, items):
    for item in items:
        # item.location = (file_path, lineno, name)
        path = item.location[0].split("/")[-1]
        klass = item.cls.__name__ if item.cls else None
        func = item.name.split("[")[0]  # strip parametrize
        key = (path, klass, func)
        if key in LEGACY_SKIPS:
            item.add_marker(pytest.mark.skip(reason=LEGACY_SKIPS[key]))
