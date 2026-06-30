"""🎬 Génération en MASSE des 8 scripts TikTok restants
Style : Aluminium + maisons béton + menuisier en action
Voix-off : nova féminine (tts-1-hd)
"""
import asyncio, base64, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
API_KEY = os.getenv('EMERGENT_LLM_KEY')
PROMO_ROOT = Path('/app/backend/static/promo')

# Base style commun à TOUS les prompts d'image
ALU_STYLE = (
    "Vertical 9:16 portrait, photorealistic, professional French aluminum "
    "carpentry context, anthracite grey or black aluminum window frames "
    "(modern Schüco/Reynaers profile), modern CONCRETE house facade or "
    "contemporary architecture in background, cinematic golden hour lighting, "
    "high-end B2B SaaS marketing visual, premium quality, sharp focus"
)

SCRIPTS = {
    # ══════════════════════════════════════════════════════════════
    "tiktok_script1": {
        "voice": (
            "POV : t'es menuisier alu, vingt-trois ans de métier, "
            "et tu mesures encore avec un carnet papier. "
            "Hauteur cent vingt-deux. Ou cent trente-deux ? Le deux est mal écrit. "
            "Diagonale ? T'as pas pris la peine. Photo ? Bah non, t'as oublié. "
            "Trois jours après, l'atelier appelle : « Les cotes correspondent pas, "
            "le châssis rentre pas. » Devine quoi ? Tu refais le chantier à tes frais. "
            "Coût : huit cents euros. Femme : pas contente. "
            "Ou tu télécharges MesureChâssis. Tu mesures sur ton tél, tout est carré. "
            "L'atelier valide direct. Zéro retour. "
            "MesureChâssis. Lien en bio."
        ),
        "slides": [
            ("01_pov_hook.png",
             "dark charcoal background, giant white text 'POV : TU MESURES À "
             "L'ANCIENNE' with small notebook emoji, dramatic TikTok hook"),
            ("02_carnet_dechire.png",
             "close-up old crumpled paper notebook with messy handwriting in pencil, "
             "broken pencil, blurred construction site"),
            ("03_atelier_call.png",
             "smartphone displaying angry phone call notification from 'ATELIER', "
             "blurred construction site background"),
            ("04_chassis_renvoye.png",
             "frustrated foreman holding anthracite aluminum window frame that "
             "doesn't fit in opening, modern workshop background"),
            ("05_facture_800.png",
             "calculator + euro banknotes scattered + dramatic red overlay '800 €' "
             "on dark surface"),
            ("06_femme_facon.png",
             "silhouette of a wife with arms crossed, looking annoyed, blurred living "
             "room background, soft warm lighting"),
            ("07_app_mesure.png",
             "hand holding modern smartphone showing MesureChâssis app dashboard with "
             "successful measurement form, anthracite aluminum window visible"),
            ("08_cta.png",
             "dark background, MesureChâssis logo, bold text 'ESSAI 14J GRATUIT' "
             "and '19€/MOIS', orange accent, call-to-action slide"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script3": {
        "voice": (
            "Tu reçois un cahier des charges de douze pages... "
            "et tu sais déjà que ta soirée va y passer. "
            "Cinquante lignes de cotes, cinq vues, trois plans, à recopier à la main. "
            "Une erreur, et ton châssis alu est foutu. "
            "Avec MesureChâssis, tu prends une seule photo du document. "
            "L'intelligence artificielle lit toutes les cotes en moins de trois secondes. "
            "Châssis fixe 1200 par 1500. Vasistas 800 par 600. Porte-fenêtre 2 vantaux. "
            "Tout est extrait automatiquement, prêt à valider, avec les diagonales calculées. "
            "Tu récupères deux heures par chantier. "
            "MesureChâssis. Lien en bio."
        ),
        "slides": [
            ("01_cdc_pile.png",
             "vertical stack of CDC PDF documents on a wooden desk, "
             "evening lamp lighting, '12 PAGES' overlay text orange, dramatic"),
            ("02_recopie_main.png",
             "tired hand writing measurements in a notebook with a pen, scattered "
             "papers around, late evening atmosphere"),
            ("03_clock_2h.png",
             "vintage clock showing 2 hours of work, dark background, orange '2H' "
             "overlay, dramatic tired mood"),
            ("04_smartphone_pdf.png",
             "smartphone taking a photo of a PDF document on a desk, ALUMINUM "
             "carpentry context, blueprint visible"),
            ("05_ai_analyzing.png",
             "smartphone screen showing AI progress bar 'Analyse en cours...' with "
             "scanning effect on a PDF blueprint, futuristic UI"),
            ("06_dashboard_filled.png",
             "smartphone dashboard showing MesureChâssis app with all measurements "
             "filled automatically: '1200x1500', '800x600', '1600x2150', orange UI"),
            ("07_stopwatch_3sec.png",
             "stopwatch showing 3 seconds, orange highlight, dramatic motion blur"),
            ("08_cta.png",
             "dark background, MesureChâssis logo, '+ 2 HEURES PAR CHANTIER' bold "
             "white text, 'LIEN EN BIO' orange CTA, modern minimalist"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script4": {
        "voice": (
            "Tu mesures un châssis alu. Yann, l'assistant IA, te checke en temps réel. "
            "Tu tapes : hauteur 218. Yann : « T'as vu le seuil ? Mesure depuis le sol "
            "fini, pas la chape. » Tu corriges. Tu sauves ton chantier. "
            "Tu tapes : reculement 12 centimètres. Yann : « OK pour pose en applique. "
            "Vérifie le tableau côté extérieur. » Tu prends une photo, tu valides. "
            "Diagonales : 1822, 1825. Yann : « Châssis d'aplomb. Tu peux poser. » "
            "Confiance : cent pour cent. "
            "Yann inclus dans tous nos plans payants. MesureChâssis. Lien en bio."
        ),
        "slides": [
            ("01_yann_intro.png",
             "smartphone screen with AI assistant chat interface 'Yann' speaking, "
             "orange and white UI, hand holding the phone on construction site"),
            ("02_yann_seuil.png",
             "smartphone chat showing Yann message 'T'as vu le seuil ? Mesure du sol "
             "fini', construction site background with anthracite aluminum door"),
            ("03_seuil_correction.png",
             "close-up of aluminum door threshold measurement, measuring tape laid "
             "between concrete subfloor and finished floor, technical detail"),
            ("04_yann_reculement.png",
             "smartphone chat showing Yann 'OK pour pose en applique', professional "
             "carpenter holding measurement tape against aluminum frame"),
            ("05_photo_tableau.png",
             "smartphone camera shooting an aluminum window frame opening, viewfinder "
             "visible, professional photo capture moment"),
            ("06_diagonales_ok.png",
             "smartphone screen showing two diagonal measurements 1822mm 1825mm with "
             "green checkmark, 'D'APLOMB ✅' overlay"),
            ("07_carpenter_confident.png",
             "professional French carpenter standing confidently next to a perfectly "
             "installed anthracite aluminum window on modern concrete house"),
            ("08_cta.png",
             "dark background, big text 'YANN, TON CHEF D'ATELIER DE POCHE', orange "
             "MesureChâssis logo, '19€/MOIS' CTA, premium SaaS"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script6": {
        "voice": (
            "Tableau ou baie ? Tu confonds ? T'es pas seul. "
            "Le tableau, c'est le trou dans le mur, avant pose. "
            "La baie, c'est l'ouverture finie, après isolation. "
            "La différence ? Souvent quatre à six centimètres. "
            "Confusion égale châssis trop petit ou trop grand. "
            "Soit tu mets des cales partout, soit tu commandes un nouveau châssis. "
            "Dans les deux cas, tu perds quatre cents euros. "
            "MesureChâssis te demande lequel à chaque mesure. "
            "Plus jamais d'erreur. Lien en bio."
        ),
        "slides": [
            ("01_hook.png",
             "dark background, big white text 'TABLEAU ou BAIE ?', smaller orange "
             "text 'TU CONFONDS ?', minimalist dramatic typography"),
            ("02_tableau_diagram.png",
             "technical architectural diagram showing rough wall opening labeled "
             "'TABLEAU' with concrete edges, top-down view, clean minimalist"),
            ("03_baie_diagram.png",
             "technical architectural diagram showing finished window opening "
             "labeled 'BAIE' with insulation and finished plaster, contemporary"),
            ("04_comparison.png",
             "side-by-side technical comparison of tableau vs baie with arrows "
             "showing '5 CM DIFFÉRENCE' in orange, blueprint style"),
            ("05_chassis_trop_petit.png",
             "anthracite aluminum window frame visibly too small in concrete "
             "opening with multiple wedges/shims, problem visualization"),
            ("06_facture_400.png",
             "calculator showing '400 €' with euro banknotes scattered, dramatic "
             "red overlay 'PERTE', dark surface"),
            ("07_app_choice.png",
             "smartphone showing MesureChâssis app interface with two big buttons "
             "'TABLEAU' and 'BAIE', clean French UI"),
            ("08_cta.png",
             "dark background, MesureChâssis logo, text 'PLUS JAMAIS D'ERREUR', "
             "orange CTA 'LIEN EN BIO', minimalist"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script7": {
        "voice": (
            "Un menuisier moyen perd mille huit cent quarante-sept euros par an, "
            "à cause de cotes mal prises. "
            "Ces mille huit cent quarante-sept euros, c'est : "
            "des SAV non facturés, des châssis refaits, "
            "des heures de pose en plus, de la quincaillerie commandée deux fois. "
            "Tu fais cent chantiers par an, tu fais mille huit cent quarante-sept "
            "euros d'erreurs, soit dix-huit euros d'erreur par chantier. "
            "MesureChâssis coûte... dix-neuf euros par mois. "
            "Math : tu rentabilises en trois chantiers. "
            "Le reste de l'année, tu mets de l'argent dans ta poche. "
            "Lien en bio."
        ),
        "slides": [
            ("01_hook_1847.png",
             "dramatic dark background, giant orange text '1847 €/AN', smaller "
             "white text 'PERDUS À CAUSE DES COTES', red bleeding euro symbol"),
            ("02_breakdown.png",
             "list overlay on dark background with 4 lines: 'SAV', 'CHÂSSIS REFAITS', "
             "'HEURES EN PLUS', 'QUINCAILLERIE 2x', each in red, dramatic"),
            ("03_calculator.png",
             "professional calculator on desk showing '100 × 18 = 1847', euro "
             "banknotes scattered, dark wood surface"),
            ("04_logo_19.png",
             "MesureChâssis logo with bold text '19 €/MOIS' in orange, dark "
             "premium background, SaaS branding"),
            ("05_math_rentable.png",
             "math equation overlay '3 CHANTIERS = RENTABILISÉ' on construction "
             "site background with anthracite aluminum window"),
            ("06_billets_poche.png",
             "hand putting euro banknotes into a jeans back pocket, work clothes, "
             "satisfaction, golden hour lighting"),
            ("07_chassis_pose.png",
             "professional carpenter successfully installing large anthracite "
             "aluminum window into modern concrete house, golden hour, satisfaction"),
            ("08_cta.png",
             "dark background, MesureChâssis logo, '19€/MOIS · RENTABILISÉ EN "
             "3 CHANTIERS', 'LIEN EN BIO', orange minimalist CTA"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script8": {
        "voice": (
            "Combien d'heures tu passes le soir... sur tes devis ? "
            "Moyenne menuisier indépendant : deux heures par soir. "
            "Sur cinq soirs, dix heures par semaine. "
            "Sur le mois, quarante heures non facturées. "
            "Soit une semaine de travail entière... gratuite. "
            "MesureChâssis génère ton devis depuis tes mesures. "
            "Trente minutes au lieu de deux heures. "
            "Tu récupères tes soirées. Tu joues avec tes enfants. "
            "Tu manges avec ta famille. "
            "Ta vie, c'est pas que des devis. "
            "MesureChâssis. Lien en bio."
        ),
        "slides": [
            ("01_hook_soiree.png",
             "warm dark home office at night with single desk lamp on, papers and "
             "laptop, lonely atmosphere, '21H30' clock visible"),
            ("02_tired_carpenter.png",
             "tired French carpenter at home office desk late evening, rubbing "
             "eyes, work clothes still on, devis papers scattered"),
            ("03_calc_40h.png",
             "calculator showing '10H × 4 = 40H/MOIS', dramatic overlay 'UNE "
             "SEMAINE GRATUITE', dark background"),
            ("04_devis_auto.png",
             "smartphone showing MesureChâssis app generating a PDF quote "
             "automatically, progress bar 'Génération devis...', professional UI"),
            ("05_devis_30min.png",
             "stopwatch showing 30 minutes, contrast with previous 2h, satisfaction"),
            ("06_family_dinner.png",
             "warm family dinner scene, parents with children at table, laughter, "
             "candlelight, emotional family moment"),
            ("07_kids_playing.png",
             "father playing with his kids in the living room, joyful evening, "
             "warm soft lighting, no laptop in sight"),
            ("08_cta.png",
             "dark background, big text 'TA VIE, C'EST PAS QUE DES DEVIS', "
             "MesureChâssis logo, 'LIEN EN BIO' orange CTA"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script9": {
        "voice": (
            "Marc. Douze ans de menuiserie alu. Trois employés. "
            "Avant MesureChâssis : trois SAV par mois. Stress permanent. "
            "Femme qui rouspète. Soirées à refaire des devis. Insomnies. "
            "Un mois après MesureChâssis : zéro SAV. "
            "Ses techniciens utilisent l'app sur le chantier. "
            "Toutes les cotes arrivent directement dans son ordi. "
            "Il a gagné une journée par semaine. "
            "Marc dit : « C'est pas une appli. C'est un employé en plus, "
            "qui bosse vingt-quatre sept, qui se trompe jamais, "
            "et qui coûte dix-neuf balles. » "
            "Toi aussi ? Lien en bio."
        ),
        "slides": [
            ("01_marc_intro.png",
             "professional French carpenter (back view, anonymous), wearing work "
             "vest, standing in front of his aluminum carpentry workshop, "
             "'MARC · 12 ANS DE MÉTIER' overlay"),
            ("02_marc_stress.png",
             "tired carpenter at office desk surrounded by SAV paperwork, "
             "rubbing temples, dramatic warm light, '3 SAV / MOIS' overlay"),
            ("03_evening_devis.png",
             "late evening home office, single lamp, papers, devis open, sad "
             "atmosphere, clock showing 23H"),
            ("04_team_app.png",
             "two French carpenters in gilets jaunes using smartphones with "
             "MesureChâssis app on a modern construction site with anthracite "
             "aluminum windows being installed"),
            ("05_dashboard_centralized.png",
             "office computer screen showing MesureChâssis admin dashboard with "
             "all team measurements centralized, modern UI, orange accents"),
            ("06_calendar_free_day.png",
             "calendar showing a free day (highlighted in orange) among working "
             "days, 'GAGNÉ' overlay, contrast"),
            ("07_marc_quote.png",
             "dark dramatic background with quote text 'C'EST UN EMPLOYÉ EN PLUS "
             "À 19€', signed Marc, premium typography"),
            ("08_cta.png",
             "MesureChâssis logo on dark background, 'TOI AUSSI ?', orange CTA "
             "'LIEN EN BIO', premium minimalist B2B"),
        ],
    },
    # ══════════════════════════════════════════════════════════════
    "tiktok_script10": {
        "voice": (
            "Le client te dit : « Vous avez cassé mon mur en posant le châssis. » "
            "Toi : « C'était déjà fissuré avant. » "
            "Lui : « Prouvez-le. » "
            "Pas de photo, ta parole contre la sienne. "
            "Tribunal. Avocat. Trois mille euros de frais. "
            "Avec MesureChâssis, tu prends une photo avant la pose. "
            "Elle est horodatée. Géolocalisée. Signée par le client. "
            "Stockée en cloud sécurisé. "
            "Litige terminé en trente secondes. "
            "Tu envoies la photo au juge. Affaire classée. "
            "Protège tes chantiers. Lien en bio."
        ),
        "slides": [
            ("01_mur_fissure.png",
             "close-up of cracked concrete wall around an aluminum window, "
             "client pointing at it accusingly, dramatic lighting, '!' icon"),
            ("02_litige_3000.png",
             "courthouse facade silhouette with overlay text '3000 € DE FRAIS', "
             "lawyer briefcase, dark dramatic mood"),
            ("03_app_photo.png",
             "smartphone with MesureChâssis app camera active, taking photo of "
             "an aluminum window before installation, French construction context"),
            ("04_photo_timestamped.png",
             "smartphone screen showing photo with timestamp '14:32 - 30/06/2026' "
             "and GPS location overlay 'Lyon, France', secure UI"),
            ("05_client_signature.png",
             "smartphone showing digital signature field with client signing on "
             "screen with finger, professional context"),
            ("06_cloud_secure.png",
             "abstract secure cloud storage visualization with lock icon, MesureChâssis "
             "branding, modern minimalist tech illustration"),
            ("07_juge_classed.png",
             "judge gavel hitting block with overlay 'AFFAIRE CLASSÉE', orange "
             "stamp 'PREUVE ACCEPTÉE', dramatic"),
            ("08_cta.png",
             "dark premium background, shield icon, text 'PROTÈGE TES CHANTIERS', "
             "MesureChâssis logo, orange 'LIEN EN BIO' CTA"),
        ],
    },
}

async def gen_image(filename, prompt, output_dir):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    full_prompt = ALU_STYLE + ", " + prompt
    chat = LlmChat(api_key=API_KEY, session_id=f'{output_dir.name}-{filename}',
                   system_message='Designer.')
    chat.with_model('gemini', 'gemini-3.1-flash-image-preview').with_params(modalities=['image','text'])
    try:
        _, images = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
        if images:
            (output_dir / filename).write_bytes(base64.b64decode(images[0]['data']))
            print(f'      ✅ {filename}')
            return True
    except Exception as e:
        print(f'      ❌ {filename}: {str(e)[:80]}')
    return False


async def gen_voice(text, output_dir):
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=API_KEY, base_url="https://integrations.emergentagent.com/llm")
    try:
        r = await client.audio.speech.create(
            model="tts-1-hd", voice="nova", input=text,
            speed=1.0, response_format="mp3"
        )
        (output_dir / "voiceover.mp3").write_bytes(r.content)
        print(f'      ✅ voiceover.mp3 ({len(r.content)//1024} KB)')
    except Exception as e:
        print(f'      ❌ voiceover.mp3: {str(e)[:80]}')


async def main():
    for script_name, content in SCRIPTS.items():
        print(f'\n🎬 {script_name.upper()}')
        output_dir = PROMO_ROOT / script_name
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f'   🎨 Images ({len(content["slides"])})...')
        for fn, p in content["slides"]:
            await gen_image(fn, p, output_dir)

        print(f'   🎙️  Voix-off (nova)...')
        await gen_voice(content["voice"], output_dir)

    print('\n' + '═'*50)
    print('✅ TERMINÉ — Tous les scripts sont prêts !')
    print('═'*50)


if __name__ == '__main__':
    asyncio.run(main())
