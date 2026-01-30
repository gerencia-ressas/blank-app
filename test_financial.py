import numpy as np
try:
    import numpy_financial as npf
    print("numpy_financial is available")
except ImportError:
    print("numpy_financial is NOT available")
    npf = None

def calculate_irr(values):
    if npf:
        return npf.irr(values)
    try:
        return np.irr(values)
    except AttributeError:
        # Simple Newton-Raphson implementation for verification if needed, 
        # but for this test we mainly want to see if it crashes or returns reasonable values
        print("Using custom/fallback IRR logic would go here if np.irr fails")
        return 0.10 # dummy for test if both fail

def calculate_npv(rate, values):
    if npf:
        return npf.npv(rate, values)
    try:
        return np.npv(rate, values)
    except AttributeError:
        values = np.asarray(values)
        t = np.arange(len(values))
        return (values / (1 + rate) ** t).sum()

# Test case
inversion = 10_000_000
ahorro = 1_000_000
rate = 0.10
flows = [-inversion] + [ahorro] * 20

print(f"NPV: {calculate_npv(rate, flows)}")
print(f"IRR: {calculate_irr(flows)}")
