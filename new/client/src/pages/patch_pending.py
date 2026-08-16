import re

with open('ManageData.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

patch_code = """    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [pendingEmissions, setPendingEmissions] = useState({ scope1: [], scope2: [], scope3: [] });

    const fetchPendingEmissions = async () => {
        if (user?.role !== 'admin' && user?.role !== 'superuser') return;
        try {
            const res = await api.get('/emissions/pending');
            setPendingEmissions({
                scope1: res.data.scope1 || [],
                scope2: res.data.scope2 || [],
                scope3: res.data.scope3 || []
            });
        } catch (e) {
            console.error("Failed to fetch pending emissions", e);
        }
    };
"""

content = content.replace("    const [loading, setLoading] = useState(false);\n    const [searchTerm, setSearchTerm] = useState('');", patch_code)

with open('ManageData.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching ManageData.jsx for missing pendingEmissions")
