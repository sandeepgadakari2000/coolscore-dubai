"""A dependency-light copy of the trained surrogate for serverless hosting.

scikit-learn (with SciPy) is too heavy for a serverless function, but a fitted
HistGradientBoostingRegressor is just a sum of decision trees. ``export`` flattens
every tree of every model in the artifact into a few NumPy arrays; ``LiteModel``
evaluates them with NumPy alone and returns exactly what ``.predict`` returns
(identity link for the quantile loss: baseline + the sum of the leaf values).

Run ``python -m coolscore.model.lite`` after training to refresh
``data/demo/coolscore_model_lite.npz``; tests check it matches the full model.
"""

from __future__ import annotations

import json
import lzma
import pickle
from pathlib import Path

import numpy as np

from coolscore import config

META_KEYS = ("version", "created", "n_scenarios", "seed", "quantiles", "features", "conformal_log_delta",
             "score_cuts_aed_per_sqft", "score_letters", "monthly_shares", "label")


def lite_path() -> Path:
    return config.path("demo") / "coolscore_model_lite.npz"


def _flatten(model) -> dict[str, np.ndarray]:
    """All trees of one fitted HistGradientBoostingRegressor as flat node arrays."""
    feats, thr, mgl, left, right, leaf, val, cat, bset, roots, bitsets = ([] for _ in range(11))
    offset = bits = 0
    for (tree,) in model._predictors:
        n = tree.nodes
        roots.append(offset)
        feats.append(n["feature_idx"].astype(np.int16))
        thr.append(n["num_threshold"].astype(np.float64))
        mgl.append(n["missing_go_to_left"].astype(bool))
        left.append(n["left"].astype(np.int32) + offset)
        right.append(n["right"].astype(np.int32) + offset)
        leaf.append(n["is_leaf"].astype(bool))
        val.append(n["value"].astype(np.float64))
        cat.append(n["is_categorical"].astype(bool))
        bset.append(n["bitset_idx"].astype(np.int32) + bits)
        cb = np.asarray(tree.raw_left_cat_bitsets, dtype=np.uint32).reshape(-1, 8)
        bitsets.append(cb)
        bits += len(cb)
        offset += len(n)
    # scikit-learn's own preprocessing: categorical columns ordinal-encoded (unknown → NaN) and moved first
    pre, order, cats = getattr(model, "_preprocessor", None), np.arange(model.n_features_in_), []
    if pre is not None:
        masks = {name: np.asarray(cols) for name, _, cols in pre.transformers_ if name != "remainder"}
        enc = pre.named_transformers_["encoder"]
        order = np.concatenate([np.nonzero(masks["encoder"])[0], np.nonzero(masks["numerical"])[0]])
        cats = [np.asarray(c, dtype=np.float64) for c in enc.categories_]
    width = max([len(c) for c in cats], default=0)
    table = np.full((len(cats), width), np.nan)
    for i, c in enumerate(cats):
        table[i, :len(c)] = c
    return {
        "order": order.astype(np.int32), "categories": table,
        "feature": np.concatenate(feats), "threshold": np.concatenate(thr), "missing_left": np.concatenate(mgl),
        "left": np.concatenate(left), "right": np.concatenate(right), "leaf": np.concatenate(leaf),
        "value": np.concatenate(val), "categorical": np.concatenate(cat), "bitset": np.concatenate(bset),
        "roots": np.asarray(roots, dtype=np.int32),
        "bitsets": np.concatenate(bitsets) if bits else np.zeros((0, 8), np.uint32),
        "baseline": np.asarray([float(np.ravel(model._baseline_prediction)[0])]),
    }


class LiteModel:
    """``.predict(X)`` over the flattened trees: NumPy only."""

    def __init__(self, arrays: dict[str, np.ndarray]):
        self.__dict__.update(arrays)
        self.base = float(arrays["baseline"][0])

    def _transform(self, X: np.ndarray) -> np.ndarray:
        """Reorder columns and ordinal-encode the categorical ones, as the fitted model's preprocessor does."""
        Xt = X[:, self.order].copy()
        for i, cats in enumerate(self.categories):
            known = cats[~np.isnan(cats)]
            col = Xt[:, i]
            pos = np.searchsorted(known, col)
            hit = (pos < len(known)) & (known[np.minimum(pos, len(known) - 1)] == col)
            Xt[:, i] = np.where(hit, pos, np.nan)
        return Xt

    def predict(self, X) -> np.ndarray:
        X = self._transform(np.asarray(X, dtype=np.float64))
        n, t = X.shape[0], len(self.roots)
        node = np.tile(self.roots, n)                       # (rows × trees) cursors, row-major
        row = np.repeat(np.arange(n), t)
        active = ~self.leaf[node]
        while active.any():
            idx = np.nonzero(active)[0]
            nd = node[idx]
            x = X[row[idx], self.feature[nd]]
            missing = np.isnan(x)
            go_left = np.where(missing, self.missing_left[nd], x <= self.threshold[nd])
            c = self.categorical[nd] & ~missing
            if c.any():
                ci = np.nonzero(c)[0]
                v = x[ci].astype(np.int64)
                ok = (v >= 0) & (v < 256)
                words = self.bitsets[self.bitset[nd[ci]], np.clip(v // 32, 0, 7)]
                go_left[ci] = ok & (((words >> (v % 32).astype(np.uint32)) & 1) == 1)
            node[idx] = np.where(go_left, self.left[nd], self.right[nd])
            active[idx] = ~self.leaf[node[idx]]
        return self.base + self.value[node].reshape(n, t).sum(axis=1)


def export(art: dict, path: Path | None = None) -> Path:
    """Write the lite artifact (trees as arrays + the artifact's metadata as JSON)."""
    path = path or lite_path()
    arrays: dict[str, np.ndarray] = {}
    for variant, targets in art["models"].items():
        for target, models in targets.items():
            for q, model in models.items():
                for k, a in _flatten(model).items():
                    arrays[f"{variant}|{target}|{q}|{k}"] = a
    meta = {k: art[k] for k in META_KEYS if k in art}
    arrays["__meta__"] = np.frombuffer(json.dumps(meta).encode(), dtype=np.uint8)
    np.savez_compressed(path, **arrays)
    return path


def load(path: Path | None = None) -> dict:
    """The lite artifact in the same shape as the full one: ``art["models"][variant][target][q].predict``."""
    data = np.load(path or lite_path())
    art = json.loads(bytes(data["__meta__"]).decode())
    groups: dict[tuple, dict] = {}
    for key in data.files:
        if key == "__meta__":
            continue
        variant, target, q, name = key.split("|")
        groups.setdefault((variant, target, float(q)), {})[name] = data[key]
    art["models"] = {}
    for (variant, target, q), arrays in groups.items():
        art["models"].setdefault(variant, {}).setdefault(target, {})[q] = LiteModel(arrays)
    return art


if __name__ == "__main__":
    full = pickle.load(lzma.open(config.path("demo") / "coolscore_model.pkl.xz", "rb"))
    out = export(full)
    print(f"wrote {out.relative_to(config.ROOT)} ({out.stat().st_size / 1e6:.1f} MB)")
