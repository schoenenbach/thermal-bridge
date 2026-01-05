import subprocess
import os

def build():
    print("Building C++ Thermal Solver...")
    cmd = [
        "g++",
        "-O3",
        "-shared",
        "-fPIC",
        "-fopenmp",
        "thermal_solver_core.cpp",
        "-o",
        "thermal_solver_core.so"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("Build successful: thermal_solver_core.so created.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        exit(1)

if __name__ == "__main__":
    build()
