# JARVIS Édition Studio — MVP v1.0

Plateforme privée de microédition pour Papeterie Reine & Fils : **Claude Code + GitHub + Supabase**.

## Ce que la V1 fait

- Tableau de bord responsive en français, authentification Supabase par lien magique.
- Collections et dossiers livres, chapitres en Markdown, historique de versions.
- Sources et statut de vérification, sept contrôles éditoriaux, approbation humaine.
- Coûts par livre et prix de vente cible (sans calcul de marge non justifié).
- Export JSON du dossier, puis génération locale de Markdown, DOCX et PDF A5.
- Génération / audit / plan de fact-checking par Claude Code CLI en local, sans outil ni accès aux bases lors de ces appels.
- Contrôle RLS PostgreSQL : un utilisateur ne voit que ses propres contenus.

## Important : état du projet

Ceci est un **prototype opérationnel en local**. Aucun site n'a été déployé ; l'état d'application
des migrations Supabase est indiqué dans le rapport de déploiement.
Les appels Claude nécessitent une installation Claude Code et son authentification.
Le navigateur nécessite la configuration d'un **nouveau** projet Supabase isolé.
Les PDF générés sont des **épreuves de travail** : pas de conformité KDP certifiée.

## Mise en route, sans risque pour la boutique

### 1. Créer un dépôt privé GitHub

Nom proposé : `jarvis-edition-studio`, séparé de `ma-papeterie-v1`.
Créer le dépôt **privé** depuis ton compte GitHub, puis dans ce répertoire :

```bash
git init
git add .
git commit -m "feat: edition studio MVP"
git branch -M main
git remote add origin https://github.com/Neo52000/jarvis-edition-studio.git
git push -u origin main
```

Ces commandes supposent que le dépôt distant a d'abord été réellement créé.

### 2. Créer un projet Supabase NEUF

Avant création, vérifier le tarif et les quotas de l'organisation. Ne jamais
utiliser le projet Supabase `ma-papeterie` en production.
Nom suggéré : `jarvis-edition-studio` ; région suggérée : France (`eu-west-3`).
Activer Supabase Auth par lien magique (OTP), définir le `Site URL` et les
`Redirect URLs` vers l'origine depuis laquelle `web/` est servi.

Dans le **nouveau** projet uniquement, appliquer les migrations versionnées de `supabase/migrations/`
dans l'ordre (`supabase db push`, ou MCP/SQL Editor ; `sql/001_schema.sql` n'est que la référence du schéma initial).
Auth : activer l'e-mail OTP, **désactiver les inscriptions publiques**, inviter l'unique adresse autorisée.
Vérifier les tables, leurs politiques RLS, puis faire un test avec deux utilisateurs
pour confirmer que chacun ne voit que ses propres livres. Ne pas rendre
l'inscription publique si le studio reste mono-utilisateur : restreindre les
inscriptions au niveau Auth (ou utiliser un service d'accès privé).

### 3. Configurer le site

```bash
cp web/config.example.js web/config.js
# Compléter uniquement : URL Supabase + clé sb_publishable_ du nouveau projet.
python -m http.server 8000 --directory web
```

Ouvrir `http://localhost:8000`. Le fichier `web/config.js` est ignoré par Git.
Pour un déploiement statique, définir le fichier de configuration au build via
un mécanisme sûr sans jamais exposer de clé secrète. Un URL et une clé publiable
Supabase peuvent être publics, mais la **base reste protégée par RLS**.

Le projet est conçu pour usage privé. Pour mise sur Internet, ajouter un contrôle
d'accès au niveau hébergement et vérifier les redirect URLs Supabase.

### 4. Travailler avec Claude Code

Installer Claude Code depuis la documentation officielle, se connecter avec
`claude auth login`, puis lancer `claude` depuis le dossier racine. Il lit
automatiquement `CLAUDE.md` et le workflow `.claude/skills/editorial-workflow`.

Exemple de génération d'un brouillon (sans accès outil) :

```bash
python scripts/claude_generate.py examples/sample_book.json --chapter 1 --task draft
```

Des variantes : `--task audit` et `--task factcheck`.
Il faut ensuite **lire et intégrer manuellement** le texte dans le dossier livre.
Cette V1 ne synchronise pas automatiquement les sorties Claude dans Supabase.
Les coûts d'usage de Claude Code/API peuvent s'appliquer selon ton compte.

### 5. Exporter le livre

Exporter le dossier JSON depuis le tableau de bord, puis :

```bash
python -m pip install -r requirements.txt
python scripts/export_book.py chemin/vers/livre.json --out exports/
```

Pour interdire une épreuve finale sans toutes les validations :

```bash
python scripts/export_book.py chemin/vers/livre.json --out exports/ --final
```

Un export non-final comporte la mention de travail. Contrôler physiquement les
PDF/DOCX et procéder aux formalités de dépôt légal / ISBN / impression avant vente.

## Tests

```bash
python -m pytest tests -q                      # export, génération (CLI mocké), hygiène secrets
node --check web/app.js && node --test tests/js/util.test.mjs
# Tests RLS/triggers : base Postgres JETABLE et vide uniquement (jamais un projet Supabase)
JARVIS_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/scratch python -m pytest tests/test_sql.py -q
```

`web/vendor/supabase.js` est le bundle `@supabase/supabase-js@2.118.0` figé (hash vérifié par les tests).
La CI ne déploie ni ne publie rien.

## Architecture

- `sql/001_schema.sql` : modèle de données / RLS / déclencheurs.
- `web/` : interface cliente Supabase Auth (aucune clé secrète serveur).
- `scripts/claude_generate.py` : brouillons Claude Code local, sans accès outils.
- `scripts/export_book.py` : exports de manuscrits.
- `prompts/` : prompts métier à adapter.
- `.claude/skills/` : procédure réutilisable.

## Non livré en V1

Publication KDP / Shopify automatique, génération d'illustrations,
validation juridique ou prépresse certifiée, connexion directe Claude/Supabase,
recherche concurrentielle automatisée, intégration ma-papeterie.fr. Les outils
et validations nécessaires seront évalués **après** le pilote.

## Sécurité et exploitation

- Ne jamais déployer ou stocker de secret `sb_secret_`, `service_role` ou token GitHub dans `web/`.
- Ne jamais pousser des fichiers de manuscrits sensibles vers un dépôt public.
- Tester RLS, sauvegardes, quotas et coûts avant ouverture à plusieurs utilisateurs.
- Ne jamais publier automatiquement. Seuls des humains valident la sortie.
- Ne jamais supposer l'exactitude des contenus IA ou leur éligibilité au droit d'auteur.
