"""
train_ondevice_model.py
-----------------------
Synthetic dataset generator and ML model trainer for Hyderabad Transit On-Device AI.

This script:
1. Generates 300+ synthetic trip candidate scenarios with realistic time, fare, transfers, and context.
2. Trains a scikit-learn DecisionTreeClassifier model to predict route preference scores.
3. Exports the model to pickle format (ondevice_route_ranker.pkl) for 100% local, on-device edge AI inference
   via scikit-learn (satisfying hackathon on-device AI requirements).
"""

import numpy as np
import pickle
from sklearn.tree import DecisionTreeClassifier

try:
    import skl2onnx
    from skl2onnx.common.data_types import FloatTensorType
    HAS_SKL2ONNX = True
except ImportError:
    HAS_SKL2ONNX = False


def generate_synthetic_data(num_samples: int = 300):
    """
    Generates synthetic training dataset of (features, target_score) pairs.
    Features vector (6 float inputs):
      [norm_time, norm_fare, norm_transfers, is_peak, is_off_peak, is_budget]
    """
    np.random.seed(42)

    X = []
    y = []

    contexts = ["peak", "off_peak", "budget"]

    for _ in range(num_samples):
        # Generate 3 candidates for a trip scenario
        times = np.random.uniform(10.0, 50.0, size=3)
        fares = np.random.uniform(10.0, 90.0, size=3)
        transfers = np.random.choice([0, 1, 2, 3], size=3, p=[0.3, 0.4, 0.2, 0.1])

        min_t, max_t = np.min(times), np.max(times)
        min_f, max_f = np.min(fares), np.max(fares)
        min_n, max_n = np.min(transfers), np.max(transfers)

        ctx = np.random.choice(contexts)
        is_peak = 1.0 if ctx == "peak" else 0.0
        is_off_peak = 1.0 if ctx == "off_peak" else 0.0
        is_budget = 1.0 if ctx == "budget" else 0.0

        if ctx == "peak":
            w_t, w_f, w_n = 0.20, 0.10, 0.70
        elif ctx == "budget":
            w_t, w_f, w_n = 0.15, 0.70, 0.15
        else:
            w_t, w_f, w_n = 0.70, 0.15, 0.15

        for i in range(3):
            t_norm = (times[i] - min_t) / (max_t - min_t) if max_t > min_t else 0.0
            f_norm = (fares[i] - min_f) / (max_f - min_f) if max_f > min_f else 0.0
            n_norm = (transfers[i] - min_n) / (max_n - min_n) if max_n > min_n else 0.0

            # Disutility penalty (0.0 = best, 1.0 = worst)
            disutility = (w_t * t_norm) + (w_f * f_norm) + (w_n * n_norm)
            
            # Map into discrete preference tier class (0: Low, 1: Medium, 2: High, 3: Preferred Top Choice)
            if disutility <= 0.15:
                label = 3
            elif disutility <= 0.35:
                label = 2
            elif disutility <= 0.60:
                label = 1
            else:
                label = 0

            feature_vector = [t_norm, f_norm, n_norm, is_peak, is_off_peak, is_budget]
            X.append(feature_vector)
            y.append(label)

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


def train_and_export():
    print("Generating 300+ synthetic route recommendation training samples...")
    X, y = generate_synthetic_data(num_samples=300)

    print(f"Training DecisionTreeClassifier model on {len(X)} feature samples...")
    clf = DecisionTreeClassifier(max_depth=5, random_state=42)
    clf.fit(X, y)

    # 1. Save as Pickle model file
    pkl_filename = "ondevice_route_ranker.pkl"
    with open(pkl_filename, "wb") as f:
        pickle.dump(clf, f)
    print(f"[SUCCESS] Exported Pickle model to '{pkl_filename}' (Scikit-Learn Pickle Format)")

    # 2. Optional export to ONNX format if skl2onnx is available
    onnx_filename = "ondevice_route_ranker.onnx"
    if HAS_SKL2ONNX:
        try:
            initial_type = [('float_input', FloatTensorType([None, 6]))]
            onnx_model = skl2onnx.convert_sklearn(clf, initial_types=initial_type)
            with open(onnx_filename, "wb") as f:
                f.write(onnx_model.SerializeToString())
            print(f"[SUCCESS] Exported ONNX model to '{onnx_filename}'")
        except Exception as e:
            print(f"[INFO] Skipping ONNX export: {e}")

    return pkl_filename


if __name__ == "__main__":
    train_and_export()

