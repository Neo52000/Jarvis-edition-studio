---
name: editorial-workflow
description: Workflow rédaction, contrôle qualité, épreuves et validation humaine dans JARVIS Édition Studio.
---

# Exécution d'un livre

1. Lire `CLAUDE.md` et l'export JSON du livre.
2. Pour la conception, utiliser `prompts/01-brief.md`.
3. Générer **un chapitre à la fois**. Enregistrer uniquement des propositions.
4. Utiliser `prompts/02-audit.md` puis `prompts/03-verification.md`.
5. Documenter les sources primaires, licences et incertitudes.
6. L'utilisateur relit et valide dans l'interface. N'écrire aucune validation fictive.
7. Exporter le dossier JSON depuis le navigateur, exécuter `scripts/export_book.py`.
8. Réaliser une vérification manuelle des épreuves avant toute diffusion.

Aucune tâche ne doit publier automatiquement un livre.
