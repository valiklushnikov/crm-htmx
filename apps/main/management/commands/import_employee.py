import os

from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd
from utils.csv_to_objects import create_employee_from_row, clean_and_parse_row




class Command(BaseCommand):
    help = "Importing csv files from data folder"

    def handle(self, *args, **options):
        path = os.path.join(settings.BASE_DIR, "utils", "data1.csv")
        df = pd.read_csv(
            path,
            delimiter=",",
            encoding="utf-8",
            dtype=str,
        )
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

        df["Призвіще"] = df["Призвіще"].str.strip()
        df["Призвіще"] = df["Призвіще"].str.replace(r"^\d+\.\s*", "", regex=True)

        instances = 0
        for raw_row in df.to_dict(orient="records"):
            row = clean_and_parse_row(raw_row)
            create_employee_from_row(row)
            instances += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Created: {instances} instances"
            )
        )

