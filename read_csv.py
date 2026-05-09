import argparse
import os
import pandas as pd
from pandas.errors import ParserError


def read_csv_general(
    file_path: str,
    encoding: str = "utf-8",
    delimiter: str | None = None,
    show_rows: int = 5,
    on_bad_lines: str = "error",
    decimal: str = ",",
    thousands: str | None = None,
    quotechar: str = '"',
    escapechar: str | None = None,
) -> pd.DataFrame:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # sep=None + engine="python" lets pandas try to detect delimiter automatically
    if delimiter == "tab":
        sep_value = "\t"
    else:
        sep_value = delimiter if delimiter is not None else None

    # Try preferred encoding first, then common fallbacks.
    fallback_encodings = [encoding, "utf-8-sig", "latin1", "cp1252"]
    encodings_to_try: list[str] = []
    for enc in fallback_encodings:
        if enc not in encodings_to_try:
            encodings_to_try.append(enc)

    last_decode_error: UnicodeDecodeError | None = None
    for current_encoding in encodings_to_try:
        try:
            df = pd.read_csv(
                file_path,
                sep=sep_value,
                engine="python",
                encoding=current_encoding,
                on_bad_lines=on_bad_lines,
                decimal=decimal,
                thousands=thousands,
                quotechar=quotechar,
                escapechar=escapechar,
            )
            if current_encoding != encoding:
                print(f"\nUsing fallback encoding: {current_encoding}")
            break
        except UnicodeDecodeError as err:
            last_decode_error = err
    else:
        assert last_decode_error is not None
        raise last_decode_error

    print("\nLoaded successfully")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Column names: {list(df.columns)}")
    print("\nPreview:")
    print(df.head(show_rows))

    print("\nMissing values per column:")
    print(df.isna().sum())

    return df


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    original_cols = list(df.columns.astype(str))
    cols = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w€]+", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )

    seen: dict[str, int] = {}
    unique_cols: list[str] = []
    for col in cols:
        if col not in seen:
            seen[col] = 0
            unique_cols.append(col)
        else:
            seen[col] += 1
            unique_cols.append(f"{col}_{seen[col]}")

    df.columns = unique_cols

    changed_columns = [
        (old, new) for old, new in zip(original_cols, unique_cols) if old != new
    ]

    print("\nColumn name cleaning:")
    if changed_columns:
        for old, new in changed_columns:
            print(f"  {old!r} -> {new!r}")
    else:
        print("  No column names needed cleaning.")

    return df


def main():
    parser = argparse.ArgumentParser(description="General CSV reader")
    parser.add_argument("file", help="Path to CSV file")
    parser.add_argument("--encoding", default="utf-8", help="File encoding, e.g. utf-8, latin1")
    parser.add_argument("--delimiter", default=None, help="Delimiter, e.g. comma, semicolon, tab")
    parser.add_argument(
        "--on-bad-lines",
        default="error",
        choices=["error", "warn", "skip"],
        help="How to handle malformed lines",
    )
    parser.add_argument("--decimal", default=",", help="Decimal separator, e.g. . or ,")
    parser.add_argument("--thousands", default=None, help="Thousands separator, e.g. , or .")
    parser.add_argument("--quotechar", default='"', help="Quote character used in CSV")
    parser.add_argument("--escapechar", default=None, help="Escape character used in CSV")
    parser.add_argument("--rows", type=int, default=5, help="Number of preview rows")
    parser.add_argument("--save-clean", default=None, help="Optional path to save cleaned output CSV")
    parser.add_argument("--dry-run", action="store_true", help="Read and clean only; do not write output")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file without confirmation if it already exists",
    )

    args = parser.parse_args()

    try:
        df = read_csv_general(
            file_path=args.file,
            encoding=args.encoding,
            delimiter=args.delimiter,
            show_rows=args.rows,
            on_bad_lines=args.on_bad_lines,
            decimal=args.decimal,
            thousands=args.thousands,
            quotechar=args.quotechar,
            escapechar=args.escapechar,
        )
    except FileNotFoundError:
        print("Error: file not found.")
        print("Tip: check the path and quote it if it contains spaces.")
        raise SystemExit(1)
    except UnicodeDecodeError:
        print("Error: could not decode file with available encodings.")
        print("Tip: try --encoding latin1 or --encoding cp1252.")
        raise SystemExit(1)
    except ParserError as err:
        print(f"Error: CSV parsing failed: {err}")
        print("Tip: verify delimiter/quote settings or try --on-bad-lines skip.")
        raise SystemExit(1)
    except Exception as err:
        print(f"Unexpected error: {err}")
        print("Tip: re-run with explicit --delimiter and --encoding values.")
        raise SystemExit(1)

    # Optional stronger cleanup for consistent, unique column names.
    df = clean_column_names(df)

    if args.dry_run:
        print("\nDry run enabled: no output file written.")
        return

    if args.save_clean:
        if os.path.exists(args.save_clean) and not args.overwrite:
            answer = input(
                f"Output file '{args.save_clean}' exists. Overwrite? [y/N]: "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                print("Skipped writing cleaned CSV.")
                return

        df.to_csv(args.save_clean, index=False, encoding="utf-8")
        print(f"\nCleaned CSV saved to: {args.save_clean}")


if __name__ == "__main__":
    main()