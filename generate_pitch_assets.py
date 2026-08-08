import os
import matplotlib.pyplot as plt
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

OUTPUT_DIR = r"c:\Users\samsung\Desktop\H2\deck_assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Color Palette (Startup Algeria / Carbon Tech Theme)
NAVY = "#1E4E8C"
DARK_NAVY = "#112D55"
TEAL = "#00BFA5"
LIGHT_TEAL = "#A7F3D0"
RED_ALERT = "#E11D48"
ORANGE = "#F59E0B"
BG_LIGHT = "#F8FAFC"
TEXT_DARK = "#1E293B"
GRAY_MUTED = "#64748B"

# ==========================================
# 1. EMISSIONS INTENSITY & CBAM TAX EXPOSURE
# ==========================================
def generate_chart_industry_emissions():
    fig, ax1 = plt.subplots(figsize=(10, 5.5), facecolor=BG_LIGHT)
    ax1.set_facecolor(BG_LIGHT)

    industries = [
        "Engrais & Ammoniac\n(Fertial, Asmidal)",
        "Acier DRI / EAF\n(Tosyali, AQS)",
        "Ciment & Clinker\n(GICA, Lafarge)",
        "Pétrochimie\n(Raffinage/Polymères)",
        "Amont Gazier\n(Sonatrach Torchage)"
    ]
    
    # Intensité Carbone (t CO2e / t produit ou équivalent)
    intensity = [2.15, 1.48, 0.76, 0.52, 0.95]
    
    # Coût de la taxe CBAM à 75€/t CO2e pour 500k tonnes exportées (en Millions d'Euros)
    tax_exposure = [round(i * 0.5 * 75, 1) for i in intensity]

    x = np.arange(len(industries))
    width = 0.38

    bars1 = ax1.bar(x - width/2, intensity, width, label='Intensité d\'émission (t CO2e / tonne)', color=NAVY, edgecolor=DARK_NAVY, alpha=0.95, zorder=3)
    
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, tax_exposure, width, label='Taxe CBAM annuelle (€/500kt à 75€/t)', color=RED_ALERT, edgecolor="#9F1239", alpha=0.9, zorder=3)

    # Grid and styling
    ax1.grid(axis='y', linestyle='--', alpha=0.5, color='#CBD5E1', zorder=0)
    ax2.grid(False)

    ax1.set_ylabel('Intensité Carbone (t CO2e / t)', fontsize=11, fontweight='bold', color=NAVY)
    ax2.set_ylabel('Exposition Fiscale CBAM (Millions € / 500kt)', fontsize=11, fontweight='bold', color=RED_ALERT)
    ax1.set_xticks(x)
    ax1.set_xticklabels(industries, fontsize=9.5, fontweight='bold', color=TEXT_DARK)
    
    # Add values on top of bars
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 0.05, f"{yval:.2f} t", ha='center', va='bottom', fontsize=9, fontweight='bold', color=NAVY)
        
    for bar in bars2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 1.2, f"{yval:.1f} M€", ha='center', va='bottom', fontsize=9, fontweight='bold', color=RED_ALERT)

    ax1.set_ylim(0, 2.7)
    ax2.set_ylim(0, 95)
    
    plt.title("Intensité d'Émissions des Industries Clés en Algérie & Menace Fiscale CBAM", fontsize=13, fontweight='bold', color=DARK_NAVY, pad=18)
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=9)
    
    # Highlight box
    ax1.text(0.02, 0.88, "Sans mesure précise Tier 3,\nces montants explosent de +35% !", transform=ax1.transAxes, 
             fontsize=9, fontweight='bold', color=RED_ALERT, bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFE4E6", edgecolor=RED_ALERT, alpha=0.9))

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart_industry_emissions.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated:", path)

# ==========================================
# 2. DEFAULT VALUES PENALTY GAP VS TIER 3 SAVINGS
# ==========================================
def generate_chart_cbam_savings():
    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=BG_LIGHT)
    ax.set_facecolor(BG_LIGHT)

    sectors = ["Aciérie DRI\n(Export 1M t)", "Ammoniac / Engrais\n(Export 500k t)", "Ciment & Clinker\n(Export 800k t)"]
    default_cost = [142.5, 95.6, 54.0] # En Millions € (valeurs pénalisantes EU)
    actual_cost = [111.0, 80.6, 45.6]  # En Millions € (calcul réel gaz naturel Tier 3)
    savings = [round(d - a, 1) for d, a in zip(default_cost, actual_cost)]

    y = np.arange(len(sectors))
    height = 0.32

    rects1 = ax.barh(y + height/2, default_cost, height, label='Taxe avec Valeurs par Défaut UE (Pénalité +10% pire)', color=RED_ALERT, alpha=0.9, edgecolor="#9F1239", zorder=3)
    rects2 = ax.barh(y - height/2, actual_cost, height, label='Taxe avec Calcul Réel Ingénierie Carbon Tech (Tier 3)', color=TEAL, alpha=0.95, edgecolor="#065F46", zorder=3)

    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#CBD5E1', zorder=0)
    ax.set_xlabel('Montant Annuel de la Taxe CBAM (Millions d\'Euros)', fontsize=10.5, fontweight='bold', color=DARK_NAVY)
    ax.set_yticks(y)
    ax.set_yticklabels(sectors, fontsize=10, fontweight='bold', color=TEXT_DARK)
    
    # Add values and savings annotations
    for rect, cost in zip(rects1, default_cost):
        ax.text(rect.get_width() + 1.5, rect.get_y() + rect.get_height()/2.0, f"{cost} M€", ha='left', va='center', fontsize=9.5, fontweight='bold', color=RED_ALERT)
    
    for i, (rect, cost, save) in enumerate(zip(rects2, actual_cost, savings)):
        ax.text(rect.get_width() + 1.5, rect.get_y() + rect.get_height()/2.0, f"{cost} M€", ha='left', va='center', fontsize=9.5, fontweight='bold', color=TEAL)
        # Annotation badge
        ax.annotate(f"Économie directe :\n-{save} M€ / an ({round(save/default_cost[i]*100)}%)",
                    xy=(actual_cost[i], y[i] - height/2),
                    xytext=(actual_cost[i] - 30, y[i] - height/2 - 0.28),
                    bbox=dict(boxstyle="round,pad=0.3", fc="#ECFDF5", ec=TEAL, lw=1.5),
                    fontsize=8.5, fontweight='bold', color="#065F46",
                    arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.5))

    ax.set_xlim(0, 165)
    plt.title("L'Impact Financier de la Précision : Valeurs par Défaut UE vs Carbon Tech", fontsize=13, fontweight='bold', color=DARK_NAVY, pad=18)
    ax.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart_cbam_savings.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated:", path)

