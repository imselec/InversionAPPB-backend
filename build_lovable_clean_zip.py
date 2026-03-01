import os
import zipfile

PROJECT_ROOT = os.path.abspath(".")
ZIP_NAME = "lovable_project_clean.zip"

# Carpetas permitidas
INCLUDE_DIRS = {"app", "tests"}

# Archivos permitidos en raíz
INCLUDE_FILES = {".env"}

# Carpetas a excluir
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "env",
    "node_modules",
    ".idea",
    ".vscode",
}

# Extensiones a excluir
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".log", ".tmp"}


def should_include_file(filepath):
    filename = os.path.basename(filepath)

    # excluir extensiones
    _, ext = os.path.splitext(filename)
    if ext in EXCLUDE_EXTENSIONS:
        return False

    # excluir pycache
    if "__pycache__" in filepath:
        return False

    return True


def should_include_dir(dirname):
    return dirname not in EXCLUDE_DIRS


def build_zip():
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:

        # incluir carpetas principales
        for include_dir in INCLUDE_DIRS:

            if not os.path.exists(include_dir):
                continue

            for root, dirs, files in os.walk(include_dir):

                # filtrar dirs excluidos
                dirs[:] = [d for d in dirs if should_include_dir(d)]

                for file in files:

                    full_path = os.path.join(root, file)

                    if should_include_file(full_path):
                        arcname = os.path.relpath(full_path, PROJECT_ROOT)
                        zipf.write(full_path, arcname)

        # incluir archivos raíz
        for file in INCLUDE_FILES:

            if os.path.exists(file):
                zipf.write(file, file)

    print(f"\n✅ ZIP limpio generado: {ZIP_NAME}")
    print("Listo para subir a Lovable")


if __name__ == "__main__":
    build_zip()
