#!/usr/bin/env python3
"""Generate cryptic legacy sanctuary telemetry & inventory CSVs for PetVerse Analytics.

Designed to run cleanly with `uv` (Python 3.14+ or fallback standard Python 3):
  uv run --python 3.14 scripts/generate_telemetry.py
  uv run scripts/generate_telemetry.py

Reads configurable pipe-delimited seed files from `--seed-dir`:
  - pet_profiles_seed.txt
  - supply_skus_seed.txt

Outputs clean CSV files into `--output-dir`:
  - pv_ops_tlm_v2.csv  (90-day daily resident telemetry + 15 hardware calibration rows)
  - pv_snct_inv_88.csv (sanctuary feed & cold-storage SKU inventory)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PetSeedProfile:
    ent_fk: int
    pet_name: str
    species: str
    base_nutr_g: float
    daily_trend_g: float
    weekend_bump_g: float
    base_act_stp: int
    base_slp_min: int
    base_care_cents: int


@dataclass(frozen=True)
class SupplySkuSeed:
    sku_cd: str
    sp_cat_cd: str
    itm_lbl: str
    cur_stk_kg: float
    reord_thr_kg: float
    unit_cost_c: int
    cold_flg: str


def load_pet_profiles(seed_file: Path) -> list[PetSeedProfile]:
    profiles: list[PetSeedProfile] = []
    with seed_file.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 9:
                raise ValueError(
                    f"Expected 9 pipe-delimited fields in {seed_file}, got {len(parts)}: {line}"
                )
            profiles.append(
                PetSeedProfile(
                    ent_fk=int(parts[0]),
                    pet_name=parts[1],
                    species=parts[2],
                    base_nutr_g=float(parts[3]),
                    daily_trend_g=float(parts[4]),
                    weekend_bump_g=float(parts[5]),
                    base_act_stp=int(parts[6]),
                    base_slp_min=int(parts[7]),
                    base_care_cents=int(parts[8]),
                )
            )
    if not profiles:
        raise ValueError(f"No pet profiles loaded from {seed_file}")
    return profiles


def load_supply_skus(seed_file: Path) -> list[SupplySkuSeed]:
    skus: list[SupplySkuSeed] = []
    with seed_file.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 7:
                raise ValueError(
                    f"Expected 7 pipe-delimited fields in {seed_file}, got {len(parts)}: {line}"
                )
            skus.append(
                SupplySkuSeed(
                    sku_cd=parts[0],
                    sp_cat_cd=parts[1],
                    itm_lbl=parts[2],
                    cur_stk_kg=float(parts[3]),
                    reord_thr_kg=float(parts[4]),
                    unit_cost_c=int(parts[5]),
                    cold_flg=parts[6],
                )
            )
    if not skus:
        raise ValueError(f"No supply SKUs loaded from {seed_file}")
    return skus


def generate_telemetry_csv(
    profiles: list[PetSeedProfile],
    output_csv: Path,
    start_date: dt.date,
    days: int,
    seed: int,
    calibration_count: int = 15,
) -> tuple[int, int]:
    rng = random.Random(seed)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Pick evenly spaced dates across the window for mainframe bench calibration spikes (ent_fk=99, st_cd=9)
    cal_count = min(calibration_count, days)
    step = max(1, days // cal_count)
    calibration_day_indices = {min(days - 1, i * step) for i in range(cal_count)}
    while len(calibration_day_indices) < cal_count:
        for candidate in range(days):
            if candidate not in calibration_day_indices:
                calibration_day_indices.add(candidate)
                if len(calibration_day_indices) == cal_count:
                    break

    seq_num = 100001
    active_rows = 0
    cal_rows = 0

    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            [
                "rec_seq_id",
                "ent_fk",
                "ts_dt",
                "nutr_g_qty",
                "act_k_stp",
                "slp_m_dur",
                "care_c_usd",
                "st_cd",
            ]
        )

        for day_idx in range(days):
            current_date = start_date + dt.timedelta(days=day_idx)
            is_weekend = current_date.weekday() in (5, 6)

            for p in profiles:
                # Smooth weekly harmonic + weekend enrichment treat bump + bounded Gaussian noise
                harmonic = math.sin(2.0 * math.pi * (day_idx + p.ent_fk) / 7.0)
                weekend_boost = p.weekend_bump_g if is_weekend else 0.0
                noise_g = rng.gauss(0.0, max(0.35, p.base_nutr_g * 0.025))

                nutr_g = (
                    p.base_nutr_g
                    + (p.daily_trend_g * day_idx)
                    + weekend_boost
                    + (0.35 * p.weekend_bump_g * harmonic)
                    + noise_g
                )
                nutr_g = round(max(4.0, nutr_g), 1)

                # Activity steps/wheel revolutions correlate with weekend play + subtle harmonic
                act_multiplier = 1.08 if is_weekend else 1.0
                act_noise = rng.gauss(0.0, p.base_act_stp * 0.055)
                act_stp = int(
                    round(
                        max(
                            80.0,
                            p.base_act_stp * act_multiplier
                            + (p.base_act_stp * 0.03 * harmonic)
                            + act_noise,
                        )
                    )
                )

                # Sleep minutes inversely adjust slightly on high-activity days
                slp_delta = -18 if is_weekend else 0
                slp_min = int(
                    round(
                        min(
                            1360.0,
                            max(
                                360.0,
                                p.base_slp_min + slp_delta + rng.gauss(0.0, 16.0),
                            ),
                        )
                    )
                )

                # Vet checkup observation day (`st_cd = 2`) roughly once per month per resident
                is_vet_day = ((day_idx + (p.ent_fk * 3)) % 28) == 14
                st_cd = 2 if is_vet_day else 1

                # Daily care cost in US cents scales with feed ratio + vet observation surcharge
                feed_ratio = nutr_g / p.base_nutr_g
                vet_surcharge_cents = 650 if is_vet_day else 0
                care_cents = int(
                    round(
                        max(
                            50.0,
                            (p.base_care_cents * (0.45 + 0.55 * feed_ratio))
                            + vet_surcharge_cents
                            + rng.gauss(0.0, 12.0),
                        )
                    )
                )

                writer.writerow(
                    [
                        f"TLM-{seq_num:06d}",
                        p.ent_fk,
                        current_date.isoformat(),
                        f"{nutr_g:.1f}",
                        act_stp,
                        slp_min,
                        care_cents,
                        st_cd,
                    ]
                )
                seq_num += 1
                active_rows += 1

            # Inject non-animal AS/400 load-cell calibration row (`ent_fk = 99`, `st_cd = 9`)
            if day_idx in calibration_day_indices:
                writer.writerow(
                    [
                        f"TLM-{seq_num:06d}",
                        99,
                        current_date.isoformat(),
                        "9999.0",
                        99999,
                        0,
                        99900,
                        9,
                    ]
                )
                seq_num += 1
                cal_rows += 1

    return active_rows, cal_rows


def generate_inventory_csv(skus: list[SupplySkuSeed], output_csv: Path) -> int:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(
            [
                "sku_cd",
                "sp_cat_cd",
                "itm_lbl",
                "cur_stk_kg",
                "reord_thr_kg",
                "unit_cost_c",
                "cold_flg",
            ]
        )
        for s in skus:
            writer.writerow(
                [
                    s.sku_cd,
                    s.sp_cat_cd,
                    s.itm_lbl,
                    f"{s.cur_stk_kg:.1f}",
                    f"{s.reord_thr_kg:.1f}",
                    s.unit_cost_c,
                    s.cold_flg,
                ]
            )
    return len(skus)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    parser = argparse.ArgumentParser(
        description="Generate PetVerse Sanctuary legacy telemetry and supply inventory CSVs."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Number of continuous daily telemetry observations per resident (default: 90).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2026-08-01",
        help="UTC start date in YYYY-MM-DD format (default: 2026-08-01).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed (default: 42).",
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=script_dir,
        help="Directory containing pet_profiles_seed.txt and supply_skus_seed.txt.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=repo_root / "data",
        help="Output directory for generated CSV files (default: ./data).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.days < 14:
        raise ValueError("--days must be at least 14 for time-series forecasting.")

    start_date = dt.date.fromisoformat(args.start_date)
    end_date = start_date + dt.timedelta(days=args.days - 1)

    profiles_path = args.seed_dir / "pet_profiles_seed.txt"
    skus_path = args.seed_dir / "supply_skus_seed.txt"

    profiles = load_pet_profiles(profiles_path)
    skus = load_supply_skus(skus_path)

    tlm_csv = args.output_dir / "pv_ops_tlm_v2.csv"
    inv_csv = args.output_dir / "pv_snct_inv_88.csv"

    active_rows, cal_rows = generate_telemetry_csv(
        profiles=profiles,
        output_csv=tlm_csv,
        start_date=start_date,
        days=args.days,
        seed=args.seed,
    )
    sku_rows = generate_inventory_csv(skus=skus, output_csv=inv_csv)

    print(
        f"Generated {tlm_csv} ({active_rows + cal_rows} total rows: "
        f"{active_rows} active resident rows [{start_date}..{end_date}] + "
        f"{cal_rows} st_cd=9 calibration rows)."
    )
    print(f"Generated {inv_csv} ({sku_rows} supply SKU rows).")


if __name__ == "__main__":
    main()
