import re

with open('Sidebar.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

nav_link_erp = """                  <span className="nav-label">Manage Data</span>
                </NavLink>
              </li>
              {user?.role === "admin" && (
                <li className="nav-item">
                  <NavLink
                    to="/erp-sync"
                    className={({ isActive }) =>
                      `nav-link ${isActive ? "active" : ""}`
                    }
                    title="ERP Sync"
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="nav-icon"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <path d="M12 18v-6" />
                      <path d="M9 15l3-3 3 3" />
                    </svg>
                    <span className="nav-label">ERP Sync</span>
                  </NavLink>
                </li>
              )}
"""
content = content.replace("""                  <span className="nav-label">Manage Data</span>
                </NavLink>
              </li>""", nav_link_erp)

with open('Sidebar.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching Sidebar.jsx for ERP sync")