# ==========================================
# 3. REPORTING RISK COMPARISON
# ==========================================
def generate_chart_reporting_risks():
    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=BG_LIGHT)
    ax.set_facecolor(BG_LIGHT)

    categories = ["Sous-Déclaration\n(Facteurs sous-évalués)", "Sur-Déclaration / Défaut\n(Facteurs génériques / Excel)", "Précision Tier 3\n(Carbon Tech SaaS)"]
    risk_level = [95, 85, 10]
    financial_waste = [80, 90, 5]

    x = np.arange(len(categories))
    width = 0.35

    ax.bar(x - width/2, risk_level, width, label='Niveau de Risque Juridique & Audit (%)', color=RED_ALERT, alpha=0.85, edgecolor="#9F1239", zorder=3)
    ax.bar(x + width/2, financial_waste, width, label='Surcoût Fiscal Inutile / Pertes (%)', color=ORANGE, alpha=0.85, edgecolor="#B45309", zorder=3)

    ax.grid(axis='y', linestyle='--', alpha=0.5, color='#CBD5E1', zorder=0)
    ax.set_ylabel('Gravité de l\'Impact (%)', fontsize=11, fontweight='bold', color=DARK_NAVY)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10, fontweight='bold', color=TEXT_DARK)
    ax.set_ylim(0, 115)

    # Bullet descriptions inside plot
    ax.text(0 - width/2, 100, "Amendes lourdes (10-50€/t)\nRejet en douane UE", ha='center', fontsize=8.5, fontweight='bold', color=RED_ALERT)
    ax.text(1 + width/2, 95, "Fuite de devises massive\nPerte marge exportateur", ha='center', fontsize=8.5, fontweight='bold', color="#B45309")
    ax.text(2, 20, "Conformité Totale ISO/CBAM\nÉconomies Maximisées", ha='center', fontsize=9, fontweight='bold', color="#065F46",
            bbox=dict(boxstyle="round,pad=0.3", fc="#ECFDF5", ec=TEAL, lw=1.2))

    plt.title("Risques Comparés : Sous-Déclaration vs Sur-Déclaration vs Solution Carbon Tech", fontsize=12.5, fontweight='bold', color=DARK_NAVY, pad=18)
    ax.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', fontsize=9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart_reporting_risks.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated:", path)

