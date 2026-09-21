# freeview: Interactive FreeSurfer Stats Dashboard

[![PyPI Version](https://img.shields.io/pypi/v/freeview?label=PyPI&color=gold)](https://pypi.org/project/freeview/)
[![Python Versions](https://img.shields.io/pypi/pyversions/freeview)](https://pypi.org/project/freeview/)
[![License](https://img.shields.io/badge/license-GPLv3-deepgreen.svg?style=flat)](https://github.com/kkt-ee/freeview/LICENSE)

<!-- Prerequisite: Python 3.10 or newer (recommend Python 3.12). -->




## Quick install (recommended)

Use a Python 3.10+ interpreter when creating the virtual environment.


**Install `freeview`**:

- Linux / macOS:

```bash
# ensure you pick a 3.10+ interpreter (3.12 recommended)
python3.12 -m venv freeviewer
./freeviewer/bin/python -m pip install --upgrade pip
./freeviewer/bin/python -m pip install freeview
./freeviewer/bin/freeview cert
./freeviewer/bin/freeview serve
```

- Windows (PowerShell):

```powershell
py -3.12 -m venv freeviewer
.\freeviewer\Scripts\python.exe -m pip install --upgrade pip
.\freeviewer\Scripts\python.exe -m pip install freeview
.\freeviewer\Scripts\freeview.exe cert
.\freeviewer\Scripts\freeview.exe serve
```

<!-- Notes:
- Prefer `python -m pip ...` so you always run the venv's pip.
- If you see `ERROR: Package 'freeview' requires a different Python: X not in '>=3.10'`, recreate the venv with a Python 3.10+ interpreter (this means the wheel was built for Python >=3.10). -->


<!-- ## One-step local installer scripts

```bash
./install_freeviewer.sh /path/to/freeview.whl   # optional wheel path
./uninstall_freeviewer.sh
```

Windows PowerShell:

```powershell
.\install_freeviewer.ps1
.\uninstall_freeviewer.ps1
```
-->

**Key Note**: If `mkcert` is **not available**, `freeview cert` and `freeview serve` will print installation hints and will not start until valid, trusted certs exist. `freeview` will call `mkcert -install` and then `mkcert -ecdsa` to generate `localhost.pem` and `localhost-key.pem` in the per-user cert directory.



## Setup local certificates (important)

Certificates are required for the recommended HTTPS-only local setup.



- `freeview` requires HTTPS for `localhost`. The CLI command `freeview cert` will create and trust a local CA using `mkcert` (explicit consent is requested) and generate ECDSA P-256 certs.
- Generated certs are stored per-user:
	- macOS / Linux: `$XDG_DATA_HOME/freeview/certs` or `~/.local/share/freeview/certs`
	- Windows: `%APPDATA%\\freeview\\certs`

<!-- Typical flow (after installing `freeview`):

```bash
# create or verify certs
freeview cert
# start server (HTTPS):
freeview serve
``` -->



<!-- `freeview serve` looks for `localhost.pem` and `localhost-key.pem` in the cert directory above and will refuse to start without trusted certs (it will offer to run `mkcert` for you, but consent is required). -->
<br>


### (Dependency) Install `mkcert` to create local certificates:

- Linux:

```bash
sudo apt install -y mkcert libnss3-tools 
```

- macOS:

```bash
brew install mkcert 
```

- Windows (Admin PowerShell):

```powershell
choco install mkcert -y
# mkcert -install
```

*For other Linux distros, see mkcert's official guidelines*: use your distro package or download the binary from https://github.com/FiloSottile/mkcert and run `mkcert -install`.

After installing `mkcert`, create the local certificates

### Create local certificates

```bash
./freeviewer/bin/freeview cert   # to create local certificates
```

<!-- Manual example for advanced user (if you prefer to run `mkcert` yourself):

```bash
mkdir -p ~/.local/share/freeview/certs
mkcert -install
mkcert -ecdsa -cert-file ~/.local/share/freeview/certs/localhost.pem \\
	-key-file ~/.local/share/freeview/certs/localhost-key.pem \\
	localhost 127.0.0.1 ::1
``` -->


**INSTALLATION COMPLETE**


## Launch `freeview` dashboard
<!-- The above `freeview cert` command creates, the  following command will launch the `freeview` dashboard -->


```bash
./freeviewer/bin/freeview serve --port 8501   # when using a local venv
```


**Note**: The viewer should be running in the default URL: `https://localhost:8501`


---

<br><br><br><br>


## Troubleshooting

- `ERROR: Package 'freeview' requires a different Python`: your venv Python is older than 3.10 — recreate the venv with a 3.10+ interpreter (for example `python3.12 -m venv freeviewer`).
- `no such file or directory: ./freeviewer/bin/freeview`: the package failed to install into that venv (or you typed an extra dot like `freeview..`). Re-run the install steps above.
- Browser certificate warnings: run `mkcert -install` (or `freeview cert`), then restart the browser.
- Upgrade pip inside the venv if you see pip warnings:

```bash
./freeviewer/bin/python -m pip install --upgrade pip
```


## Install from a local wheel (developer / offline)

Build a wheel in the project root (requires the `build` package):

```bash
./freeviewer/bin/python -m pip install --upgrade pip build
./freeviewer/bin/python -m build
./freeviewer/bin/python -m pip install *.whl
```

Replace `./freeviewer/bin/python` with the interpreter you used to create the venv (or `python3.12` if you are not in a venv yet).


## Alternate launch method with Streamlit directly (advanced / debugging)

```bash
python -m streamlit run path/to/freeview/streamlit_app.py -- \\
	./output/consolidated_stats.csv ./output/summary.csv
```

When running Streamlit directly and wanting HTTPS you must pass `--server.sslCertFile` and `--server.sslKeyFile`.


## CSV conversion

```bash
freeview stats2csv --stats-dir /path/to/A_T1/stats --out-dir ./output
```

## Citation

This software is released for broad research, educational, and engineering use. If this package helps your work, please cite the following paper:

```bibtex
@misc{tarafdar2026interpretablefrugallearningsystems,
      title={Interpretable and Frugal Learning Systems Employing Multiresolution Pyramids and Volterra Kernels},
      author={Kishore Kumar Tarafdar},
      year={2026},
      eprint={2606.15011},
      archivePrefix={arXiv},
      primaryClass={eess.SP},
      url={https://arxiv.org/abs/2606.15011},
}
```


---

Copyright © 2026 Kishore Kumar Tarafdar

Released under the GNU General Public License v3.0 — see [LICENSE](LICENSE)
