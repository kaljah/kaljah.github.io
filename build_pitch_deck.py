import os
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# Initialize Presentation
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Color Palette Definitions
NAVY = RGBColor(30, 78, 140)       # #1E4E8C
DARK_NAVY = RGBColor(17, 45, 85)   # #112D55
TEAL = RGBColor(0, 191, 165)       # #00BFA5
EMERALD = RGBColor(5, 150, 105)    # #059669
CARD_BG = RGBColor(248, 250, 252)  # #F8FAFC
CARD_BORDER = RGBColor(203, 213, 225) # #CBD5E1
TEXT_DARK = RGBColor(30, 41, 59)   # #1E293B
TEXT_MUTED = RGBColor(100, 116, 139) # #64748B
WHITE = RGBColor(255, 255, 255)
RED_ACCENT = RGBColor(225, 29, 72) # #E11D48
AMBER = RGBColor(217, 119, 6)      # #D97706

ASSETS_DIR = r"c:\Users\samsung\Desktop\H2\deck_assets"

def add_header(slide, title_text, category_text="1. PRÉSENTATION GÉNÉRALE"):
    """Adds standard Startup Algeria header banner with accent bar and title."""
    # Left accent indicator bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.5), Inches(0.15), Inches(0.6))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.color.rgb = NAVY

    # Header category & title text
    tb = slide.shapes.add_textbox(Inches(1.1), Inches(0.42), Inches(11.4), Inches(0.75))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    p = tf.paragraphs[0]
    p.text = category_text.upper()
    p.font.name = "Arial"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = NAVY

