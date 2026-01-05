# Deployment Guide

## 1. Run Locally (Python)

If you have Python installed and the dependencies are set up:

```bash
streamlit run app.py
```
This will open the simulator in your browser at `http://localhost:8501`.

## 2. Run with Docker (Recommended for Sharing)

To let friends run it without installing Python/C++ compilers, send them the source (or a built image).

### Build the Image
```bash
docker build -t thermal-bridge-sim .
```

### Run the Container
```bash
docker run -p 8501:8501 thermal-bridge-sim
```
They can now access it at `http://localhost:8501`.

## 3. Hosting on a Server (VPS)

If you have a Linux server (DigitalOcean, Hetzner, AWS, etc.):

1.  **Install Docker** on the server.
2.  **Copy the project files** to the server (git clone or scp).
3.  **Build and Run** using the Docker commands above.
4.  (Optional) Use Nginx as a reverse proxy to serve on port 80/443.

## 4. Cloud Deployment (Streamlit Community Cloud)

1.  Push this repository to **GitHub**.
2.  Sign up for [Streamlit Community Cloud](https://streamlit.io/cloud).
3.  Connect your GitHub account and select your repository.
4.  It will automatically detect `app.py` and `requirements.txt` and deploy it for free.
    *   *Note*: Since we compile C++ code (`build_solver.py`), we need to ensure the build happens. Streamlit Cloud usually just installs `requirements.txt`.
    *   **Fix**: Add a `packages.txt` file with `g++` (if needed) and ensure `build_solver.py` is called. We can add a command to `packages.txt` or a `pre-install` script?
    *   Actually, Streamlit Cloud allows `packages.txt` for apt packages. We need `g++`.
    *   And we can add `python build_solver.py` to the top of `app.py` or as a subprocess in setup.

### Special Note for Streamlit Cloud
Create a file `packages.txt`:
```text
g++
libgomp1
```
And ensure the solver is built. Since we can't easily run a build step in their pipeline, we can check in `app.py`:

```python
import os
import subprocess
if not os.path.exists("thermal_solver_core.so"):
    subprocess.check_call(["python3", "build_solver.py"])
```
(This logic is already implicitly handled if you just run the build script, but good to double check context).
