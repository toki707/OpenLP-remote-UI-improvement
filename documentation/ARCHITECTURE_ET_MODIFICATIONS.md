# Documentation Technique Complète — Refonte Mobile Remote & Mode Simplifié PC (OpenLP 3.1.7)

> **Licence :** GNU General Public License v3.0 or later (`GPL-3.0-or-later`)  
> **Base :** OpenLP 3.1.7 (`Copyright (c) 2008-2024 OpenLP Developers`)  
> **Objectif de ce document :** Fournir une référence technique exhaustive permettant à tout développeur de comprendre, maintenir, tester et faire évoluer le code sans assistance IA.

---

## 1. Vue d'ensemble des travaux réalisés

Ce projet apporte trois grands ensembles de fonctionnalités à **OpenLP 3.1.7** tout en préservant une rétrocompatibilité totale avec l'existant :

1. **Nouvelle Télécommande Web Mobile (`openlp/core/api/remote_client/`)** :
   - Interface 100 % autonome (zéro dépendance CDN externe pour fonctionner sur un réseau Wi-Fi local d'église sans Internet).
   - **Double moniteur 16:9 permanent** : écran **Prévisualisation** (avant envoi, avec bouton *Go Live*) et écran **En direct** (projecteur).
   - **Import direct d'images depuis la galerie du smartphone** vers la bibliothèque OpenLP, l'aperçu, le service ou le direct.
   - **Volet latéral rabattable (Drawer)** limité aux 5 sections essentielles : *Services*, *Images*, *Bible* (sélecteur Livre/Chapitre/Verset + lecture du texte), *Thèmes* (habillages visuels OpenLP avec miniatures) et *Diapos perso* (création et modification à distance).
   - **Conservation des 5 commandes inférieures d'origine** : *Élém. préc.*, *Élém. suiv.*, *Diapo préc.*, *Diapo suiv.* et *Affichage* (*Noir*, *Thème*, *Bureau*, *Afficher*).
   - **Bascule de thème Noir / Blanc** persistée dans `localStorage`.

2. **Extension de l'API REST v2 d'OpenLP (`openlp/core/api/versions/v2/`)** :
   - Ajout d'un répartiteur inter-threads Qt (`MainThreadDispatcher` / `call_on_main_thread`) permettant aux threads HTTP Flask/Waitress d'interagir en toute sécurité avec les contrôleurs graphiques PyQt5 (`preview_controller`, `live_controller`, `service_manager`, `media_item`).
   - Nouvelles routes v2 pour piloter le `preview_controller`, téléverser des images depuis un mobile, lister/créer/modifier des diapositives personnalisées (`CustomSlide`), et récupérer la liste des livres/chapitres des Bibles installées.

3. **Interface PC « Mode Simplifié / Jeunes » (`openlp/core/ui/simplifiedmode.py`)** :
   - Barre d'outils supérieure d'accès direct aux 4 bibliothèques principales : **Bible**, **Images & Affiches**, **Diapos perso**, **Chants**.
   - Bouton bascule **Mode Simplifié (Jeunes)** qui masque les panneaux complexes inutilisés (*Présentations*, *Médias*, *Contrôleur de projecteur*) tout en **conservant la barre d'outils native de chaque onglet (et notamment le bouton d'envoi Direct sans passer par l'aperçu)**.
   - Bouton bascule **Thème : Noir / Blanc** appliquant à chaud une feuille de style Qt moderne (`QSS`) et une palette adaptée.

---

## 2. Cartographie des fichiers créés et modifiés

| Fichier | Statut | Rôle |
| :--- | :--- | :--- |
| `openlp/core/api/lib.py` | Modifié | Ajout de `MainThreadDispatcher` et `call_on_main_thread(fn, wait=True, timeout=5.0)` pour exécuter les opérations PyQt5 sur le thread principal GUI. |
| `openlp/core/api/main.py` | Modifié | Ajout de `_get_remotes_dir()` et du dossier de secours intégré `openlp/core/api/remote_client/` si `%APPDATA%\openlp\data\remotes` est vide. |
| `openlp/core/api/remote_client/index.html` | Créé | Application Web Mobile complète (HTML5 / CSS Design System Noir & Blanc / JS ES6+ connecté à `/api/v2` et au WebSocket `/state`). |
| `openlp/core/api/remote_client/assets/version.js` | Créé | Fichier de version du client Web Remote (`appVersion = '3.2.0-custom'`). |
| `openlp/core/api/versions/v2/controller.py` | Modifié | Ajout des routes de prévisualisation (`/preview-items`, `/preview/show`, `/preview/progress`, `/preview/go-live`) et enrichissement Base64 des miniatures d'images (`_enrich_image_slides`). |
| `openlp/core/api/versions/v2/service.py` | Modifié | Ajout de `POST /api/v2/service/preview` pour charger un élément du service dans le panneau de prévisualisation sans le projeter en direct. |
| `openlp/core/api/versions/v2/plugins.py` | Modifié | Ajout de `/<plugin>/preview`, `/images/list`, `/images/upload`, `/custom/list`, `/custom/save` et `/bibles/books`. |
| `openlp/core/ui/simplifiedmode.py` | Créé | Contrôleur `SimplifiedModeController` et feuilles de style Qt `MODERN_DARK_QSS` / `MODERN_LIGHT_QSS` pour la barre d'accès rapide PC. |
| `openlp/core/ui/mainwindow.py` | Modifié | Appel de `attach_simplified_mode(self)` dans `MainWindow.bootstrap_post_set_up()`. |
| `scripts/remoteenhancementsplugin.py` | Créé | Module d'extension communautaire autonome copié dans `%APPDATA%\openlp\data\contrib\plugins\remote_enhancements\` pour activer toutes les nouveautés dans un binaire `OpenLP.exe` déjà compilé. |
| `scripts/OpenLPUISetup.cs` | Créé | Code source C# (.NET Framework WinForms) de l'installateur graphique Windows autonome `OpenLP-Remote-UI-Setup.exe`. |
| `install_custom_ui.bat` | Créé | Script batch d'installation rapide sous Windows. |
| `.github/workflows/release.yml` | Créé | Pipeline GitHub Actions (`windows-latest`) qui compile `OpenLP-Remote-UI-Setup.exe` et publie les archives sur GitHub Releases à chaque tag `v*`. |
| `tests/openlp_core/api/v2/test_controller.py` | Modifié | Tests unitaires des nouvelles routes `/api/v2/controller/preview*` et de `_enrich_image_slides`. |
| `tests/openlp_core/api/v2/test_service.py` | Modifié | Tests unitaires de `/api/v2/service/preview` (par UUID, par index, et cas d'erreurs 400/404). |
| `tests/openlp_core/api/v2/test_plugins.py` | Modifié | Tests unitaires de `/<plugin>/preview`, `/images/list`, `/images/upload`, `/custom/list`, `/custom/save` et `/bibles/books`. |
| `tests/openlp_core/api/test_main.py` | Modifié | Tests unitaires du serveur statique `_get_remotes_dir()`, des routes `/` et `/assets/version.js`, et de `call_on_main_thread`. |
| `tests/openlp_core/ui/test_simplifiedmode.py` | Créé | Tests unitaires complets de `SimplifiedModeController` (sélection d'onglets, filtrage Mode Simplifié, bascule Thème Noir/Blanc). |

---

## 3. Architecture Backend & Référence des Nouvelles Routes API v2

### 3.1. Exécution Thread-Safe sur la boucle Qt (`openlp/core/api/lib.py`)

Dans OpenLP, le serveur HTTP Flask tourne dans un thread secondaire (`HttpWorker` via Waitress), tandis que tous les composants graphiques (`PreviewController`, `LiveController`, `ServiceManager`, `MediaManagerItem`) résident sur le thread principal Qt (`MainThread`).

La classe `MainThreadDispatcher(QtCore.QObject)` résout ce problème :
1. Elle s'attache au thread de `QCoreApplication.instance().thread()` via `moveToThread()`.
2. Lorsqu'une route Flask appelle `call_on_main_thread(fn, wait=True)`, si l'appelant est déjà sur le thread principal (cas des tests unitaires `pytest`), `fn()` est exécutée directement.
3. Si l'appelant est sur un thread HTTP Waitress, `execute_signal.emit((fn, event, box))` planifie l'exécution de `fn()` dans la boucle d'événements Qt principale via une connexion `QueuedConnection`, attend la fin via `threading.Event.wait(timeout)`, et retourne la valeur ou propage l'exception.

---

### 3.2. Nouvelles routes du Contrôleur (`openlp/core/api/versions/v2/controller.py`)

#### `GET /api/v2/controller/preview-items`
Retourne l'élément actuellement chargé dans le panneau **Prévisualisation** (`preview_controller`).
- **Authentification :** Non requise (lecture seule).
- **Réponse `200 OK` (`application/json`) :**
  ```json
  {
    "id": "50dcb1bd-e6ad-11f1-8adc-c0a8105c5985",
    "title": "Jean 3:16 (Louis Segond)",
    "name": "bibles",
    "type": 1,
    "slides": [
      {
        "tag": "1",
        "title": "Jean 3:16",
        "text": "Car Dieu a tant aimé le monde...",
        "html": "Car Dieu a tant aimé le monde...",
        "selected": true
      }
    ]
  }
  ```
  *(Si l'élément est une image, la fonction `_enrich_image_slides` garantit que chaque diapo contient un champ `"img": "data:image/...;base64,..."`.)*

#### `POST /api/v2/controller/preview/show`
Sélectionne une diapositive précise dans le panneau **Prévisualisation**.
- **Authentification :** `@login_required`
- **Corps JSON :** `{"id": 0}` (index de la diapositive, base 0)
- **Réponse :** `204 No Content` (ou `400 Bad Request` si corps manquant).

#### `POST /api/v2/controller/preview/progress`
Passe à la diapositive suivante ou précédente dans le panneau **Prévisualisation**.
- **Authentification :** `@login_required`
- **Corps JSON :** `{"action": "next"}` ou `{"action": "previous"}`
- **Réponse :** `204 No Content` (ou `400 Bad Request` si action invalide).

#### `POST /api/v2/controller/preview/go-live`
Envoie l'élément actuellement en **Prévisualisation** directement vers le **Direct** (`live_controller`) à la diapositive sélectionnée (appelle `preview_controller.on_go_live()` sur le thread principal).
- **Authentification :** `@login_required`
- **Corps JSON :** `{}`
- **Réponse :** `204 No Content` (ou `400 Bad Request` si aucun élément n'est en prévisualisation).

---

### 3.3. Nouvelle route Service (`openlp/core/api/versions/v2/service.py`)

#### `POST /api/v2/service/preview` (et `/api/v2/service/preview/<item_id>`)
Charge un élément de la liste du service (`service_manager`) dans le panneau **Prévisualisation** sans l'afficher sur le projecteur.
- **Authentification :** `@login_required`
- **Corps JSON :** `{"id": "<uuid_ou_index_entier>"}`
- **Réponse :** `204 No Content`, `400 Bad Request` (identifiant manquant/invalide), ou `404 Not Found` (élément introuvable).

---

### 3.4. Nouvelles routes Plugins (`openlp/core/api/versions/v2/plugins.py`)

#### `POST /api/v2/plugins/<plugin>/preview`
Construit un `ServiceItem` à partir d'un élément de bibliothèque (`bibles`, `images`, `custom`, `songs`) et le charge dans `preview_controller`.
- **Authentification :** `@login_required`
- **Corps JSON :** `{"id": "<identifiant_element>"}` (ex. `"Jean 3:16"`, chemin d'image, ou ID de diapo perso).
- **Réponse :** `204 No Content`.

#### `GET /api/v2/plugins/images/list`
Retourne toutes les images enregistrées dans la bibliothèque Images d'OpenLP avec leurs miniatures en Base64.
- **Réponse `200 OK` :**
  ```json
  [
    {
      "id": "C:\\Users\\...\\openlp\\data\\images\\mobile_uploads\\affiche.png",
      "db_id": 1,
      "filename": "affiche.png",
      "title": "affiche.png",
      "thumbnail": "data:image/png;base64,..."
    }
  ]
  ```

#### `POST /api/v2/plugins/images/upload`
Téléverse une image depuis la galerie du téléphone, l'enregistre dans `AppLocation.get_section_data_path('images') / 'mobile_uploads'`, l'ajoute à la base SQLite du plugin Images, génère sa miniature, rafraîchit l'arbre UI sur le PC, et exécute l'action demandée (`preview`, `live`, `service`, ou `library`).
- **Authentification :** `@login_required`
- **Corps JSON (ou `multipart/form-data`) :**
  ```json
  {
    "filename": "programme_semaine.jpg",
    "data": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "action": "preview"
  }
  ```
- **Réponse `201 Created` :** retourne l'objet image créé (`id`, `filename`, `title`, `thumbnail`).

#### `GET /api/v2/plugins/custom/list`
Retourne toutes les diapositives personnalisées (`CustomSlide`) avec leurs couplets décodés depuis le format XML interne (`CustomXML`).

#### `POST /api/v2/plugins/custom/save`
Crée ou met à jour une diapositive personnalisée (`CustomSlide`) dans la base SQLite du plugin `custom`, recharge la liste sur le PC, et exécute optionnellement `action` (`preview`, `live`, `service`, ou `save`).
- **Authentification :** `@login_required`
- **Corps JSON :**
  ```json
  {
    "id": null,
    "title": "Thème de la Parole",
    "text": "MARCHER PAR LA FOI\n---\n2 Corinthiens 5:7",
    "credits": "Culte du dimanche",
    "theme_name": "Parole Biblique",
    "action": "preview"
  }
  ```
- **Réponse `200 OK` :** retourne la diapositive enregistrée avec son `id`.

#### `GET /api/v2/plugins/bibles/books`
Retourne la liste des Bibles installées dans OpenLP, la Bible principale active, ainsi que la liste ordonnée des livres et leur nombre exact de chapitres (`[{ "name": "Genèse", "abbreviation": "", "chapters": 50 }, ...]`).

---

## 4. Architecture Interface PC — Mode Simplifié (`openlp/core/ui/simplifiedmode.py`)

La classe `SimplifiedModeController(QtCore.QObject)` ajoute une barre d'outils `QToolBar` (`objectName = 'simplified_quick_bar'`) en haut de la fenêtre principale (`QtCore.Qt.TopToolBarArea`).

### Fonctionnement interne :
1. **Navigation directe (`focus_plugin_tab(plugin_name)`)** :
   - Rend `main_window.media_manager_dock` visible s'il était masqué.
   - Parcourt `main_window.media_tool_box` à la recherche du widget dont `widget.settings_section == plugin_name` (`bibles`, `images`, `custom`, `songs`) et l'active via `setCurrentIndex(idx)`.
   - **Important :** Les barres d'outils internes de chaque `MediaManagerItem` ne sont jamais altérées, ce qui garantit que le bouton natif **Envoyer en direct (Go Live)** reste toujours présent dans chaque onglet.
2. **Mode Simplifié (`toggle_simple_mode()`)** :
   - Lorsqu'il est activé, masque `projector_manager_dock` et retire temporairement du `MediaDockManager` les plugins dont le nom n'appartient pas à `YOUTH_ALLOWED_PLUGINS = ('bibles', 'images', 'custom', 'songs')` via `media_dock_manager.remove_dock(plugin.media_item)`.
   - Lorsqu'il est désactivé, réinsère tous les plugins actifs (`PluginStatus.Active`) via `media_dock_manager.add_item_to_dock(plugin.media_item)`.
3. **Bascule Thème Noir / Blanc (`toggle_color_theme()`)** :
   - Alterne à chaud entre `set_default_darkmode(app)` + `MODERN_DARK_QSS` et `set_default_lightmode(app)` + `MODERN_LIGHT_QSS`.

---

## 5. Compilation de l'installateur Windows (`OpenLP-Remote-UI-Setup.exe`)

L'installateur autonome Windows est écrit en C# standard sans dépendance tierce (`scripts/OpenLPUISetup.cs`) et embarque les 3 fichiers (`index.html`, `version.js`, `remoteenhancementsplugin.py`) en tant que ressources binaires compilées (`.NET Manifest Resources`).

Pour recompiler `OpenLP-Remote-UI-Setup.exe` sur n'importe quelle machine Windows (sans Visual Studio, uniquement avec le compilateur natif du système) :

```powershell
$ico = (Get-ChildItem -Recurse resources -Filter "OpenLP.ico" | Select-Object -First 1).FullName
& "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe `
  /out:"OpenLP-Remote-UI-Setup.exe" `
  /win32icon:"$ico" `
  /resource:"openlp\core\api\remote_client\index.html,index.html" `
  /resource:"openlp\core\api\remote_client\assets\version.js,version.js" `
  /resource:"scripts\remoteenhancementsplugin.py,remoteenhancementsplugin.py" `
  "scripts\OpenLPUISetup.cs"
```

L'exécutable supporte également l'installation silencieuse en ligne de commande :
```powershell
.\OpenLP-Remote-UI-Setup.exe /S
```

---

## 6. Exécution des Tests Unitaires et Vérification de la Couverture (>= 80 %)

Tous les développements sont couverts par des tests unitaires `pytest` situés dans :
- `tests/openlp_core/api/test_main.py`
- `tests/openlp_core/api/v2/test_controller.py`
- `tests/openlp_core/api/v2/test_service.py`
- `tests/openlp_core/api/v2/test_plugins.py`
- `tests/openlp_core/ui/test_simplifiedmode.py`

### Commande pour exécuter les tests et mesurer la couverture de code :

```bash
pytest \
  tests/openlp_core/api/test_main.py \
  tests/openlp_core/api/v2/test_controller.py \
  tests/openlp_core/api/v2/test_service.py \
  tests/openlp_core/api/v2/test_plugins.py \
  tests/openlp_core/ui/test_simplifiedmode.py \
  --cov=openlp.core.api.lib \
  --cov=openlp.core.api.main \
  --cov=openlp.core.api.versions.v2.controller \
  --cov=openlp.core.api.versions.v2.service \
  --cov=openlp.core.api.versions.v2.plugins \
  --cov=openlp.core.ui.simplifiedmode \
  --cov-report=term-missing \
  --cov-fail-under=80
```