def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
    """Creates a modern rounded rectangular card container."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.2)
    else:
        shape.line.fill.background()
    return shape

# ==========================================
# SLIDE 1: TITLE SLIDE
# ==========================================
s1 = prs.slides.add_slide(prs.slide_layouts[6]) # blank layout

# Top subtle accent line
top_line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.15))
top_line.fill.solid()
top_line.fill.fore_color.rgb = TEAL
top_line.line.fill.background()

# Main Title Container
tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.9), Inches(4.5))
tf1 = tb1.text_frame
tf1.word_wrap = True
tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

p = tf1.paragraphs[0]
p.text = "PITCH DECK"
p.alignment = PP_ALIGN.CENTER
p.font.name = "Arial"
p.font.size = Pt(54)
p.font.bold = True
p.font.color.rgb = NAVY

p2 = tf1.add_paragraph()
p2.text = "PRÉSENTATION DU PROJET INNOVANT"
p2.alignment = PP_ALIGN.CENTER
p2.font.name = "Arial"
p2.font.size = Pt(22)
p2.font.bold = True
p2.font.color.rgb = NAVY
p2.space_before = Pt(15)

p3 = tf1.add_paragraph()
p3.text = "CARBON TECH : Plateforme SaaS d'Ingénierie Carbone & Conformité MACF / CBAM"
p3.alignment = PP_ALIGN.CENTER
p3.font.name = "Arial"
p3.font.size = Pt(15)
p3.font.color.rgb = TEAL
p3.font.bold = True
p3.space_before = Pt(25)

p4 = tf1.add_paragraph()
p4.text = "Candidature au Label « Projet Innovant » / « Startup » • République Algérienne Démocratique et Populaire"
p4.alignment = PP_ALIGN.CENTER
p4.font.name = "Arial"
p4.font.size = Pt(12)
p4.font.color.rgb = TEXT_MUTED
p4.space_before = Pt(10)

# Bottom decorative badge
b_card = add_card(s1, Inches(3.6), Inches(6.1), Inches(6.1), Inches(0.6), bg_color=CARD_BG, border_color=TEAL)
b_tb = s1.shapes.add_textbox(Inches(3.7), Inches(6.15), Inches(5.9), Inches(0.5))
b_tf = b_tb.text_frame
b_p = b_tf.paragraphs[0]
b_p.text = "Solution Souveraine d'Ingénierie pour les Industries Lourdes & Exportatrices"
b_p.alignment = PP_ALIGN.CENTER
b_p.font.name = "Arial"
b_p.font.size = Pt(11)
b_p.font.bold = True
b_p.font.color.rgb = DARK_NAVY

# ==========================================
# SLIDE 2: PRÉSENTATION GÉNÉRALE (BRAND & VISION)
# ==========================================
s2 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s2, "PRÉSENTATION GÉNÉRALE", "1. PRÉSENTATION GÉNÉRALE")

# Logo & Branding Box
logo_box = add_card(s2, Inches(1.0), Inches(1.4), Inches(11.333), Inches(2.2), bg_color=WHITE, border_color=CARD_BORDER)
tb = s2.shapes.add_textbox(Inches(1.5), Inches(1.6), Inches(10.3), Inches(1.8))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "CARBON TECH"
p.alignment = PP_ALIGN.CENTER
p.font.name = "Arial"
p.font.size = Pt(40)
p.font.bold = True
p.font.color.rgb = DARK_NAVY

p2 = tf.add_paragraph()
p2.text = "M E A S U R E   •   A N A L Y Z E   •   R E D U C E"
p2.alignment = PP_ALIGN.CENTER
p2.font.name = "Arial"
p2.font.size = Pt(14)
p2.font.bold = True
p2.font.color.rgb = TEAL
p2.space_before = Pt(8)

p3 = tf.add_paragraph()
p3.text = "Plateforme intelligente de comptabilité carbone et d'ingénierie des émissions de GES"
p3.alignment = PP_ALIGN.CENTER
p3.font.name = "Arial"
p3.font.size = Pt(13)
p3.font.color.rgb = NAVY
p3.space_before = Pt(10)

# 3 Highlights Cards
cards_data = [
    ("SOUVERAINETÉ & PRÉCISION", "Calculs basés sur la physique réelle des procédés (Tier 3) plutôt que des moyennes forfaitaires.", TEAL),
    ("BOUCLIER FISCAL CBAM 2026", "Protection des exportateurs algériens contre la surtaxation punitive de l'Union Européenne.", NAVY),
    ("CONFORMITÉ INDUSTRIELLE", "Rapports automatisés conformes ISO 14064, GHG Protocol, OGMP 2.0 et API 2021 Compendium.", EMERALD)
]

for i, (title, desc, color) in enumerate(cards_data):
    left = Inches(1.0 + i * 3.9)
    card = add_card(s2, left, Inches(3.9), Inches(3.55), Inches(2.9), bg_color=CARD_BG, border_color=color)
    
    tb_c = s2.shapes.add_textbox(left + Inches(0.2), Inches(4.1), Inches(3.15), Inches(2.5))
    tf_c = tb_c.text_frame
    tf_c.word_wrap = True
    
    p = tf_c.paragraphs[0]
    p.text = title
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_desc = tf_c.add_paragraph()
    p_desc.text = desc
    p_desc.font.name = "Arial"
    p_desc.font.size = Pt(11)
    p_desc.font.color.rgb = TEXT_DARK
    p_desc.space_before = Pt(14)

# ==========================================
# SLIDE 3: INFORMATIONS DE CONTACT
# ==========================================
s3 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s3, "INFORMATIONS DE CONTACT", "1. PRÉSENTATION GÉNÉRALE")

card_contact = add_card(s3, Inches(1.2), Inches(1.5), Inches(10.9), Inches(5.2), bg_color=WHITE, border_color=CARD_BORDER)

tb_c = s3.shapes.add_textbox(Inches(1.8), Inches(1.8), Inches(9.8), Inches(4.6))
tf_c = tb_c.text_frame
tf_c.word_wrap = True

p = tf_c.paragraphs[0]
p.text = "• INFORMATIONS DE CONTACT DU PROJET"
p.font.name = "Arial"
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = NAVY

contacts = [
    ("Nom(s) du / des responsable(s) :", "[Nom et Prénom du Porteur de Projet / Équipe Fondatrice]"),
    ("Fonction / Rôle :", "Fondateur & Lead Ingénierie Carbone / Développeur Principal"),
    ("Email Professionnel :", "contact@carbontech-dz.com / [Email du Porteur]"),
    ("Numéro de Téléphone :", "+213 (0) [Numéro de Téléphone Professionnel]"),
    ("Site Web (SaaS Prototype) :", "https://carbontech.dz (Plateforme Web Opérationnelle)"),
    ("Localisation & Écosystème :", "Alger / Cyberparc de Sidi Abdellah, Algérie"),
    ("Réseaux Professionnels :", "linkedin.com/company/carbontech-algeria")
]

for label, val in contacts:
    p_row = tf_c.add_paragraph()
    p_row.space_before = Pt(12)
    run1 = p_row.add_run()
    run1.text = f"{label} "
    run1.font.bold = True
    run1.font.size = Pt(13)
    run1.font.color.rgb = DARK_NAVY
    
    run2 = p_row.add_run()
    run2.text = val
    run2.font.bold = False
    run2.font.size = Pt(13)
    run2.font.color.rgb = TEXT_MUTED if "[" in val else TEAL

# ==========================================
# SLIDE 4: RÉSUMÉ DU PROJET - LE PROBLÈME
# ==========================================
s4 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s4, "RÉSUMÉ DU PROJET", "1. RÉSUMÉ DU PROJET")

# Top Narrative Card
top_narrative = add_card(s4, Inches(1.0), Inches(1.3), Inches(11.333), Inches(2.2), bg_color=CARD_BG, border_color=CARD_BORDER)
tb_n = s4.shapes.add_textbox(Inches(1.3), Inches(1.45), Inches(10.7), Inches(1.9))
tf_n = tb_n.text_frame
tf_n.word_wrap = True

p = tf_n.paragraphs[0]
p.text = "Les industries font face à des réglementations de plus en plus exigeantes (MACF / CBAM, ISO 14064, GHG Protocol, ETS, OGMP 2.0) mais continuent de calculer leurs émissions à l'aide de feuilles Excel manuelles ou de logiciels généralistes reposant sur des facteurs par défaut."
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.color.rgb = TEXT_DARK
p.font.bold = True

p2 = tf_n.add_paragraph()
p2.text = "Ces approches imprécises produisent des estimations très éloignées de la réalité opérationnelle des usines, entraînant des erreurs massives de déclaration, des surtaxes douanières exorbitantes et des sanctions réglementaires."
p2.font.name = "Arial"
p2.font.size = Pt(12)
p2.font.color.rgb = RED_ACCENT
p2.space_before = Pt(8)

# Bottom 4 limit boxes
limits = [
    ("Facteurs Génériques", "Utilisent des facteurs moyens internationaux inadaptés au mix gaz algérien.", RED_ACCENT),
    ("Aucune Modélisation", "Ne modélisent ni les bilans matière/énergie, ni la thermodynamique des équipements.", AMBER),
    ("Non Spécifique", "Ne prennent pas en compte les paramètres réels des installations (brûleurs, torchères).", DARK_NAVY),
    ("Manque de Transparence", "Offrent peu de traçabilité, rendant l'audit CBAM impossible ou rejetable.", NAVY)
]

for i, (title, desc, color) in enumerate(limits):
    left = Inches(1.0 + i * 2.92)
    add_card(s4, left, Inches(3.8), Inches(2.65), Inches(3.0), bg_color=WHITE, border_color=color)
    tb_l = s4.shapes.add_textbox(left + Inches(0.15), Inches(4.0), Inches(2.35), Inches(2.6))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    
    p = tf_l.paragraphs[0]
    p.text = f"• {title}"
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_desc = tf_l.add_paragraph()
    p_desc.text = desc
    p_desc.font.name = "Arial"
    p_desc.font.size = Pt(10.5)
    p_desc.font.color.rgb = TEXT_DARK
    p_desc.space_before = Pt(10)

# ==========================================
# SLIDE 5: RÉSUMÉ DU PROJET - LA SOLUTION
# ==========================================
s5 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s5, "RÉSUMÉ DU PROJET", "1. RÉSUMÉ DU PROJET")

# Solution Introduction
add_card(s5, Inches(1.0), Inches(1.3), Inches(11.333), Inches(1.8), bg_color=CARD_BG, border_color=TEAL)
tb_s = s5.shapes.add_textbox(Inches(1.3), Inches(1.45), Inches(10.7), Inches(1.5))
tf_s = tb_s.text_frame
tf_s.word_wrap = True

p = tf_s.paragraphs[0]
p.text = "Carbon Tech est une plateforme SaaS d'ingénierie carbone qui calcule les émissions de GES à partir des DONNÉES RÉELLES des procédés industriels."
p.font.name = "Arial"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = DARK_NAVY

p2 = tf_s.add_paragraph()
p2.text = "Contrairement aux plateformes ESG classiques de simple reporting, Carbon Tech applique des modèles d'ingénierie physique et chimique avancés adaptés à chaque typologie d'industrie lourde."
p2.font.name = "Arial"
p2.font.size = Pt(12)
p2.font.color.rgb = NAVY
p2.space_before = Pt(6)

# 4 Engineering pillars
pillars = [
    ("Bilans Matière & Énergie", "Calcul dynamique des flux thermiques, bilans massiques et stœchiométrie des réactions."),
    ("Paramètres des Équipements", "Efficacité de combustion, débits réels, pression, température et cinétique de torchage."),
    ("Compositions Chimiques", "Intégration directe des analyses chromatographiques du gaz naturel et combustibles."),
    ("Facteurs Propres au Site", "Application de facteurs Tier 3 mesurés avec repli automatique sur standards API 2021.")
]

for i, (title, desc) in enumerate(pillars):
    col = i % 2
    row = i // 2
    left = Inches(1.0 + col * 5.8)
    top = Inches(3.4 + row * 1.8)
    add_card(s5, left, top, Inches(5.5), Inches(1.55), bg_color=WHITE, border_color=CARD_BORDER)
    
    tb_p = s5.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), Inches(5.1), Inches(1.25))
    tf_p = tb_p.text_frame
    tf_p.word_wrap = True
    
    p = tf_p.paragraphs[0]
    p.text = f"✓  {title}"
    p.font.name = "Arial"
    p.font.size = Pt(12.5)
    p.font.bold = True
    p.font.color.rgb = TEAL
    
    p_desc = tf_p.add_paragraph()
    p_desc.text = desc
    p_desc.font.name = "Arial"
    p_desc.font.size = Pt(11)
    p_desc.font.color.rgb = TEXT_DARK
    p_desc.space_before = Pt(4)

# ==========================================
# SLIDE 6: LES 3 PILIERS CLÉS
# ==========================================
s6 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s6, "RÉSUMÉ DU PROJET", "1. RÉSUMÉ DU PROJET")

cards_piliers = [
    ("PRÉCISION", "Modèles adaptés au procédé\net à la composition réelle", [
        "Calculs physiques Tier 3",
        "Stœchiométrie & Bilan matière",
        "Analyse d'incertitude Monte Carlo"
    ], TEAL),
    ("CONFORMITÉ", "ISO 14064 • GHG Protocol\nMACF / CBAM • MRV", [
        "Scope 1, Scope 2, Scope 3",
        "Dossiers douaniers CBAM XML",
        "Traçabilité prête pour l'audit"
    ], NAVY),
    ("INDUSTRIALISATION", "SaaS Cloud & On-Premise\nMulti-sites • Audit Trail", [
        "Gestion multi-installations",
        "Piste d'audit immuable",
        "Exports automatisés PDF/Excel"
    ], EMERALD)
]

for i, (title, subtitle, bullets, color) in enumerate(cards_piliers):
    left = Inches(1.0 + i * 3.9)
    add_card(s6, left, Inches(1.8), Inches(3.55), Inches(4.8), bg_color=CARD_BG, border_color=color)
    
    tb_card = s6.shapes.add_textbox(left + Inches(0.2), Inches(2.1), Inches(3.15), Inches(4.2))
    tf_card = tb_card.text_frame
    tf_card.word_wrap = True
    
    p = tf_card.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Arial"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_sub = tf_card.add_paragraph()
    p_sub.text = subtitle
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = DARK_NAVY
    p_sub.font.bold = True
    p_sub.space_before = Pt(8)
    
    for b in bullets:
        pb = tf_card.add_paragraph()
        pb.text = f"•  {b}"
        pb.font.name = "Arial"
        pb.font.size = Pt(11)
        pb.font.color.rgb = TEXT_DARK
        pb.space_before = Pt(12)

# ==========================================
# SLIDE 7: PRÉSENTATION DE L'ÉQUIPE
# ==========================================
s7 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s7, "PRÉSENTATION DE L'ÉQUIPE", "1. PRÉSENTATION DE L'ÉQUIPE")

roles = [
    ("Nom de la personne 1", "Lead Ingénierie Carbone & Procédés", "Expert thermodynamique industrielle, modélisation des émissions & bilans matière."),
    ("Nom de la personne 2", "CTO & Architecte Logiciel SaaS", "Ingénieur Cloud & Sécurité, calcul distribué et architecture applicative moderne."),
    ("Nom de la personne 3", "Responsable Réglementation CBAM & ISO", "Spécialiste conformité internationale MACF, MRV et audits environnementaux."),
    ("Nom de la personne 4", "Lead Business Dev & Partenariats", "Déploiement commercial grands comptes, relations secteur industriel & institutionnel.")
]

for i, (name, role, skills) in enumerate(roles):
    left = Inches(0.9 + i * 2.95)
    # Photo placeholder
    photo_box = add_card(s7, left, Inches(1.5), Inches(2.65), Inches(2.2), bg_color=CARD_BG, border_color=CARD_BORDER)
    tb_ph = s7.shapes.add_textbox(left + Inches(0.1), Inches(2.2), Inches(2.45), Inches(0.8))
    p = tb_ph.text_frame.paragraphs[0]
    p.text = "[ Photo Membre ]"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED

    # Info Box
    info_box = add_card(s7, left, Inches(3.9), Inches(2.65), Inches(2.9), bg_color=WHITE, border_color=NAVY)
    tb_inf = s7.shapes.add_textbox(left + Inches(0.15), Inches(4.0), Inches(2.35), Inches(2.7))
    tf_inf = tb_inf.text_frame
    tf_inf.word_wrap = True
    
    p = tf_inf.paragraphs[0]
    p.text = name
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = DARK_NAVY
    
    p_r = tf_inf.add_paragraph()
    p_r.text = role
    p_r.font.name = "Arial"
    p_r.font.size = Pt(10.5)
    p_r.font.bold = True
    p_r.font.color.rgb = TEAL
    p_r.space_before = Pt(4)
    
    p_s = tf_inf.add_paragraph()
    p_s.text = skills
    p_s.font.name = "Arial"
    p_s.font.size = Pt(9.5)
    p_s.font.color.rgb = TEXT_DARK
    p_s.space_before = Pt(8)

# ==========================================
# SLIDE 8: PROBLÉMATIQUE CIBLÉE (WITH EMISSIONS CHART)
# ==========================================
s8 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s8, "PROBLÉMATIQUE CIBLÉE", "1. PROBLÉMATIQUE CIBLÉE")

# Left Column (Limits & Consequences)
left_card = add_card(s8, Inches(0.8), Inches(1.3), Inches(4.8), Inches(5.6), bg_color=WHITE, border_color=CARD_BORDER)
tb_prob = s8.shapes.add_textbox(Inches(1.0), Inches(1.45), Inches(4.4), Inches(5.3))
tf_prob = tb_prob.text_frame
tf_prob.word_wrap = True

p = tf_prob.paragraphs[0]
p.text = "QUEL EST LE PROBLÈME IDENTIFIÉ ?"
p.font.name = "Arial"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = RED_ACCENT

p_sub = tf_prob.add_paragraph()
p_sub.text = "Les industriels manquent d'outils adaptés :"
p_sub.font.bold = True
p_sub.font.size = Pt(11)
p_sub.font.color.rgb = DARK_NAVY
p_sub.space_before = Pt(6)

limits_text = [
    "Calculs manuels & fichiers Excel dispersés",
    "Risques majeurs d'erreurs et de non-conformité",
    "Absence totale de traçabilité et d'automatisation",
    "Logiciels ESG incapables de modéliser les usines"
]
for item in limits_text:
    pi = tf_prob.add_paragraph()
    pi.text = f"✗  {item}"
    pi.font.size = Pt(10)
    pi.font.color.rgb = TEXT_DARK
    pi.space_before = Pt(3)

p_cons = tf_prob.add_paragraph()
p_cons.text = "Conséquences Financières & Réglementaires :"
p_cons.font.bold = True
p_cons.font.size = Pt(11)
p_cons.font.color.rgb = RED_ACCENT
p_cons.space_before = Pt(10)

cons_text = [
    "Surtaxation CBAM massive par défaut (+35%)",
    "Fuite de devises et perte de marges à l'export",
    "Risque d'amendes de 10€ à 50€/t de CO2",
    "Surcoût exorbitant des audits externes ponctuels"
]
for item in cons_text:
    pi = tf_prob.add_paragraph()
    pi.text = f"⚠  {item}"
    pi.font.size = Pt(10)
    pi.font.color.rgb = RED_ACCENT
    pi.space_before = Pt(3)

# Right Column (Embed chart_industry_emissions.png)
chart_emissions_path = os.path.join(ASSETS_DIR, "chart_industry_emissions.png")
if os.path.exists(chart_emissions_path):
    s8.shapes.add_picture(chart_emissions_path, Inches(5.8), Inches(1.3), Inches(6.8), Inches(5.6))

# ==========================================
# SLIDE 9: LA SOLUTION PROPOSÉE
# ==========================================
s9 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s9, "LA SOLUTION PROPOSÉE", "1. LA SOLUTION PROPOSÉE")

# Subtitle description
tb_sol_header = s9.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.8))
tf_sh = tb_sol_header.text_frame
tf_sh.word_wrap = True
p = tf_sh.paragraphs[0]
p.text = "Une solution d'ingénierie physique alliant précision scientifique, automatisation SaaS et conformité légale."
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = DARK_NAVY

# Left box: Originalité
card_orig = add_card(s9, Inches(0.8), Inches(1.9), Inches(5.7), Inches(5.0), bg_color=CARD_BG, border_color=TEAL)
tb_orig = s9.shapes.add_textbox(Inches(1.0), Inches(2.1), Inches(5.3), Inches(4.6))
tf_orig = tb_orig.text_frame
tf_orig.word_wrap = True

p = tf_orig.paragraphs[0]
p.text = "ORIGINALITÉ TECHNOLOGIQUE"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = TEAL

orig_points = [
    ("Moteur de Calcul Stœchiométrique", "Modélise les réactions chimiques directes (décarbonatation du calcaire dans le ciment, réduction de fer au gaz naturel DRI)."),
    ("Intégration API 2021 Compendium", "Standard mondial d'ingénierie pour le torchage, les évents et les émissions fugitives de gaz."),
    ("Propagation d'Incertitude", "Intègre un module statistique (Monte Carlo) attestant la rigueur des données déclarées aux auditeurs."),
    ("Adaptation au Gaz Algérien", "Calcul exact basé sur le pouvoir calorifique et la composition chromatographique locale.")
]
for title, desc in orig_points:
    p_t = tf_orig.add_paragraph()
    p_t.text = f"★  {title}"
    p_t.font.bold = True
    p_t.font.size = Pt(11)
    p_t.font.color.rgb = DARK_NAVY
    p_t.space_before = Pt(8)
    
    p_d = tf_orig.add_paragraph()
    p_d.text = desc
    p_d.font.size = Pt(9.5)
    p_d.font.color.rgb = TEXT_DARK
    p_d.space_before = Pt(2)

# Right box: Efficacité
card_eff = add_card(s9, Inches(6.8), Inches(1.9), Inches(5.7), Inches(5.0), bg_color=WHITE, border_color=NAVY)
tb_eff = s9.shapes.add_textbox(Inches(7.0), Inches(2.1), Inches(5.3), Inches(4.6))
tf_eff = tb_eff.text_frame
tf_eff.word_wrap = True

p = tf_eff.paragraphs[0]
p.text = "EFFICACITÉ OPÉRATIONNELLE & GAINS"
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = NAVY

eff_points = [
    ("Génération CBAM XML en 1 Clic", "Automatise la création des fichiers officiels de déclaration douanière européenne sans ressaisie manuelle."),
    ("Réduction de 80% du Temps d'Audit", "L'Audit Trail complet retrace chaque paramètre source, accélérant la vérification par les tiers accrédités."),
    ("Économies Fiscale Immédiates", "Prouve l'empreinte carbone réelle plus basse de l'Algérie, évitant les pénalités forfaitaires de l'UE."),
    ("Plateforme Souveraine et Sécurisée", "Protection intégrale du secret industriel et des données stratégiques nationales.")
]
for title, desc in eff_points:
    p_t = tf_eff.add_paragraph()
    p_t.text = f"✔  {title}"
    p_t.font.bold = True
    p_t.font.size = Pt(11)
    p_t.font.color.rgb = NAVY
    p_t.space_before = Pt(8)
    
    p_d = tf_eff.add_paragraph()
    p_d.text = desc
    p_d.font.size = Pt(9.5)
    p_d.font.color.rgb = TEXT_DARK
    p_d.space_before = Pt(2)

# ==========================================
# SLIDE 10: PRÉSENTATION DU PROTOTYPE (WITH LIVE SCREENSHOTS)
# ==========================================
s10 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s10, "PRÉSENTATION DU PROTOTYPE (PRODUIT/SERVICE)", "1. PRÉSENTATION DU PROTOTYPE (PRODUIT/SERVICE)")

# Top 3 links boxes
boxes = [
    ("1", "VIDÉO DÉMONSTRATION", "Lien vers la vidéo de démonstration\nde 4 minutes du logiciel fonctionnel.", TEAL),
    ("2", "ACCÈS SAAS PROTOTYPE", "Accès direct à la plateforme web live :\nhttps://carbontech.dz / Démo Interactive.", NAVY),
    ("3", "DOCUMENTATION & API", "Dossier technique d'architecture,\nmoteurs de calcul & API Swagger.", DARK_NAVY)
]

for i, (num, title, desc, color) in enumerate(boxes):
    left = Inches(0.8 + i * 3.95)
    add_card(s10, left, Inches(1.3), Inches(3.75), Inches(1.6), bg_color=CARD_BG, border_color=color)
    tb_b = s10.shapes.add_textbox(left + Inches(0.15), Inches(1.35), Inches(3.45), Inches(1.5))
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True
    
    p = tf_b.paragraphs[0]
    p.text = f"{num}. {title}"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_d = tf_b.add_paragraph()
    p_d.text = desc
    p_d.font.size = Pt(9.5)
    p_d.font.color.rgb = TEXT_DARK
    p_d.space_before = Pt(4)

# Bottom: Embed Live Software Screenshots
ui_dash_path = os.path.join(ASSETS_DIR, "ui_dashboard.png")
ui_rep_path = os.path.join(ASSETS_DIR, "ui_reports.png")

if os.path.exists(ui_dash_path):
    s10.shapes.add_picture(ui_dash_path, Inches(0.8), Inches(3.1), Inches(5.7), Inches(3.8))
    # Caption
    tb_cap1 = s10.shapes.add_textbox(Inches(0.8), Inches(6.92), Inches(5.7), Inches(0.4))
    p = tb_cap1.text_frame.paragraphs[0]
    p.text = "Figure 1 : Tableau de bord exécutif multi-sites & intensité carbone réelle"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(8.5)
    p.font.bold = True
    p.font.color.rgb = DARK_NAVY

if os.path.exists(ui_rep_path):
    s10.shapes.add_picture(ui_rep_path, Inches(6.8), Inches(3.1), Inches(5.7), Inches(3.8))
    # Caption
    tb_cap2 = s10.shapes.add_textbox(Inches(6.8), Inches(6.92), Inches(5.7), Inches(0.4))
    p = tb_cap2.text_frame.paragraphs[0]
    p.text = "Figure 2 : Module de génération automatisée des rapports CBAM & ISO 14064"
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(8.5)
    p.font.bold = True
    p.font.color.rgb = DARK_NAVY

# ==========================================
# SLIDE 11: PROPRIÉTÉ INTELLECTUELLE
# ==========================================
s11 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s11, "BREVETS, MARQUES ET DROITS DE PROPRIÉTÉ INTELLECTUELLE", "1. BREVETS, MARQUES ET DROITS DE PROPRIÉTÉ INTELLECTUELLE")

ip_cards = [
    ("MARQUES & DESIGN ENREGISTRÉS", "Protection de la Marque & Identité", [
        "Marque déposée 'Carbon Tech™' auprès de l'INAPI (Algérie).",
        "Dépôt de la charte graphique et des modèles d'interface utilisateur.",
        "Protection du nom de domaine national stratégique .DZ."
    ], TEAL),
    ("DROITS D'AUTEUR & CODE SOURCE", "Protection du Logiciel & Algorithmes", [
        "Dépôt du code source propriétaire auprès de l'ONDA (Algérie).",
        "Algorithmes d'optimisation de calcul d'ingénierie Tier 3 sous licence fermée.",
        "Architecture modulaire de micro-calculateurs industriels propriétaires."
    ], NAVY),
    ("SAVOIR-FAIRE & BASE FACTEURS", "Secret Industriel & Données Procédés", [
        "Base de données propriétaire de facteurs d'émission spécifiques au gaz naturel algérien.",
        "Modèles stœchiométriques calibrés sur les installations sidérurgiques et cimentières locales.",
        "Accords de confidentialité stricts (NDA) sur les données d'usines clientes."
    ], EMERALD)
]

for i, (title, subtitle, bullets, color) in enumerate(ip_cards):
    left = Inches(0.9 + i * 3.95)
    add_card(s11, left, Inches(1.6), Inches(3.65), Inches(5.1), bg_color=CARD_BG, border_color=color)
    
    tb_ip = s11.shapes.add_textbox(left + Inches(0.2), Inches(1.8), Inches(3.25), Inches(4.6))
    tf_ip = tb_ip.text_frame
    tf_ip.word_wrap = True
    
    p = tf_ip.paragraphs[0]
    p.text = title
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_s = tf_ip.add_paragraph()
    p_s.text = subtitle
    p_s.font.size = Pt(11)
    p_s.font.bold = True
    p_s.font.color.rgb = DARK_NAVY
    p_s.space_before = Pt(6)
    
    for b in bullets:
        pb = tf_ip.add_paragraph()
        pb.text = f"•  {b}"
        pb.font.size = Pt(10)
        pb.font.color.rgb = TEXT_DARK
        pb.space_before = Pt(10)

# ==========================================
# SLIDE 12: VALEUR AJOUTÉE (WITH CBAM SAVINGS CHART)
# ==========================================
s12 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s12, "VALEUR AJOUTÉE", "1. VALEUR AJOUTÉE")

# Left Column (3 Pillars)
left_card = add_card(s12, Inches(0.8), Inches(1.3), Inches(4.9), Inches(5.6), bg_color=WHITE, border_color=CARD_BORDER)
tb_val = s12.shapes.add_textbox(Inches(1.0), Inches(1.45), Inches(4.5), Inches(5.3))
tf_val = tb_val.text_frame
tf_val.word_wrap = True

p = tf_val.paragraphs[0]
p.text = "CE QUE NOUS APPORTONS AUX INDUSTRIELS :"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = NAVY

pillars_val = [
    ("ÉCONOMIE FISCALE & DEVISES", "-30% à -45% de taxe carbone CBAM en prouvant les émissions réelles plutôt que d'accepter les pénalités par défaut de l'UE.", TEAL),
    ("INNOVATION SCIENTIFIQUE", "Premier moteur de calcul d'ingénierie Tier 3 d'Algérie avec bilan matière, stœchiométrie et analyse d'incertitude.", DARK_NAVY),
    ("IMPACT & SOUVERAINETÉ", "Protection directe de la compétitivité internationale de nos exportations d'acier, ciment et engrais vers l'Europe.", EMERALD)
]

for title, desc, col in pillars_val:
    pt = tf_val.add_paragraph()
    pt.text = f"★  {title}"
    pt.font.bold = True
    pt.font.size = Pt(11)
    pt.font.color.rgb = col
    pt.space_before = Pt(12)
    
    pd = tf_val.add_paragraph()
    pd.text = desc
    pd.font.size = Pt(9.8)
    pd.font.color.rgb = TEXT_DARK
    pd.space_before = Pt(3)

# Right Column (Embed chart_cbam_savings.png)
chart_savings_path = os.path.join(ASSETS_DIR, "chart_cbam_savings.png")
if os.path.exists(chart_savings_path):
    s12.shapes.add_picture(chart_savings_path, Inches(5.9), Inches(1.3), Inches(6.7), Inches(5.6))

# ==========================================
# SLIDE 13: ANALYSE CONCURRENTIELLE (WITH MATRIX CHART)
# ==========================================
s13 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s13, "ANALYSE CONCURRENTIELLE", "1. ANALYSE CONCURRENTIELLE")

# Left text box
card_comp = add_card(s13, Inches(0.8), Inches(1.3), Inches(4.9), Inches(5.6), bg_color=CARD_BG, border_color=CARD_BORDER)
tb_c = s13.shapes.add_textbox(Inches(1.0), Inches(1.45), Inches(4.5), Inches(5.3))
tf_c = tb_c.text_frame
tf_c.word_wrap = True

p = tf_c.paragraphs[0]
p.text = "BENCHMARK DE LA CONCURRENCE :"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = DARK_NAVY

comp_points = [
    ("Feuilles Excel Internes (85%)", "Calculs manuels, zéro traçabilité, erreurs fréquentes (>40%), rejet systématique en audit CBAM strict."),
    ("Logiciels ESG Occidentaux", "(Sweep, Greenly, EcoVadis) : Très chers en devises, focalisés sur le tertiaire, incapables de modéliser l'ingénierie lourde."),
    ("Cabinets d'Audit (PwC, EY)", "Prestations ponctuelles statiques, honoraires très élevés, absence de plateforme continue."),
    ("Notre Différenciation Unique", "SaaS continu + Ingénierie Tier 3 + Coût compétitif en DZD + Souveraineté des données.")
]

for title, desc in comp_points:
    pt = tf_c.add_paragraph()
    pt.text = f"•  {title}"
    pt.font.bold = True
    pt.font.size = Pt(10.5)
    pt.font.color.rgb = TEAL if "Différenciation" in title else DARK_NAVY
    pt.space_before = Pt(8)
    
    pd = tf_c.add_paragraph()
    pd.text = desc
    pd.font.size = Pt(9.2)
    pd.font.color.rgb = TEXT_DARK
    pd.space_before = Pt(2)

# Right Column (Embed chart_competitive_matrix.png)
chart_matrix_path = os.path.join(ASSETS_DIR, "chart_competitive_matrix.png")
if os.path.exists(chart_matrix_path):
    s13.shapes.add_picture(chart_matrix_path, Inches(5.9), Inches(1.3), Inches(6.7), Inches(5.6))

# ==========================================
# SLIDE 14: ANALYSE SWOT
# ==========================================
s14 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s14, "ANALYSE CONCURRENTIELLE (SWOT)", "1. ANALYSE CONCURRENTIELLE")

swot = [
    ("FORCES (STRENGTHS)", [
        "Moteur d'ingénierie Tier 3 ultra précis",
        "Conformité native CBAM, ISO 14064, API 2021",
        "Facturation en Dinar Algérien (DZD)",
        "Hébergement souverain des données industrielles"
    ], TEAL),
    ("FAIBLESSES (WEAKNESSES)", [
        "Jeune entreprise en phase de labellisation",
        "Cycle de vente B2B industriel (3 à 6 mois)",
        "Nécessite une sensibilisation des directeurs d'usine"
    ], AMBER),
    ("OPPORTUNITÉS (OPPORTUNITIES)", [
        "Taxe CBAM obligatoire en 2026 pour l'acier, ciment, engrais",
        "Objectifs nationaux de réduction du torchage Sonatrach",
        "Absence de concurrent direct spécialisé en Algérie",
        "Expansion naturelle vers le Maghreb et la zone MENA"
    ], EMERALD),
    ("MENACES (THREATS)", [
        "Évolution rapide des exigences réglementaires européennes",
        "Résistance au changement et inertie des fichiers Excel",
        "Arrivée potentielle d'acteurs internationaux avec des filiales"
    ], RED_ACCENT)
]

for i, (title, bullets, color) in enumerate(swot):
    col = i % 2
    row = i // 2
    left = Inches(0.9 + col * 5.8)
    top = Inches(1.4 + row * 2.8)
    add_card(s14, left, top, Inches(5.6), Inches(2.6), bg_color=WHITE, border_color=color)
    
    tb_sw = s14.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), Inches(5.2), Inches(2.3))
    tf_sw = tb_sw.text_frame
    tf_sw.word_wrap = True
    
    p = tf_sw.paragraphs[0]
    p.text = title
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = color
    
    for b in bullets:
        pb = tf_sw.add_paragraph()
        pb.text = f"•  {b}"
        pb.font.size = Pt(10)
        pb.font.color.rgb = TEXT_DARK
        pb.space_before = Pt(4)

# ==========================================
# SLIDE 15: ANALYSE DU MARCHÉ CIBLE (WITH MARKET SIZING CHART)
# ==========================================
s15 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s15, "ANALYSE DU MARCHÉ CIBLE", "1. ANALYSE DU MARCHÉ CIBLE")

# Left Column (Clients & Beneficiaries)
left_card = add_card(s15, Inches(0.8), Inches(1.3), Inches(4.9), Inches(5.6), bg_color=CARD_BG, border_color=CARD_BORDER)
tb_m = s15.shapes.add_textbox(Inches(1.0), Inches(1.45), Inches(4.5), Inches(5.3))
tf_m = tb_m.text_frame
tf_m.word_wrap = True

p = tf_m.paragraphs[0]
p.text = "SEGMENTATION DU MARCHÉ CIBLE :"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = DARK_NAVY

segments = [
    ("Exportateurs CBAM Clés", "Aciéries DRI (Tosyali, AQS), Cimenteries (GICA, Lafarge), Complexes d'Engrais Azotés (Fertial, Sorfert)."),
    ("Secteur Énergie & Hydrocarbures", "Sonatrach (Amont gazier, raffinage, réduction du torchage & méthane) et Sonelgaz."),
    ("Utilisateurs Directs", "Directeurs d'Usine, Responsables HSE/RSE, Ingénieurs Procédés, Auditeurs carbone."),
    ("Bénéficiaires Économiques", "Directions Générales & Financières (préservation des marges et accès garanti à l'UE).")
]

for title, desc in segments:
    pt = tf_m.add_paragraph()
    pt.text = f"■  {title}"
    pt.font.bold = True
    pt.font.size = Pt(10.5)
    pt.font.color.rgb = NAVY
    pt.space_before = Pt(8)
    
    pd = tf_m.add_paragraph()
    pd.text = desc
    pd.font.size = Pt(9.2)
    pd.font.color.rgb = TEXT_DARK
    pd.space_before = Pt(2)

# Right Column (Embed chart_market_sizing.png)
chart_market_path = os.path.join(ASSETS_DIR, "chart_market_sizing.png")
if os.path.exists(chart_market_path):
    s15.shapes.add_picture(chart_market_path, Inches(5.9), Inches(1.3), Inches(6.7), Inches(5.6))

# ==========================================
# SLIDE 16: MODÈLE ÉCONOMIQUE (BUSINESS MODEL)
# ==========================================
s16 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s16, "MODÈLE ÉCONOMIQUE (BUSINESS MODEL)", "1. MODÈLE ÉCONOMIQUE (BUSINESS MODEL)")

tb_bm_top = s16.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(11.7), Inches(0.6))
p = tb_bm_top.text_frame.paragraphs[0]
p.text = "Modèle B2B SaaS par abonnement annuel récurrent (ARR) + Modules d'ingénierie d'onboarding à haute valeur ajoutée."
p.font.size = Pt(12)
p.font.bold = True
p.font.color.rgb = DARK_NAVY

# 3 Pricing Tiers Cards
tiers = [
    ("STARTER PME", "850 000 DZD / an", "Pour PME industrielle locale", [
        "1 Site industriel",
        "Calculs Scope 1 & Scope 2",
        "Facteurs standards & API",
        "Rapports ISO 14064 PDF",
        "Support technique standard"
    ], DARK_NAVY),
    ("ENTERPRISE CBAM", "2 400 000 DZD / an", "Pour exportateur majeur vers l'UE", [
        "Jusqu'à 3 Sites / Usines",
        "Moteur Tier 3 complet (Procédés)",
        "Module CBAM XML officiel",
        "Analyse d'incertitude Monte Carlo",
        "Piste d'audit illimitée"
    ], TEAL),
    ("CORPORATE / GROUPE", "Sur Devis (10M+ DZD)", "Pour grands groupes (Sonatrach, GICA)", [
        "Multi-sites illimité",
        "Déploiement Cloud souverain / On-Prem",
        "Intégration API / SCADA / ERP",
        "Module Methane OGMP 2.0 Niveau 5",
        "Account Manager dédié 24/7"
    ], NAVY)
]

for i, (name, price, sub, features, color) in enumerate(tiers):
    left = Inches(0.8 + i * 3.95)
    add_card(s16, left, Inches(1.9), Inches(3.75), Inches(4.9), bg_color=WHITE, border_color=color)
    
    tb_t = s16.shapes.add_textbox(left + Inches(0.2), Inches(2.05), Inches(3.35), Inches(4.6))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    
    p = tf_t.paragraphs[0]
    p.text = name
    p.alignment = PP_ALIGN.CENTER
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_pr = tf_t.add_paragraph()
    p_pr.text = price
    p_pr.alignment = PP_ALIGN.CENTER
    p_pr.font.size = Pt(13)
    p_pr.font.bold = True
    p_pr.font.color.rgb = DARK_NAVY
    p_pr.space_before = Pt(4)
    
    p_s = tf_t.add_paragraph()
    p_s.text = sub
    p_s.alignment = PP_ALIGN.CENTER
    p_s.font.size = Pt(9)
    p_s.font.color.rgb = TEXT_MUTED
    p_s.space_before = Pt(2)
    
    for f in features:
        pf = tf_t.add_paragraph()
        pf.text = f"✔  {f}"
        pf.font.size = Pt(10)
        pf.font.color.rgb = TEXT_DARK
        pf.space_before = Pt(8)

# ==========================================
# SLIDE 17: ROADMAP DU PROJET (6 MOIS, 1 AN, 3 ANS)
# ==========================================
s17 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s17, "ROADMAP DU PROJET ET STRATÉGIE DE DÉVELOPPEMENT", "1. ROADMAP DU PROJET ET STRATÉGIE DE DÉVELOPPEMENT")

roadmap = [
    ("1", "PHASE 1 : 0 À 6 MOIS", "Labellisation & Pilotes Industriels", [
        "Obtention du Label 'Projet Innovant' / 'Startup'.",
        "Déploiement pilote sur 2 sites majeurs (1 cimenterie GICA + 1 complexe sidérurgique).",
        "Validation de la conformité des exports CBAM auprès d'un vérificateur accrédité."
    ], TEAL),
    ("2", "PHASE 2 : 6 MOIS À 1 AN", "Commercialisation Nationale", [
        "Déploiement commercial auprès de 15 sites industriels exportateurs clés en Algérie.",
        "Intégration de connecteurs automatisés IoT / SCADA pour les usines modernes.",
        "Atteinte de l'équilibre financier (Break-even opérationnel)."
    ], NAVY),
    ("3", "PHASE 3 : 1 AN À 3 ANS", "Expansion Régionale & Scaling", [
        "Extension de la solution au Maghreb (Tunisie, Maroc) et Moyen-Orient (Égypte, CCG).",
        "Lancement du module d'optimisation d'investissements et trading de crédits carbone.",
        "Objectif : 35+ grands complexes industriels souscrits (3.2 M€ ARR)."
    ], DARK_NAVY)
]

for i, (num, phase, sub, milestones, color) in enumerate(roadmap):
    left = Inches(0.8 + i * 3.95)
    add_card(s17, left, Inches(1.5), Inches(3.75), Inches(5.3), bg_color=CARD_BG, border_color=color)
    
    tb_rm = s17.shapes.add_textbox(left + Inches(0.2), Inches(1.7), Inches(3.35), Inches(4.9))
    tf_rm = tb_rm.text_frame
    tf_rm.word_wrap = True
    
    p = tf_rm.paragraphs[0]
    p.text = f"{num}. {phase}"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_s = tf_rm.add_paragraph()
    p_s.text = sub
    p_s.font.size = Pt(11)
    p_s.font.bold = True
    p_s.font.color.rgb = DARK_NAVY
    p_s.space_before = Pt(4)
    
    for m in milestones:
        pm = tf_rm.add_paragraph()
        pm.text = f"•  {m}"
        pm.font.size = Pt(10)
        pm.font.color.rgb = TEXT_DARK
        pm.space_before = Pt(10)

# ==========================================
# SLIDE 18: RESSOURCES NÉCESSAIRES & STRATÉGIE
# ==========================================
s18 = prs.slides.add_slide(prs.slide_layouts[6])
add_header(s18, "ROADMAP DU PROJET ET STRATÉGIE DE DÉVELOPPEMENT", "1. ROADMAP DU PROJET ET STRATÉGIE DE DÉVELOPPEMENT")

resources = [
    ("RESSOURCES HUMAINES", "Équipe Clé à Renforcer", [
        "2 Ingénieurs Génie des Procédés / Thermodynamique.",
        "2 Développeurs Full-Stack / DevOps Cloud.",
        "1 Consultant Sénior en Réglementation MACF & Audits Carbone.",
        "1 Responsable Commercial Grands Comptes Industriels."
    ], TEAL),
    ("RESSOURCES TECHNIQUES", "Infrastructure & Certifications", [
        "Infrastructure Cloud souveraine certifiée hébergée en Algérie.",
        "Banc de validation et d'étalonnage des algorithmes stœchiométriques.",
        "Accréditation et partenariats avec les organismes de vérification (MRV).",
        "Connecteurs API sécurisés pour protocoles industriels (Modbus, OPC UA)."
    ], NAVY),
    ("RESSOURCES FINANCIÈRES", "Plan d'Allocation d'Amorçage", [
        "Besoin de financement initial : 12 000 000 DZD (Fonds ASF / Label Startup).",
        "45% : R&D, moteurs d'ingénierie et infrastructure sécurisée.",
        "35% : Déploiement terrain, onboarding des usines et pilotes.",
        "20% : Conformité légale, certifications ISO et marketing industriel."
    ], EMERALD)
]

for i, (title, sub, bullets, color) in enumerate(resources):
    left = Inches(0.8 + i * 3.95)
    add_card(s18, left, Inches(1.5), Inches(3.75), Inches(5.3), bg_color=WHITE, border_color=color)
    
    tb_res = s18.shapes.add_textbox(left + Inches(0.2), Inches(1.7), Inches(3.35), Inches(4.9))
    tf_res = tb_res.text_frame
    tf_res.word_wrap = True
    
    p = tf_res.paragraphs[0]
    p.text = title
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = color
    
    p_s = tf_res.add_paragraph()
    p_s.text = sub
    p_s.font.size = Pt(11)
    p_s.font.bold = True
    p_s.font.color.rgb = DARK_NAVY
    p_s.space_before = Pt(4)
    
    for b in bullets:
        pb = tf_res.add_paragraph()
        pb.text = f"•  {b}"
        pb.font.size = Pt(10)
        pb.font.color.rgb = TEXT_DARK
        pb.space_before = Pt(10)

# ==========================================
# SLIDE 19: MERCI POUR VOTRE ATTENTION
# ==========================================
s19 = prs.slides.add_slide(prs.slide_layouts[6])

# Decorative top line
top_line = s19.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.15))
top_line.fill.solid()
top_line.fill.fore_color.rgb = TEAL
top_line.line.fill.background()

tb19 = s19.shapes.add_textbox(Inches(1.2), Inches(1.6), Inches(10.9), Inches(4.8))
tf19 = tb19.text_frame
tf19.word_wrap = True

p = tf19.paragraphs[0]
p.text = "MERCI POUR VOTRE ATTENTION"
p.alignment = PP_ALIGN.CENTER
p.font.name = "Arial"
p.font.size = Pt(46)
p.font.bold = True
p.font.color.rgb = NAVY

p2 = tf19.add_paragraph()
p2.text = "CARBON TECH : Armer l'industrie algérienne pour conquérir les marchés internationaux dans un monde décarboné."
p2.alignment = PP_ALIGN.CENTER
p2.font.name = "Arial"
p2.font.size = Pt(15)
p2.font.bold = True
p2.font.color.rgb = TEAL
p2.space_before = Pt(16)

p3 = tf19.add_paragraph()
p3.text = "Questions & Réponses avec la Commission Nationale de Labellisation"
p3.alignment = PP_ALIGN.CENTER
p3.font.name = "Arial"
p3.font.size = Pt(13)
p3.font.color.rgb = DARK_NAVY
p3.font.bold = True
p3.space_before = Pt(25)

p4 = tf19.add_paragraph()
p4.text = "Email : contact@carbontech-dz.com  |  Web : https://carbontech.dz  |  Alger, Algérie"
p4.alignment = PP_ALIGN.CENTER
p4.font.name = "Arial"
p4.font.size = Pt(11.5)
p4.font.color.rgb = TEXT_MUTED
p4.space_before = Pt(15)

# Save presentation
OUTPUT_PPTX = r"c:\Users\samsung\Desktop\H2\CarbonTech_PitchDeck_StartupAlgeria.pptx"
prs.save(OUTPUT_PPTX)
print("Successfully generated PPTX at:", OUTPUT_PPTX)
