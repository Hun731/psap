"""Console script for psap."""
import argparse
import sys
from pathlib import Path
from psap.util import export_matrix
from psap.classifier import train_model, psap_predict, eval_model


def main():
    """Console script for psap."""
    parser = argparse.ArgumentParser()
    # parser.add_argument("-v", "--version", action="version", version=psap.__version__)
    subparsers = parser.add_subparsers(dest="command")
    annotate = subparsers.add_parser(
        "annotate",
        help="adds biochemical features to a set of protein sequences in fasta format and writes it to a serialized data frame",
    )
    train = subparsers.add_parser("train", help="train psap model")
    pp = subparsers.add_parser("pp", help="predict classes")
    cv = subparsers.add_parser("cv", help="evaluate model using cross validation")
    annotate.add_argument(
        "-f",
        "--fasta",
        default=None,
        required=True,
        help="Path to peptide fasta file",
    )
    annotate.add_argument(
        "-o",
        "--out",
        default="~",
        required=False,
        help="Output directory for annotated and serialized (pkl) data frame",
    )
    train.add_argument(
        "-df",
        "--data_frame",
        default=None,
        required=True,
        help="Path to annotated and serialized data frame (output from annotate command)",
    )
    train.add_argument(
        "-out",
        "--out_dir",
        default=None,
        required=True,
        help="Output directory for trained and serialized RandomForest classifier",
    )
    pp.add_argument(
        "-df",
        "--data_frame",
        default=None,
        required=True,
        help="Path to annotated and serialized data frame (output from annotate)",
    )
    pp.add_argument(
        "-m",
        "--model",
        default=None,
        required=True,
        help="Path to serialized RandomForest model",
    )
    pp.add_argument(
        "-o",
        "--out_dir",
        default=None,
        required=True,
        help="Output directory for prediction results",
    )
    cv.add_argument(
        "-df",
        "--data_frame",
        default=None,
        required=True,
        help="Path to annotated and serialized data frame (output from annotate command)",
    )
    cv.add_argument(
        "-out",
        "--out_dir",
        default=None,
        required=True,
        help="Output directory for prediction results",
    )
    args = parser.parse_args()
    # Pickle training-set
    if args.command == "annotate":
        export_matrix(
            name=Path(args.db_fasta).stem, fasta_path=args.db_fasta, out_path=args.out
        )
    if args.command == "train":
        train_model(
            training_data=args.data_frame,
            prefix=Path(args.out_dir).stem,
            out_dir=args.out_dir,
        )
    elif args.command == "pp":
        psap_predict(
            test_data=args.data_frame,
            model=args.model,
            prefix=Path(args.out_dir).stem,
            out_dir=args.out_dir,
        )
    elif args.command == "cv":
        eval_model(
            path=args.data_frame,
            prefix=Path(args.out_dir).stem,
            out_dir=args.out_dir,
        )
    else:
        print("Incorrect subparser selected")


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
