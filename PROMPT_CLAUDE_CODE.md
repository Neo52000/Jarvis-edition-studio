# Instruction de déploiement pour Claude Code — JARVIS Édition Studio

Tu agis comme architecte logiciel senior full-stack, expert PostgreSQL/Supabase, sécurité RLS,
Claude Code, GitHub et workflow éditorial. Prends connaissance du dépôt courant et de
`CLAUDE.md` avant d'écrire du code.

**Mission : rendre le MVP opérationnel de bout en bout**, sans altérer un quelconque service
ou dépôt existant de Papeterie Reine & Fils.

1. Audite tous les fichiers, lance les tests et corrige les défauts.
2. Vérifie la version courante de Supabase Auth, RLS et JS SDK via la documentation officielle.
3. Utilise un dépôt GitHub *privé et indépendant* `jarvis-edition-studio`.
   S'il n'existe pas ou si la création n'est pas possible, indique les opérations manuelles
   nécessaires; ne déplace pas le projet dans le dépôt de ma-papeterie.fr.
4. Crée ou connecte un projet Supabase **neuf et indépendant**, après avoir affiché les coûts
   réels et obtenu une validation explicite de toute facturation non nulle.
   Ne réutilise JAMAIS le projet Supabase de ma-papeterie.fr.
5. Applique `sql/001_schema.sql` après revue et tests, vérifie les triggers et les droits RLS
   avec deux comptes distincts. Utilise les migrations versionnées plutôt qu'une manipulation
   non tracée des tables de production.
6. Configure Auth OTP email, les URL de redirection et les restrictions d'accès.
7. Configure `web/config.js` localement; n'y place que l'URL et la clé publiable.
   Interdiction absolue d'exposer toute clé secrète, mot de passe, ou token.
8. Déploie le tableau de bord sur un sous-domaine privé ou environnement de test indépendant.
9. Vérifie au navigateur toutes les opérations : collection, livre, chapitre, version,
   source, contrôle qualité, coût, visa humain et export JSON. Vérifie le refus de validation
   prématurée et l'invalidation après modification d'un chapitre.
10. Teste la génération locale via `scripts/claude_generate.py` puis l'export
    DOCX + PDF A5 + Markdown. L'IA peut rédiger et proposer, mais ne peut pas s'auto-valider.
11. Configure les tests GitHub Actions sans publication automatique. Teste l'absence de
    secrets dans le dépôt et la sécurité des accès en lecture/écriture.
12. Termine par un rapport : URL GitHub, URL Supabase, URL d'accès privé, état des tests,
    éventuels frais, vulnérabilités résiduelles et 3 prochaines améliorations prioritaires.

**Contraintes :** zéro action sur ma-papeterie.fr, zéro publication Amazon/Shopify,
zéro achat sans consentement explicite, pas d'invention de sources juridiques ou éditoriales,
pas de données clients en environnement de test, pas de connecteur IA utilisant des
identifiants tiers sans consentement. Aucune affirmation de « prêt pour l'imprimeur »
sans épreuve, vérification de pagination et conformité au cahier des charges réel.
