import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os


def plot_equity_curve(df, metrics, save_path):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["date"], df["equity"], label="Equity", linewidth=1.5)
    ax.axhline(y=10_000, color="gray", linestyle="--", label="Initial Capital")
    ax.set_title(
        f"Equity Curve — Total Return: {metrics['total_return']}% | "
        f"Sharpe: {metrics['sharpe_ratio']}"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Portfolio Value($)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_drawdown(df, save_path):
    equity = df["equity"]
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(df["date"], drawdown * 100, 0, color="red", alpha=0.4)
    ax.plot(df["date"], drawdown * 100, color="red", linewidth=1)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_title(f"Drawdown — Max: {drawdown.min() * 100:.2f}%")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


def plot_signal_overlay(df, save_path):
    buys = df[df["position"] == 1]
    sells = df[df["position"] == -1]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["date"], df["close"], color="blue", linewidth=1, label="Close")
    ax.scatter(
        buys["date"],
        buys["close"],
        marker="^",
        color="green",
        s=50,
        label="Buy",
        zorder=5,
    )
    ax.scatter(
        sells["date"],
        sells["close"],
        marker="v",
        color="red",
        s=50,
        label="Sell",
        zorder=5,
    )
    ax.set_title("Price with Trade Signals")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price ($)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path


def save_all_charts(results, output_dir="backtest_results"):

    os.makedirs(output_dir, exist_ok=True)

    df = results["daily"]
    metrics = results["metrics"]

    paths = {
        "equity_curve": plot_equity_curve(
            df, metrics, f"{output_dir}/equity_curve.png"
        ),
        "drawdown": plot_drawdown(df, f"{output_dir}/drawdown.png"),
        "signal_overlay": plot_signal_overlay(df, f"{output_dir}/signal_overlay.png"),
    }
    return paths
