import re

with open('App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import
import_erp = """import Settings from "./pages/Settings";
import ErpSync from "./pages/ErpSync";
import LoadingSpinner from "./components/LoadingSpinner";"""
content = content.replace('import Settings from "./pages/Settings";\nimport LoadingSpinner from "./components/LoadingSpinner";', import_erp)

# Add route
route_erp = """        <Route
          path="manage-data"
          element={
            <NonITRoute>
              <ManageData />
            </NonITRoute>
          }
        />
        <Route
          path="erp-sync"
          element={
            <AdminRoute>
              <ErpSync />
            </AdminRoute>
          }
        />"""
content = content.replace("""        <Route
          path="manage-data"
          element={
            <NonITRoute>
              <ManageData />
            </NonITRoute>
          }
        />""", route_erp)

with open('App.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching App.jsx")
