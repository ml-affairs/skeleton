"""Noisy ETL scenario used to exercise high-level architecture views."""

from pathlib import Path

from etl.extract.pipeline import CustomerExtractor
from etl.transform.pipeline import CustomerTransformer
from warehouse.data.files import LocalDataCatalog
from warehouse.load.pipeline import WarehouseLoader


def main() -> int:
    """Run the ETL scenario."""
    data_catalog = LocalDataCatalog(Path(__file__).resolve().parent / "warehouse" / "data")
    extractor = CustomerExtractor()
    transformer = CustomerTransformer(data_catalog)
    loader = WarehouseLoader(data_catalog)
    source_count = extractor.source_count()
    rows = extractor.extract()
    transformer.configure({"source_count": source_count})
    customers = transformer.transform(rows)
    loader.prepare()
    return loader.load(customers)


if __name__ == "__main__":
    main()
