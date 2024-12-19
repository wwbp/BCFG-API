import os

def print_directory_structure(root_dir):
    ignore = {'__pycache__', '*.pyc', '.git', '.env', '.dockerignore', '.DS_Store'}
    
    for root, dirs, files in os.walk(root_dir):
        # Remove ignored directories from the list of dirs
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith('.')]
        files = [f for f in files if f not in ignore and not f.startswith('.')]

        level = root.replace(root_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")

        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{sub_indent}{f}")

if __name__ == "__main__":
    print_directory_structure(".")
