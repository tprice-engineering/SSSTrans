"""Read scalar transient measurements and summarize them in seconds and kelvin."""

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from statistics import mean

TIME = {"time_s": 1.0, "time_ms": 0.001}
TEMPERATURE = {"temperature_K": 0.0, "temperature_C": 273.15}


@dataclass(frozen=True)
class Sample:
    time_s: float
    temperature_K: float


def read_history(path: Path) -> list[Sample]:
    """Read one time column and one temperature column with explicit units."""
    samples = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        table = csv.reader(stream)
        columns = next(table, [])
        time = [column for column in columns if column in TIME]
        temp = [column for column in columns if column in TEMPERATURE]
        if len(columns) != 2 or len(time) != 1 or len(temp) != 1:
            raise ValueError("expected one time_s or time_ms and one temperature_K or temperature_C column")
        time_index = columns.index(time[0])
        temp_index = columns.index(temp[0])
        for line, row in enumerate(table, start=2):
            try:
                if len(row) != len(columns):
                    raise ValueError
                seconds = float(row[time_index]) * TIME[time[0]]
                kelvin = float(row[temp_index]) + TEMPERATURE[temp[0]]
            except ValueError as error:
                raise ValueError(f"line {line}: expected two numeric fields") from error
            if not (isfinite(seconds) and isfinite(kelvin) and kelvin >= 0):
                raise ValueError(f"line {line}: expected finite time and nonnegative absolute temperature")
            if samples and seconds <= samples[-1].time_s:
                raise ValueError(f"line {line}: time must increase strictly")
            samples.append(Sample(seconds, kelvin))
    if len(samples) < 2:
        raise ValueError("at least two samples are required")
    return samples


def summarize(samples: list[Sample]) -> dict:
    first, last = samples[0], samples[-1]
    peak = max(samples, key=lambda sample: sample.temperature_K)
    duration = last.time_s - first.time_s
    area = sum(
        mean((a.temperature_K, b.temperature_K)) * (b.time_s - a.time_s)
        for a, b in zip(samples, samples[1:])
    )
    return {
        "sample_count": len(samples),
        "duration_s": duration,
        "initial_temperature_K": first.temperature_K,
        "final_temperature_K": last.temperature_K,
        "peak": asdict(peak),
        "time_weighted_mean_temperature_K": area / duration,
    }


def plot_history(samples: list[Sample], destination: Path, *, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    ax.plot([s.time_s for s in samples], [s.temperature_K for s in samples],
            color="#156b85", linewidth=2)
    ax.set(title=title, xlabel="Time (s)", ylabel="Temperature (K)")
    ax.grid(alpha=0.25)
    fig.savefig(destination, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("build"))
    parser.add_argument("--title", default="Transient temperature history")
    args = parser.parse_args()
    try:
        samples = read_history(args.csv)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    result = json.dumps(summarize(samples), indent=2) + "\n"
    (args.out_dir / "summary.json").write_text(result, encoding="utf-8")
    plot_history(samples, args.out_dir / "history.png", title=args.title)
    print(result, end="")


if __name__ == "__main__":
    main()
