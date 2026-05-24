"""
Orchestrateur de build du site MesureChâssis.
Refactore les pages existantes + génère les nouvelles + sitemap/robots.
"""
import re
import shutil
import sys
import os
from pathlib import Path

# Ajoute le répertoire courant au PATH pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shared import render_header, render_footer, render_cookie_banner, render_fab_download, YEAR
from _new_pages import (
    make_cgu, make_cgv, make_cookies, make_faq, make_telecharger, make_404, make_about
)

SOURCE_DIR = Path("/app/claude_site")
OUTPUT_DIR = Path("/app/site_mesurechassis_final")


# ============================================================================
# Refactor d'une page existante : remplace header/footer + injecte cookie+fab
# ============================================================================
def refactor_existing(filename: str, active: str):
    """Refactore une page existante : remplace header & footer."""
    src = SOURCE_DIR / filename
    if not src.exists():
        print(f"  ⚠️  {filename} introuvable, skip")
        return
    html = src.read_text(encoding="utf-8")

    new_header = render_header(active).rstrip()
    new_footer = render_footer().rstrip()

    # 1. Remplace <header>...</header> s'il existe
    if "<header>" in html and "</header>" in html:
        html = re.sub(r"<header>.*?</header>", new_header, html, count=1, flags=re.DOTALL)
    else:
        # Pas de header : injecte juste après <body...>
        html = re.sub(r"(<body[^>]*>)", r"\1\n" + new_header, html, count=1)

    # 2. Remplace <footer>...</footer> s'il existe
    if "<footer>" in html and "</footer>" in html:
        html = re.sub(r"<footer>.*?</footer>", new_footer, html, count=1, flags=re.DOTALL)
    else:
        # Tente le pattern beta.html : <div class="footer-note">...
        if 'class="footer-note"' in html:
            html = re.sub(
                r'<div class="footer-note">.*?</div>',
                new_footer,
                html,
                count=1,
                flags=re.DOTALL,
            )
        else:
            # Sinon : injecte juste avant </body>
            html = html.replace("</body>", new_footer + "\n</body>", 1)

    # 3. Injecte cookie banner + FAB juste avant </body> (si pas déjà présent)
    if 'id="cookieBanner"' not in html:
        injection = render_cookie_banner() + render_fab_download()
        html = html.replace("</body>", injection + "\n</body>", 1)

    # 4. Mise à jour copyright 2025 → 2026
    html = html.replace("© 2025", f"© {YEAR}")
    html = html.replace("&copy; 2025", f"&copy; {YEAR}")

    # 5. Ajoute la balise <link rel="icon" href="favicon.png"> si manquante
    if 'rel="icon"' not in html and '<head>' in html:
        html = html.replace("</head>", '  <link rel="icon" type="image/png" href="favicon.png">\n</head>', 1)

    # Sauvegarde
    out = OUTPUT_DIR / filename
    out.write_text(html, encoding="utf-8")
    print(f"  ✅ {filename} refactoré")


# ============================================================================
# Sitemap & robots
# ============================================================================
def make_sitemap():
    pages = [
        ("", "1.0", "weekly"),
        ("telecharger.html", "0.95", "weekly"),
        ("beta.html", "0.9", "weekly"),
        ("guide.html", "0.85", "monthly"),
        ("faq.html", "0.85", "monthly"),
        ("a-propos.html", "0.7", "monthly"),
        ("contact.html", "0.7", "monthly"),
        ("cgu.html", "0.5", "yearly"),
        ("cgv.html", "0.5", "yearly"),
        ("confidentialite.html", "0.5", "yearly"),
        ("cookies.html", "0.5", "yearly"),
        ("mentions-legales.html", "0.4", "yearly"),
    ]
    today = "2026-05-24"
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for path, prio, freq in pages:
        xml += "  <url>\n"
        xml += f"    <loc>https://mesurechassis.com/{path}</loc>\n"
        xml += f"    <lastmod>{today}</lastmod>\n"
        xml += f"    <changefreq>{freq}</changefreq>\n"
        xml += f"    <priority>{prio}</priority>\n"
        xml += "  </url>\n"
    xml += "</urlset>\n"
    (OUTPUT_DIR / "sitemap.xml").write_text(xml, encoding="utf-8")
    print("  ✅ sitemap.xml")


def make_robots():
    txt = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /404.html\n\n"
        "Sitemap: https://mesurechassis.com/sitemap.xml\n"
    )
    (OUTPUT_DIR / "robots.txt").write_text(txt, encoding="utf-8")
    print("  ✅ robots.txt")


def make_htaccess():
    """Page 404 personnalisée pour Easyhost (Apache)."""
    txt = (
        "# MesureChâssis - configuration Apache pour Easyhost\n"
        "ErrorDocument 404 /404.html\n\n"
        "# Forcer HTTPS\n"
        "RewriteEngine On\n"
        "RewriteCond %{HTTPS} !=on\n"
        "RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n\n"
        "# Compression\n"
        "<IfModule mod_deflate.c>\n"
        "  AddOutputFilterByType DEFLATE text/html text/css application/javascript application/xml image/svg+xml\n"
        "</IfModule>\n\n"
        "# Cache navigateur\n"
        "<IfModule mod_expires.c>\n"
        "  ExpiresActive On\n"
        '  ExpiresByType image/png "access plus 1 month"\n'
        '  ExpiresByType image/jpeg "access plus 1 month"\n'
        '  ExpiresByType text/css "access plus 1 week"\n'
        '  ExpiresByType application/javascript "access plus 1 week"\n'
        "</IfModule>\n"
    )
    (OUTPUT_DIR / ".htaccess").write_text(txt, encoding="utf-8")
    print("  ✅ .htaccess")


# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"\n🚀 Build du site MesureChâssis dans {OUTPUT_DIR}\n")

    # --- 1. Refactor des pages EXISTANTES ---
    print("📝 1. Refactor des pages existantes…")
    existing = [
        ("index.html", "index"),
        ("guide.html", "guide"),
        ("mentions-legales.html", "mentions-legales"),
        ("confidentialite.html", "confidentialite"),
        ("contact.html", "contact"),
        ("beta.html", "beta"),
    ]
    for filename, active in existing:
        refactor_existing(filename, active)

    # --- 2. Nouvelles pages ---
    print("\n📝 2. Création des nouvelles pages…")
    new_pages = {
        "cgu.html": make_cgu(),
        "cgv.html": make_cgv(),
        "cookies.html": make_cookies(),
        "faq.html": make_faq(),
        "telecharger.html": make_telecharger(),
        "404.html": make_404(),
        "a-propos.html": make_about(),
    }
    for name, content in new_pages.items():
        (OUTPUT_DIR / name).write_text(content, encoding="utf-8")
        print(f"  ✅ {name}")

    # --- 3. Sitemap + robots + htaccess ---
    print("\n📝 3. Génération des fichiers de configuration…")
    make_sitemap()
    make_robots()
    make_htaccess()

    # --- 4. Vérification ---
    print("\n📊 Résumé final :")
    files = sorted(OUTPUT_DIR.iterdir())
    for f in files:
        size = f.stat().st_size
        size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/(1024*1024):.1f} MB"
        print(f"  - {f.name} ({size_str})")
    print(f"\n✅ Build terminé ! {len(files)} fichiers dans {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
