"""
Management command to populate the Global National Medicament Catalog from CSV.
Extracts: Code 1, Code 2, Code géo, and Label.
Strictly excludes store-specific prices, quantities, and expiration dates.
"""
import os
import csv
import io
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.catalog.models import MedicamentCatalog

class Command(BaseCommand):
    help = "Populates or updates the National Reference Medicament Catalog from export-stocks CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default="export-stocks-26_08_2026 00_34.csv",
            help="Path to the source CSV file",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing catalog before importing",
        )

    def handle(self, *args, **options):
        csv_path = options["csv"]
        clear_first = options["clear"]

        if not os.path.isabs(csv_path):
            csv_path = os.path.abspath(csv_path)

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"Fichier CSV introuvable : {csv_path}"))
            return

        if clear_first:
            count = MedicamentCatalog.objects.count()
            MedicamentCatalog.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Ancien catalogue vidé ({count} entrées supprimées)."))

        self.stdout.write(self.style.MIGRATE_HEADING(f"Lecture du fichier {csv_path}..."))

        with open(csv_path, mode="rb") as f:
            raw_data = f.read()

        try:
            content = raw_data.decode("utf-8")
        except UnicodeDecodeError:
            content = raw_data.decode("iso-8859-1")

        # Detect delimiter
        sample = content[:2048]
        delimiter = ";" if ";" in sample and sample.count(";") > sample.count(",") else ","

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

        def get_col(row, *candidates):
            for cand in candidates:
                for h_norm, h_orig in headers.items():
                    if cand.lower() == h_norm or cand.lower() in h_norm:
                        return row.get(h_orig, "").strip()
            return ""

        existing_barcodes = set(MedicamentCatalog.objects.values_list("barcode", flat=True))
        records_to_create = []
        seen_barcodes = set(existing_barcodes)
        
        row_count = 0
        gen_counter = 1

        for row in reader:
            row_count += 1
            code_1 = get_col(row, "code 1", "code1", "code_1", "code-barre", "barcode", "cip")
            code_2 = get_col(row, "code 2", "code2", "code_2", "alternatif")
            geo_code = get_col(row, "code géo", "code geo", "code_geo", "rayon", "geo")
            label = get_col(row, "label", "désignation", "designation", "nom", "produit")

            if not label:
                continue

            # Determine primary barcode
            if code_1:
                primary_barcode = code_1
            elif code_2:
                primary_barcode = code_2
            else:
                primary_barcode = f"REF-SN-{gen_counter:05d}"
                gen_counter += 1

            # Handle barcode collisions (e.g. déconditionnement / duplicate items)
            final_barcode = primary_barcode
            suffix = 1
            while final_barcode in seen_barcodes:
                suffix += 1
                final_barcode = f"{primary_barcode}-D{suffix}"

            seen_barcodes.add(final_barcode)

            records_to_create.append(
                MedicamentCatalog(
                    barcode=final_barcode,
                    alternate_barcode=code_2,
                    geo_code=geo_code,
                    name=label,
                    default_category="",
                    dci="",
                    form_dosage="",
                    is_active=True,
                )
            )

        self.stdout.write(self.style.MIGRATE_HEADING(f"Insertion en base de {len(records_to_create)} médicaments de référence..."))

        with transaction.atomic():
            # Batch create by chunks of 1000
            chunk_size = 1000
            for i in range(0, len(records_to_create), chunk_size):
                chunk = records_to_create[i:i + chunk_size]
                MedicamentCatalog.objects.bulk_create(chunk, ignore_conflicts=True)

        total_in_db = MedicamentCatalog.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Succès ! {len(records_to_create)} médicaments traités depuis {row_count} lignes CSV. Total catalogue national : {total_in_db} références."
            )
        )
