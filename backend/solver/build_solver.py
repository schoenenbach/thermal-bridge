import subprocess
import os

def build():
    print("Building C++ Thermal Solver...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cpp_file = os.path.join(script_dir, "thermal_solver_core.cpp")
    so_file = os.path.join(script_dir, "thermal_solver_core.so")
    
    cmd = [
        "g++",
        "-O3",
        "-march=native",
        "-ffast-math",
        "-funroll-loops",
        "-flto",
        "-shared",
        "-fPIC",
        "-fopenmp",
        cpp_file,
        "-o",
        so_file
    ]
    
    try:
        subprocess.check_call(cmd)
        print("Build successful: thermal_solver_core.so created.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        exit(1)

if __name__ == "__main__":
    build()
