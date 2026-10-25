#!/usr/bin/env python3
"""
GPU check for the Soccer Deep-Learning training.

Tells you whether TensorFlow can use your GPU, and benchmarks CPU vs GPU on the
*actual* training model (78 -> 256 -> 128 -> 3x softmax + value) so you can see
the real speed difference.

    python scripts/gpu_check.py
    python scripts/gpu_check.py --iters 100

If no GPU is detected, the output points you at docs/HowTo_GPU_Setup.MD with the
right install steps for your card.
"""
import argparse
import glob
import os
import subprocess
import sys
import time

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
RELEASE = os.path.dirname(HERE)
sys.path.insert(0, RELEASE)  # so we can reuse the real model builder

VENDOR_ID = {"0x10de": "NVIDIA", "0x1002": "AMD", "0x1022": "AMD",
             "0x8086": "Intel", "0x106b": "Apple"}


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout or ""
    except Exception:
        return ""


def _vendors_from_text(text):
    low = text.lower()
    found = set()
    if "nvidia" in low:
        found.add("NVIDIA")
    if "amd" in low or "radeon" in low or "advanced micro" in low or "[amd/ati]" in low:
        found.add("AMD")
    if "intel" in low:
        found.add("Intel")
    return found


def detect_vendors():
    """Best-effort list of GPU vendors present (hardware level). Cross-platform."""
    vendors = set()
    try:
        if sys.platform == "darwin":                       # macOS
            vendors.add("Apple")                           # Apple-silicon GPU
            vendors |= _vendors_from_text(_run(["system_profiler", "SPDisplaysDataType"]))
        elif sys.platform.startswith("win"):               # Windows
            out = _run(["powershell", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_VideoController | "
                        "Select-Object -ExpandProperty Name"])
            if not out.strip():                            # fallback to (deprecated) wmic
                out = _run(["wmic", "path", "win32_videocontroller", "get", "name"])
            vendors |= _vendors_from_text(out)
        else:                                              # Linux / other Unix
            # PCI vendor id from /sys is authoritative and needs no external tools
            for vfile in glob.glob("/sys/class/drm/card*/device/vendor"):
                try:
                    vendors.add(VENDOR_ID.get(open(vfile).read().strip().lower()))
                except Exception:
                    pass
            vendors.discard(None)
            if not vendors:                                # fallback if /sys absent
                vendors |= _vendors_from_text(_run(["lspci"]))
    except Exception:
        pass
    vendors.discard(None)
    return vendors


def make_model(tf):
    """Use the real soccer model if importable; else an identical-shape stand-in."""
    try:
        from game.keras_core import build_model
        return build_model()
    except Exception:
        inp = tf.keras.Input(shape=(78,))
        x = tf.keras.layers.Dense(256, activation="relu")(inp)
        x = tf.keras.layers.Dense(128, activation="relu")(x)
        heads = [tf.keras.layers.Dense(3, activation="softmax")(x) for _ in range(3)]
        value = tf.keras.layers.Dense(1)(x)
        return tf.keras.Model(inp, heads + [value])


def benchmark(tf, device, iters):
    """One PPO-like forward+backward train step, timed. Returns steps/s or None."""
    try:
        with tf.device(device):
            model = make_model(tf)
            opt = tf.keras.optimizers.Adam(3e-4)
            x = tf.random.uniform((64, 78))

            @tf.function
            def step(x):
                with tf.GradientTape() as tape:
                    outs = model(x, training=True)   # [fb, lr, turn, value]
                    loss = (tf.add_n([tf.reduce_mean(o) for o in outs[:-1]])
                            + tf.reduce_mean(tf.square(outs[-1])))
                grads = tape.gradient(loss, model.trainable_variables)
                opt.apply_gradients(zip(grads, model.trainable_variables))
                return loss

            for _ in range(5):       # warm up
                step(x)
            t0 = time.time()
            for _ in range(iters):
                step(x)
            return iters / (time.time() - t0)
    except Exception as e:
        print(f"    ({device} benchmark failed: {type(e).__name__}: {str(e)[:70]})")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=50)
    args = ap.parse_args()

    print("=" * 60)
    print("GPU CHECK — Soccer Deep-Learning training")
    print("=" * 60)

    try:
        import tensorflow as tf
    except Exception as e:
        print(f"TensorFlow not installed: {e}")
        print("Install it first (see docs/HowTo_GPU_Setup.MD).")
        return

    gpus = list(tf.config.list_physical_devices("GPU"))
    try:
        gpus += list(tf.config.list_physical_devices("XPU"))  # Intel
    except Exception:
        pass

    print(f"TensorFlow {tf.__version__}")
    print(f"GPU(s) visible to TensorFlow: {[d.name for d in gpus] or 'NONE'}")

    print(f"\nBenchmarking (model = real training net, {args.iters} steps each)...")
    cpu_sps = benchmark(tf, "/CPU:0", args.iters)
    if cpu_sps:
        print(f"    CPU : {cpu_sps:8.0f} steps/s")

    if gpus:
        gdev = gpus[0].name.replace("/physical_device:", "/")  # -> /GPU:0 or /XPU:0
        gpu_sps = benchmark(tf, gdev, args.iters)
        if gpu_sps and cpu_sps:
            print(f"    GPU : {gpu_sps:8.0f} steps/s  ({gpu_sps / cpu_sps:.1f}x vs CPU)")
        print("\n==> GPU is ENABLED. Training will use it automatically.")
    else:
        print("\n==> No GPU is visible to TensorFlow — training will run on CPU.")
        vendors = detect_vendors()
        if vendors:
            print(f"    Detected GPU hardware: {', '.join(sorted(vendors))}")
        print("    To enable it, follow docs/HowTo_GPU_Setup.MD for your card:")
        if "NVIDIA" in vendors:
            print("      NVIDIA : pip install 'tensorflow[and-cuda]'   (Linux)")
        if "AMD" in vendors:
            print("      AMD    : pip install tensorflow-rocm          (Linux + ROCm)")
        if "Intel" in vendors:
            print("      Intel  : pip install 'intel-extension-for-tensorflow[xpu]'")
        if "Apple" in vendors:
            print("      Apple  : pip install tensorflow-metal")
        print("    (Harmless cuInit/CUDA noise? silence with TF_CPP_MIN_LOG_LEVEL=3)")

    print("=" * 60)


if __name__ == "__main__":
    main()