# ==========================================
# 4. COMPETITIVE POSITIONING MATRIX
# ==========================================
def generate_chart_competitive_matrix():
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=BG_LIGHT)
    ax.set_facecolor(BG_LIGHT)

    competitors = [
        (20, 25, 400, "Feuilles Excel Internes\n(Pratique actuelle 85%)", "#94A3B8"),
        (40, 75, 450, "Cabinets d'Audit Traditionnels\n(PwC, EY, SGS)", "#64748B"),
        (85, 30, 500, "Logiciels ESG Génériques\n(Greenly, Sweep, EcoVadis)", "#3B82F6"),
        (92, 92, 900, "CARBON TECH\n(Ingénierie Physique & MRV)", TEAL)
    ]

    ax.axvline(x=50, color='#CBD5E1', linestyle='--', linewidth=1.5, zorder=1)
    ax.axhline(y=50, color='#CBD5E1', linestyle='--', linewidth=1.5, zorder=1)

    ax.fill_between([50, 100], 50, 100, color="#ECFDF5", alpha=0.5, zorder=0)
    ax.fill_between([0, 50], 0, 50, color="#FFF1F2", alpha=0.3, zorder=0)

    ax.text(98, 98, "ZONE D'EXCELLENCE\n(Précision Tier 3 + SaaS Automatisé)", ha='right', va='top', fontsize=8.5, fontweight='bold', color="#065F46")
    ax.text(2, 2, "ZONE À RISQUE\n(Calculs manuels, Facteurs génériques)", ha='left', va='bottom', fontsize=8.5, fontweight='bold', color="#9F1239")

    for x, y, size, name, col in competitors:
        edge = DARK_NAVY if name.startswith("CARBON") else "#475569"
        ax.scatter(x, y, s=size, color=col, edgecolors=edge, linewidth=2, alpha=0.9, zorder=4)
        offset_y = 5 if y < 90 else -8
        offset_x = 0
        weight = 'bold' if name.startswith("CARBON") else 'normal'
        ax.text(x + offset_x, y + offset_y, name, ha='center', va='center', fontsize=9.5, fontweight=weight, color=DARK_NAVY, zorder=5,
                bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFFF", ec=col, alpha=0.85, lw=1.2) if name.startswith("CARBON") else None)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel('Niveau d\'Automatisation & Déploiement SaaS (%)', fontsize=10.5, fontweight='bold', color=DARK_NAVY)
    ax.set_ylabel('Précision d\'Ingénierie & Modélisation Procédés (Tier 3) (%)', fontsize=10.5, fontweight='bold', color=DARK_NAVY)
    
    plt.title("Positionnement Concurrentiel Unique sur le Marché Industriel", fontsize=13, fontweight='bold', color=DARK_NAVY, pad=18)
    
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart_competitive_matrix.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated:", path)

# ==========================================
# 5. MARKET SIZING TAM SAM SOM
# ==========================================
def generate_chart_market_sizing():
    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor=BG_LIGHT)
    ax.set_facecolor(BG_LIGHT)

    labels = [
        "TAM : Industrie & Énergie Algérie & Maghreb\n(180+ Grands Complexes Industriels - 24 M€/an)",
        "SAM : Exportateurs CBAM & Sites Énergétiques Clés\n(75 Sites Électro-Intensifs / O&G - 9.5 M€/an)",
        "SOM : Objectif 3 Ans Carbon Tech\n(35 Sites Souscrits - 3.2 M€ ARR)"
    ]
    sizes = [100, 45, 18]
    colors = [NAVY, "#2563EB", TEAL]

    y = np.arange(len(labels))
    bars = ax.barh(y, sizes, color=colors, height=0.45, edgecolor=DARK_NAVY, alpha=0.9, zorder=3)

    ax.grid(axis='x', linestyle='--', alpha=0.5, color='#CBD5E1', zorder=0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5, fontweight='bold', color=TEXT_DARK)
    ax.set_xlabel('Part de Marché Potentielle Relativisée (%)', fontsize=10, fontweight='bold', color=DARK_NAVY)
    ax.set_xlim(0, 120)

    for bar, val in zip(bars, [ "24M€ TAM", "9.5M€ SAM", "3.2M€ SOM"]):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, val, ha='left', va='center', fontsize=10, fontweight='bold', color=DARK_NAVY)

    plt.title("Opportunité de Marché & Objectifs d'Adoption (TAM / SAM / SOM)", fontsize=12.5, fontweight='bold', color=DARK_NAVY, pad=18)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart_market_sizing.png")
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print("Generated:", path)

if __name__ == "__main__":
    generate_chart_industry_emissions()
    generate_chart_cbam_savings()
    generate_chart_reporting_risks()
    generate_chart_competitive_matrix()
    generate_chart_market_sizing()
    print("All charts successfully generated!")
