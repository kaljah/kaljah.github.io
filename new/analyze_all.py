import os
import ast
import re

def analyze_python_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        return f"Python Module. Classes: {', '.join(classes) if classes else 'None'}. Functions: {', '.join(functions) if functions else 'None'}."
    except Exception as e:
        return f"Could not parse python file: {e}"

def analyze_js_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple regex to find function/class declarations
    funcs = re.findall(r'function\s+([a-zA-Z0-9_]+)', content)
    arrow_funcs = re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_]+)\s*=>', content)
    classes = re.findall(r'class\s+([a-zA-Z0-9_]+)', content)
    
    all_funcs = list(set(funcs + arrow_funcs))
    return f"JS/React Component. Classes: {', '.join(classes) if classes else 'None'}. Functions/Components: {', '.join(all_funcs) if all_funcs else 'None'}."

def analyze_directory(root_dir, skip_dirs=('.git', 'node_modules', 'venv', '__pycache__', 'graphify-out')):
    results = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for filename in filenames:
            if filename.endswith(('.py', '.js', '.jsx')):
                filepath = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(filepath, start=root_dir)
                
                if filename.endswith('.py'):
                    summary = analyze_python_file(filepath)
                else:
                    summary = analyze_js_file(filepath)
                    
                results.append(f"### `{rel_path}`\n{summary}\n")
    return results

if __name__ == "__main__":
    base_dir = r"c:\Users\samsung\Desktop\H2\new"
    
    server_analysis = analyze_directory(os.path.join(base_dir, 'server'))
    client_analysis = analyze_directory(os.path.join(base_dir, 'client', 'src'))
    
    with open(os.path.join(base_dir, 'file_by_file_analysis.md'), 'w', encoding='utf-8') as f:
        f.write("# File-by-File Analysis\n\n")
        f.write("## Backend (Server)\n\n")
        f.write("\n".join(server_analysis))
        f.write("\n## Frontend (Client)\n\n")
        f.write("\n".join(client_analysis))
    
    print("File-by-file analysis complete. Saved to file_by_file_analysis.md")
