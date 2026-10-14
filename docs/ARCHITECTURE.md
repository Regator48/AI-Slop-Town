# Architecture and limitations

The engine advances one simulated day. State is intentionally compact and scalar in this first implementation so it runs on a CPU-only host. The next scaling step is to replace household and firm scalar aggregates with contiguous arrays (NumPy/CuPy/PyTorch) and partition household/labor work from firms/banks across devices.

## Flow

1. Policy and shocks update rates and expectations.
2. Labor and production determine output and wages.
3. Households generate demand for daily needs.
4. Banks accrue interest, losses, reserves, and capital.
5. Government collects taxes, pays benefits, and issues debt.
6. Gold and equities respond to rates, inflation, earnings, unemployment, stress, and seeded noise.
7. Monthly metrics are checkpointed and invariants are checked.

## Banking interpretation

Deposits are bank liabilities; loans and securities are bank assets; reserves are settlement liquidity; capital absorbs losses. Loan rates are policy rate plus a credit spread. Deposit flight and bank runs drain deposits/reserves. Failure is an abstraction that flags a bank and leaves resolution to a future module.

## Limitations

This is not a complete reproduction of the U.S. banking system. It omits derivatives, shadow banks, international capital flows, Treasury/Fed legal detail, payment-system intraday mechanics, thousands of regulatory reports, market-maker order books, and institution-level balance sheets. Calibration hooks should use public aggregate data only. It must not be used for investment, policy, or financial decisions.

## GPU roadmap

Use array state for 10k residents and firms; batch daily transitions; minimize host/device transfers; checkpoint monthly. A dual V100 SXM2 setup can accelerate array-heavy workloads only with a compatible carrier/server platform. The i3-8100 should remain the orchestration and persistence host only if the carrier exposes a supported CUDA environment.
