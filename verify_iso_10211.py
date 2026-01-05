import ctypes
import numpy as np
import os
import matplotlib.pyplot as plt
import time
import sys

# --- Configuration ---
SO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "thermal_solver_core.so"))
MAX_ITER = 500000 
TOLERANCE = 1e-7

try:
    if not os.path.exists(SO_PATH): raise FileNotFoundError
    lib = ctypes.CDLL(SO_PATH)
    lib.solve_optimized.argtypes = [
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_double),
        ctypes.c_int, ctypes.c_int, ctypes.c_int
    ]
    lib.solve_optimized.restype = ctypes.c_double
    print(f"[INFO] Loaded C++ Solver", flush=True)
except: lib=None

def run_solver(temp, cond, fixed_mask, fixed_values, max_iter=MAX_ITER, tol=TOLERANCE):
    if lib is None: raise RuntimeError
    rows, cols = temp.shape
    temp_c = np.ascontiguousarray(temp, dtype=np.float64)
    cond_c = np.ascontiguousarray(cond, dtype=np.float64)
    mask_c = np.ascontiguousarray(fixed_mask, dtype=np.int32)
    fval_c = np.ascontiguousarray(fixed_values, dtype=np.float64)
    
    p_temp = temp_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_cond = cond_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    p_mask = mask_c.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
    p_fval = fval_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    
    batch=20000
    start_t = time.time()
    for k in range(0, max_iter, batch):
        diff = lib.solve_optimized(p_temp, p_cond, p_mask, p_fval, rows, cols, batch)
        print(f"    Iter {k+batch:6d}: Diff {diff:.2e} (T={time.time()-start_t:.1f}s)", flush=True)
        if diff < tol:
            print(f"  -> Converged in {k+batch} iters", flush=True)
            return temp_c
    print(f"  -> Max iters {max_iter} reached (Diff {diff:.2e})", flush=True)
    return temp_c

def test_case_1():
    print("\n--- Running ISO 10211 Test Case 1 ---", flush=True)
    GRID_MM=1.0; W_mm=200; H_mm=400; nx=int(W_mm/GRID_MM)+1; ny=int(H_mm/GRID_MM)+1
    temp=np.zeros((ny,nx)); cond=np.full((ny,nx),0.1); mask=np.zeros((ny,nx),dtype=np.int32); val=np.zeros((ny,nx))
    
    # BCs
    mask[-1,:]=1; val[-1,:]=20.0 # Top
    mask[:,-1]=1; val[:,-1]=0.0  # Right
    mask[0,:]=1;  val[0,:]=0.0   # Bottom
    temp[:]=10.0; temp[mask==1]=val[mask==1]
    
    res = run_solver(temp, cond, mask, val)
    
    # Check
    ix=int(150/GRID_MM); iy=int(300/GRID_MM)
    t_check = res[iy, ix]
    print(f"  Check Point (150, 300): {t_check:.4f} C (Ref: 5.25)", flush=True)
    if abs(t_check - 5.25) < 0.1: print("  [PASS] Case 1 Verified", flush=True)
    else: print(f"  [FAIL] Deviation {abs(t_check-5.25):.4f}", flush=True)
    plt.figure(); plt.imshow(res, cmap='jet', origin='lower'); plt.savefig('iso_case_1_result.png')

def test_case_2():
    print("\n--- Running ISO 10211 Test Case 2 (Full Metal Bottom) ---", flush=True)
    # Materials
    MAT_CONC=1.15; MAT_WOOD=0.12; MAT_INS=0.029; MAT_ALU=230.0
    GRID_MM=0.5; W_mm=500.0; H_mm=47.5
    nx=int(W_mm/GRID_MM)+1; ny=int(H_mm/GRID_MM)+1; dx=GRID_MM/1000.0
    
    cond = np.full((ny, nx), MAT_INS) # Background 0.029
    def to_idx(v): return int(round(v/GRID_MM))
    
    # Geometry (Image Re-verified)
    # 1. Concrete (Top 6mm, Full Width)
    cond[to_idx(41.5):to_idx(47.5), :] = MAT_CONC
    
    # 2. Wood (Left Block, 15x6.5 mm) - Touching Metal
    cond[to_idx(35.0):to_idx(41.5), to_idx(0):to_idx(15)] = MAT_WOOD
    
    # 3. Gap (35.0..36.5) -> Remains INS (Background)
    # Note: Wood starts 36.5. Top Flange ends 35.0. Gap=1.5mm.
    
    # 4. Metal Top Flange (15mm wide)
    cond[to_idx(33.5):to_idx(35.0), to_idx(0):to_idx(15)] = MAT_ALU
    
    # 5. Metal Web (1.5mm wide, 1.5..33.5)
    cond[to_idx(1.5):to_idx(33.5), to_idx(0):to_idx(1.5)] = MAT_ALU
    
    # 6. Metal Bottom Flange (Full Width 500mm)
    cond[to_idx(0):to_idx(1.5), :] = MAT_ALU
    
    # Stats
    uniq, counts = np.unique(cond, return_counts=True)
    print("  Material Counts:", dict(zip(uniq, counts)), flush=True)
    
    # Boundaries
    ny_p=ny+2; cond_p=np.full((ny_p, nx),0.029); fix_p=np.zeros((ny_p,nx),dtype=np.int32); val_p=np.zeros((ny_p,nx))
    cond_p[1:-1,:] = cond
    
    # Bottom (Inside T=20)
    cond_p[0,:] = dx/(2*0.11); fix_p[0,:]=1; val_p[0,:]=20.0
    
    # Top (Outside T=0)
    cond_p[-1,:] = dx/(2*0.06); fix_p[-1,:]=1; val_p[-1,:]=0.0
    
    # MAX_ITER updated globally or here
    
    # Initialize with gradient 20 -> 0 to speed up convergence
    temp_p = np.linspace(20, 0, ny_p)[:, None] * np.ones((1, nx))
    
    # Run with higher iter limit
    res = run_solver(temp_p, cond_p, fix_p, val_p, max_iter=2000000)
    
    # Flux
    flux_in=0.0; flux_out=0.0
    for i in range(nx):
        ki=2*cond_p[0,i]*cond_p[1,i]/(cond_p[0,i]+cond_p[1,i]+1e-12)
        flux_in += ki*(res[0,i]-res[1,i])
        
        ko=2*cond_p[-1,i]*cond_p[-2,i]/(cond_p[-1,i]+cond_p[-2,i]+1e-12)
        flux_out += ko*(res[-2,i]-res[-1,i])
        
    print(f"  Flux In:  {flux_in:.4f} W/m", flush=True)
    print(f"  Flux Out: {flux_out:.4f} W/m", flush=True)
    print(f"  Target:   9.5 W/m", flush=True)
    
    if abs(flux_in - 9.5) < 0.5: print("  [PASS] Case 2 Verified", flush=True)
    else: print("  [WARN] Flux Deviation", flush=True)
    
    plt.figure(figsize=(10,2))
    plt.imshow(res[1:-1], cmap='jet', origin='lower')
    plt.title(f'Flux={flux_in:.2f}')
    plt.savefig('iso_case_2_result.png')

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "2":
        test_case_2()
    elif len(sys.argv) > 1 and sys.argv[1] == "1":
        test_case_1()
    else:
        test_case_1()
        test_case_2()
