import os
import sys

# Ensure src directory is in sys.path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Delegate execution to src/streamlit_app.py
target_script = os.path.join(src_dir, "streamlit_app.py")
with open(target_script, "r", encoding="utf-8") as f:
    code = compile(f.read(), target_script, "exec")
    exec(code, globals())
