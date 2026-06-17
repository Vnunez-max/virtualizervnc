#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODULES = [
    "v3_4_2/module_b1_v3_4_2_residual_evidence_stratifier.py",
    "c1/module_c1_0_residual_evidence_geometry_hypothesis_validator.py",
    "c1/module_c1_1_collective_residual_evidence_hypothesis_validator.py",
    "u1/module_u1_1_subobject_clean_grid_geometry_purity_gate.py",
    "u1/module_u1_1_cal_geometric_hysteresis_calibrator.py",
    "l1/module_l1_0_observed_support_domain_stratifier.py",
    "l1/module_l1_1_observed_support_domain_calibration_layer.py",
    "l1/module_l1_2_deferred_domain_subsupport_resolver.py",
    "l1/module_l1_2_cal_deferred_line_like_fragment_calibrator.py",
    "g1/module_g1_0_deferred_line_family_resolver.py",
    "g1/module_g1_0_cal_v1_apply_trainable_calibrator.py",
    "unit/module_unit_full_model_v1_apply.py",
    "d1/module_d1_0_deferred_simple_linearity_auditor.py",
    "d1/module_d1_1_deferred_linear_role_classifier.py",
    "x3/module_x3_0_trainable_geometric_evidence_unit.py",
    "module_x2_0_geometric_evidence_fusion_single_script.py",
]

EXPECTED_MODEL_FILES = [
    "model_config.json",
    "feature_scaler.json",
    "coefficients.csv",
]

FORBIDDEN_PARTS = {
    "samples",
    "__pycache__",
}

FORBIDDEN_FILENAMES = {
    ".DS_Store",
    "dataset_manifest.json",
    "dataset_audit.json",
    "summary.json",
    "contract_audit.json",
}

FORBIDDEN_CURRENT_STRINGS = {
    "module_g1_0_cal_v1_apply_trainable_calibrator_to_test3_3_unit.py",
    "module_unit_full_model_v1_apply_to_test3_3.py",
    "unit_full_model_v1_applied_test3_2_test3_3",
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def main() -> int:
    print(f"Verificando paquete VM: {ROOT}")

    try:
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception as exc:
        return fail(f"dependencias base no disponibles: {exc}")
    print("PASS dependencias base: numpy, Pillow")

    missing_modules = [name for name in EXPECTED_MODULES if not (ROOT / "modules" / name).exists()]
    if missing_modules:
        return fail(f"faltan modulos: {missing_modules}")

    for name in EXPECTED_MODULES:
        path = ROOT / "modules" / name
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    print(f"PASS compilacion modules: {len(EXPECTED_MODULES)}")

    stale_refs: list[str] = []
    current_docs = [
        ROOT / "README.md",
        ROOT / "docs" / "README_VM_RUNTIME.md",
        ROOT / "manifests" / "MODULE_REGISTRY.md",
        ROOT / "manifests" / "TRAINABLE_MODULES.md",
    ]
    for path in current_docs:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_CURRENT_STRINGS:
            if needle in text:
                stale_refs.append(f"{path.relative_to(ROOT)}: {needle}")
    if stale_refs:
        return fail(f"referencias actuales obsoletas: {stale_refs}")
    print("PASS referencias actuales sin entrypoints test-especificos obsoletos")

    manifest_path = ROOT / "manifests" / "MANIFEST_VM_RUNTIME.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        includes = manifest.get("includes", {})
        module_count = len(list((ROOT / "modules").rglob("*.py")))
        contract_count = len(list((ROOT / "contracts").rglob("*.md")))
        doc_count = len(list((ROOT / "docs").rglob("*.md")))
        expected_counts = {
            "modules": module_count,
            "contracts": contract_count,
            "docs": doc_count,
        }
        actual_counts = {
            "modules": includes.get("modules"),
            "contracts": includes.get("contracts"),
            "docs": includes.get("docs"),
        }
        if actual_counts != expected_counts:
            return fail(f"MANIFEST_VM_RUNTIME counts obsoletos: {actual_counts} != {expected_counts}")
        print("PASS MANIFEST_VM_RUNTIME counts alineados")

    model_dir = ROOT / "models" / "g1_0_cal_v1_deferred_family"
    missing_model_files = [name for name in EXPECTED_MODEL_FILES if not (model_dir / name).exists()]
    if missing_model_files:
        return fail(f"faltan archivos de modelo G1.0-CAL V1: {missing_model_files}")

    config = json.loads((model_dir / "model_config.json").read_text(encoding="utf-8"))
    scaler = json.loads((model_dir / "feature_scaler.json").read_text(encoding="utf-8"))
    with (model_dir / "coefficients.csv").open("r", encoding="utf-8", newline="") as handle:
        coeff_rows = list(csv.DictReader(handle))

    if not config.get("feature_names") or not config.get("targets"):
        return fail("model_config.json no contiene feature_names/targets")
    if not scaler.get("mean") or not scaler.get("std"):
        return fail("feature_scaler.json no contiene mean/std")
    if not coeff_rows:
        return fail("coefficients.csv esta vacio")
    print("PASS modelo G1.0-CAL V1 presente y legible")

    forbidden_hits: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        parts = set(rel.parts)
        if parts & FORBIDDEN_PARTS:
            forbidden_hits.append(str(rel))
        if path.name in FORBIDDEN_FILENAMES:
            forbidden_hits.append(str(rel))
    if forbidden_hits:
        return fail(f"paquete contiene datasets/resultados/cache excluidos: {forbidden_hits[:12]}")
    print("PASS limpieza: sin datasets, samples, caches ni resultados historicos")

    print("PASS paquete VM funcional")
    return 0


if __name__ == "__main__":
    sys.exit(main())
