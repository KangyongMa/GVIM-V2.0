from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEMO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_ROOT))
from common import prepare_result_dir, resolve_repo_path, write_json  # noqa: E402


DEMO_ID = "spectra_to_dihedral"
DATA_PATH = "research-demos/data/azobenzenes-spectra/IR_Raman_azo.csv"


def main() -> None:
    data_path = resolve_repo_path(DATA_PATH)
    output_dir = prepare_result_dir(DEMO_ID)

    data = pd.read_csv(data_path, header=None)
    if data.shape[1] < 8001:
        raise ValueError(f"Expected at least 8001 columns, found {data.shape[1]}")

    x = data.iloc[:, :8000].astype(float).to_numpy()
    y = data.iloc[:, 8000].astype(float).to_numpy()

    # With only 20 released experimental spectra, leave-one-out validation preserves
    # as much training evidence as possible while keeping every prediction held out.
    model = make_pipeline(
        StandardScaler(),
        PLSRegression(n_components=min(5, len(data) - 1), scale=False),
    )
    pred = cross_val_predict(model, x, y, cv=LeaveOneOut()).reshape(-1)

    mae = float(mean_absolute_error(y, pred))
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    r2 = float(r2_score(y, pred))
    pearson_r = float(np.corrcoef(y, pred)[0, 1])

    pd.DataFrame(
        {
            "sample_id": np.arange(len(y)),
            "observed_dihedral_deg": y,
            "predicted_dihedral_deg": pred,
            "absolute_error_deg": np.abs(y - pred),
        }
    ).to_csv(output_dir / "predictions.csv", index=False)

    write_json(
        output_dir / "metrics.json",
        {
            "demo_id": DEMO_ID,
            "problem": "IR/Raman spectra to azobenzene dihedral angle regression",
            "source_paper": "d5sc08794e",
            "data_path": DATA_PATH,
            "n_samples": int(len(y)),
            "n_features": int(x.shape[1]),
            "validation": "leave-one-out cross-validation",
            "model": "standardized PLSRegression",
            "metrics": {
                "mae_deg": mae,
                "rmse_deg": rmse,
                "r2": r2,
                "pearson_r": pearson_r,
            },
        },
    )

    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    ax.scatter(y, pred, color="#1f6f8b", edgecolor="white", s=55)
    low = min(y.min(), pred.min())
    high = max(y.max(), pred.max())
    ax.plot([low, high], [low, high], "--", color="#d1495b", linewidth=1.5)
    ax.set_xlabel("Observed dihedral angle (deg)")
    ax.set_ylabel("Held-out prediction (deg)")
    ax.set_title("Published IR/Raman data: structure regression")
    fig.tight_layout()
    fig.savefig(output_dir / "observed_vs_predicted.png", dpi=180)
    plt.close(fig)

    print(f"{DEMO_ID}: MAE={mae:.3f} deg, RMSE={rmse:.3f} deg, R2={r2:.3f}, r={pearson_r:.3f}")


if __name__ == "__main__":
    main()
