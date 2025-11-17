# Helper function to get directories and files
from pathlib import Path

def get_subdirectories(base_path):
    """Get all subdirectories from a base path with relative paths"""
    try:
        path = Path(base_path)
        if not path.exists():
            return []
        
        # Folders to exclude
        exclude_folders = {'__pycache__', '.git', '.vscode', '.idea',
                            'node_modules', '.pytest_cache', '__MACOSX',
                            '.venv'}
        
        dirs = [str(base_path)]  # Include base path itself
        for item in path.rglob("*"):
            if item.is_dir():
                # Skip if any part of the path is in exclude list
                if not any(excluded in item.parts for excluded in exclude_folders):
                    dirs.append(str(item))
        return sorted(dirs)
    except Exception:
        return [str(base_path)]

def format_dir_path(dir_path, base_path):
    """Format directory path to show hierarchy"""
    try:
        rel_path = Path(dir_path).relative_to(Path(base_path))
        if str(rel_path) == ".":
            return f"📂 {Path(base_path).name}"
        else:
            # Show relative path with hierarchy
            return f"📂 {Path(base_path).name}/{rel_path}"
    except ValueError:
        # If not relative, just show the name
        return f"📂 {Path(dir_path).name}"

def get_files_in_directory(directory, extensions=None):
    """Get all files in a directory with optional extension filter"""
    try:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return []
        files = []
        for item in path.iterdir():
            if item.is_file():
                if extensions is None or item.suffix.lower() in extensions:
                    files.append(str(item))
        return sorted(files)
    except Exception:
        return []