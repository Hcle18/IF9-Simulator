# Helper function to get directories and files
from pathlib import Path

def get_subdirectories(base_path):
    """Get all subdirectories from a base path with hierarchical ordering"""
    try:
        path = Path(base_path)
        if not path.exists():
            return []
        
        # Folders to exclude
        exclude_folders = {'__pycache__', '.git', '.vscode', '.idea',
                            'node_modules', '.pytest_cache', '__MACOSX',
                            '.venv'}
        
        # Recursively build directory tree in order
        def walk_dirs(current_path, result_list):
            """Recursively walk directories in hierarchical order"""
            result_list.append(str(current_path))
            
            try:
                # Get immediate subdirectories only
                subdirs = [item for item in current_path.iterdir() 
                          if item.is_dir()
                          and not any(excluded in item.parts for excluded in exclude_folders)]
                
                # Sort subdirectories alphabetically
                subdirs.sort(key=lambda x: x.name.lower())
                
                # Recursively process each subdirectory
                for subdir in subdirs:
                    walk_dirs(subdir, result_list)
            except (PermissionError, OSError):
                # Skip directories we can't access
                pass
        
        dirs = []
        walk_dirs(path, dirs)
        return dirs
        
    except Exception:
        return [str(base_path)]


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

def format_dir_path(dir_path, base_path):
    """Format directory path to show hierarchy with indentation"""
    try:
        rel_path = Path(dir_path).relative_to(Path(base_path))
        if str(rel_path) == ".":
            return f"📂 {Path(base_path).name}"
        else:
            # Calculate indentation level based on path depth
            depth = len(rel_path.parts) - 1
            print(rel_path)
            # Use non-breaking spaces and tree symbols for better display in selectbox
            indent = "│" + "─" * (depth * 2)  # Tree-like structure
            return f"{indent}📂 {rel_path}"
    except ValueError:
        # If not relative, just show the name
        return f"📂 {Path(dir_path).name}"