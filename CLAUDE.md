# JARVIS Édition Studio — Règles Claude Code

## Mission
Construire et faire évoluer une chaîne de microédition reproductible pour Papeterie Reine & Fils.
**Projet AUTONOME**, séparé des dépôts et bases de production ma-papeterie.fr.

## Priorités
1. Sécurité des données et confidentialité des manuscrits.
2. Qualité éditoriale, justesse des informations, traçabilité des sources.
3. Validation humaine explicite avant approbation et diffusion.
4. Coûts de production contrôlés, tests à faible budget.
5. Vitesse de production seulement une fois la qualité démontrée.

## Architecture
- `web/` : tableau de bord HTML/CSS/JavaScript + client Supabase côté navigateur.
- `sql/001_schema.sql` : schéma PostgreSQL isolé, RLS pour chaque table.
- `scripts/claude_generate.py` : appel local à `claude -p` pour générer des brouillons sans accès outil.
- `scripts/export_book.py` : création Markdown + DOCX + PDF A5 à partir d'un export JSON.
- `examples/` : données fictives, sans données clients.
- `tests/` : tests basiques automatisés.

## Interdictions absolues
- Ne jamais utiliser le projet Supabase de ma-papeterie.fr pour ce studio.
- Ne pas modifier de dépôt existant hors du dépôt dédié à l'édition.
- Ne jamais committer les clés secrètes, tokens, credentials, fichiers `web/config.js`, `.env` ou manuscrits confidentiels.
- Ne jamais utiliser `service_role` ou `sb_secret_` dans le navigateur.
- Ne jamais passer le statut `approved` sans les 7 contrôles et signature humaine.
- Ne jamais envoyer un manuscrit vers Amazon KDP, Shopify, Netlify, réseaux sociaux ou un imprimeur sans instruction et confirmation explicites.
- Ne pas prétendre qu'un texte généré a été vérifié; distinguer génération, audit et vérification externe.
- Ne pas fabriquer d'ISBN, d'avis, de sources, de statistiques, de témoignages, de droits ou de revenus.

## Procédure de travail
- Débuter par identifier le besoin et le module concerné.
- Développer sur branche dédiée, tests obligatoires et PR revue avant merge.
- Mettre à jour README et tests pour toute fonction nouvelle.
- Exécuter `python -m pytest tests -q` et `node --check web/app.js`.
- Vérifier l'affichage PDF/DOCX sur une épreuve réelle avant diffusion.
- Pour les règles françaises de l'édition, vérifier les sources officielles à jour (AFNIL, BnF, DGCCRF, KDP).

## Modèle éditorial
`collection → livre → chapitres → sources → contrôles qualité → approbation → export`.
L'export n'est pas une publication. Pas de publication automatisée en V1.

## Premier test
Livre de démonstration : « Le français sans fautes au quotidien », format A5.
Toujours remplacer le texte de démonstration par du contenu intégralement vérifié.
