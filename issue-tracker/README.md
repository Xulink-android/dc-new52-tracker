# DC New 52 · Issues — Comic Book Reading Orders
Application PWA indépendante pour suivre les fascicules du New 52 dans l'ordre exact du site [Comic Book Reading Orders](https://comicbookreadingorders.com/dc/new-52-reading-order-part-1/).

## Périmètre

| Source | Fascicules hors événements | Renvois événements |
|---|---:|---:|
| [Partie 1](https://comicbookreadingorders.com/dc/new-52-reading-order-part-1/) | 640 | 3 |
| [Partie 2](https://comicbookreadingorders.com/dc/new-52-reading-order-part-2/) | 605 | 8 |
| [Partie 3](https://comicbookreadingorders.com/dc/new-52-reading-order-part-3/) | 698 | 14 |
| **Total** | **1 943** | **25** |

Les 25 renvois contiennent **24 événements New 52** et une transition vers **DC You**. Les 24 événements New 52 ont été détaillés à l'intérieur de l'application, pour **554 fascicules supplémentaires**, dans leur ordre d'origine.

**Total à cocher : 2 497 fascicules**, hors transition DC You. Les renvois d'événement sont affichés dans la liste, mais ne comptent pas comme un fascicule supplémentaire lorsque leurs numéros détaillés sont déjà intégrés. La partie **DC You** reste une suite distincte, non incluse dans le total.

## Fonctionnement

- Une case par fascicule, les événements se déplient à leur place d'origine
- Trois parties, recherche, filtre lu/non lu, renvois d'événements
- Progression locale : `dc-cbro-new52-issues-progress-v1`
- Export / import des sauvegardes personnelles au format JSON
- Thème clair/sombre et installation Android / PWA autonome
- Liens vers la source, sans copie des commentaires et résumés du site
- Navigation avec les applications DC Tracker et Marvel Tracker existantes
- Usage local hors ligne via un service worker

Les fichiers d'origine des deux autres applications, leurs clés de progression et leurs checklists ne sont pas modifiés par ce nouveau catalogue.

## Mise à jour de la source

Le script `scripts/import_new52_cbro.py` importe les données bibliographiques des trois pages et des 24 pages d'événements. Il vérifie les compteurs avant de publier le résultat dans `issue-tracker/catalog.json`. Une exécution GitHub Actions peut être lancée volontairement depuis la page Workflows pour mettre à jour les données après modification du site d'origine.

**Avertissement :** l'application est indépendante de Comic Book Reading Orders, DC et leurs éditeurs. Les liens de lecture officielle appartiennent aux services concernés et peuvent exiger un abonnement. Les règles de lecture « Essential issues only » du site d'origine ne sont pas reproduites dans cette version.
