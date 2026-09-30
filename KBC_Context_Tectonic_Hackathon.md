# KBC Context — Tectonic Hackathon
## Concept complet, architecture, personas et plan de présentation

> **Document de travail à partager avec l'équipe**
>
> Objectif : centraliser l'idée du projet KBC, expliquer précisément ce que l'on construit, pourquoi cela répond au challenge Tectonic, comment le prototype doit fonctionner et comment le présenter au jury.

---

# 1. Résumé en 30 secondes

Nous voulons construire un moteur de personnalisation bancaire qui maintient une **compréhension dynamique du contexte de chaque client**.

Le système combine :

1. un **contexte persistant** : situation relativement stable du client ;
2. des **moments actifs** : événements et signaux récents ;
3. un **Intent Engine** : estimation de ce dont le client pourrait avoir besoin ;
4. un **Decision Engine** : décision sur ce que KBC devrait faire maintenant ;
5. une **expérience KBC adaptative** : l'interface et les parcours se réorganisent en fonction du client.

L'idée n'est **pas** :

> « analyser les transactions et afficher des publicités personnalisées ».

L'idée est plutôt :

> **comprendre ce qui se passe dans la vie financière du client et adapter KBC au bon moment.**

La meilleure action peut être :

- proposer un produit ;
- proposer un service ;
- proposer un parcours ;
- donner un conseil ;
- prévenir d'un problème ;
- attendre ;
- ou **ne rien faire du tout**.

Phrase centrale :

> **We turn customer signals into customer understanding.**

Autre formulation :

> **KBC adapts to the customer instead of forcing the customer to navigate the bank.**

---

# 2. Ce que demande réellement le challenge KBC

Le brief KBC du *Tectonic Hackathon - Participants Guide* demande d'imaginer un futur dans lequel KBC comprend parfaitement ce dont ses clients ont besoin et leur répond **au bon moment**.

Le brief insiste sur cinq questions :

1. Quels **signaux** peuvent aider KBC à comprendre ce dont les clients ont besoin ?
2. Comment reconnaître les clients selon leur **situation, comportement et intention** ?
3. Comment les expériences personnalisées peuvent-elles **s'adapter automatiquement** ?
4. Comment faire fonctionner cela à travers différents **produits, services et canaux** ?
5. Comment créer un impact significatif pour **des millions de clients en même temps** ?

Le brief précise également qu'ils ne cherchent **pas une simple nouvelle feature**, mais une **vision + un proof of concept** d'une nouvelle approche de personnalisation scalable.

Il faut donc éviter de tomber dans :

- un simple chatbot ;
- une page "Recommended for you" ;
- une règle `si voyage -> assurance voyage` ;
- une segmentation marketing classique ;
- une démo composée uniquement de belles maquettes.

Notre prototype doit donner l'impression qu'il existe un **véritable moteur de compréhension client** derrière l'interface.

---

# 3. Le concept

Nom de travail :

# **KBC Context**

Autres noms possibles :

- KBC Pulse
- My KBC
- KBC Moments
- KBC Context Engine

Le concept peut être résumé ainsi :

```text
PERSISTENT CUSTOMER CONTEXT
            +
     REAL-TIME MOMENTS
            ↓
       CONTEXT ENGINE
            ↓
        INTENT ENGINE
            ↓
       DECISION ENGINE
            ↓
      CUSTOMER JOURNEY
            ↓
   ADAPTIVE KBC EXPERIENCE
```

Le moteur répond en permanence à quatre questions :

```text
1. What is happening?

2. What does this customer probably need?

3. Should KBC act now?

4. What should KBC change?
```

---

# 4. Notre idée initiale : catégories longues et catégories courtes

L'intuition de départ est bonne :

- une **catégorie longue** représente la situation générale du client ;
- plusieurs **catégories courtes** peuvent être actives simultanément et représentent ce qui se passe maintenant.

Mais pour la présentation, on évite les termes "catégories longues" et "catégories courtes".

On utilise plutôt :

## 4.1 Persistent Customer Context

Ce sont les caractéristiques relativement stables.

Exemples :

- jeune professionnel ;
- premiers salaires ;
- salarié établi ;
- locataire ;
- propriétaire ;
- crédit hypothécaire actif ;
- parent ;
- compte enfant ;
- retraité ;
- indépendant ;
- niveau d'épargne faible / moyen / élevé ;
- situation financière stable.

Le point important : **on ne crée pas une catégorie monolithique par personne**.

Mauvais modèle :

```text
young_parent_homeowner_mortgage_stable_salary
```

Cela provoquerait rapidement une explosion du nombre de catégories.

On préfère plusieurs dimensions :

```json
{
  "life_stage": "young_professional",
  "employment": "salaried",
  "income_stage": "first_salary",
  "housing": "tenant",
  "mortgage": false,
  "family": "single",
  "financial_buffer": "low"
}
```

Cela rend le système combinable et scalable.

---

## 4.2 Active Moments

Les moments actifs représentent des événements ou intentions temporaires.

Exemples :

- premier salaire ;
- voyage probable ;
- achat ou changement de voiture ;
- naissance / nouveau parent ;
- projet immobilier ;
- grosse dépense récente ;
- grosse rentrée d'argent ;
- augmentation de salaire ;
- tension de trésorerie ;
- intérêt pour l'investissement ;
- changement de domicile ;
- retraite récente.

Un client peut avoir plusieurs moments actifs.

Exemple :

```text
ACTIVE MOMENTS

TRAVEL                  91%
CAR PURCHASE            37%
CASHFLOW PRESSURE       12%
HOME BUYING              8%
```

Les moments doivent pouvoir expirer.

Exemple :

```text
TRAVEL
active for 30 days
```

alors que :

```text
HOMEOWNER
```

appartient plutôt au contexte persistant.

---

# 5. Transaction ≠ intention

C'est une règle fondamentale du projet.

Une transaction chez BMW de 1 200 € ne signifie pas automatiquement :

> "le client vient d'acheter une voiture".

Cela peut être :

- une réparation ;
- un acompte ;
- des pièces ;
- une dépense pour une autre personne ;
- un leasing ;
- un entretien.

Nous devons donc utiliser un **confidence score**.

Exemple :

```text
BMW transaction
→ CAR ACQUISITION 42%
```

Puis :

```text
BMW transaction
+
vehicle financing page visited
→ CAR ACQUISITION 78%
```

Puis :

```text
insurance page visited
→ CAR ACQUISITION 93%
```

Le système ne doit pas agir de la même manière avec une confiance de 42 % et de 93 %.

Exemple de logique :

```text
< 50%
→ no action

50–75%
→ subtle personalization

75–90%
→ relevant suggestion

> 90%
→ proactive contextual experience
```

Ces seuils sont des choix de prototype, pas des valeurs officielles KBC.

---

# 6. Les données analysées

Le système ne doit pas se limiter aux dépenses.

Il peut combiner plusieurs familles de signaux.

## 6.1 Signaux financiers

Exemples :

- nouveaux salaires ;
- changement de montant du salaire ;
- dépenses inhabituelles ;
- gros paiements ;
- paiements récurrents ;
- augmentation de l'épargne ;
- diminution de l'épargne ;
- faible solde prévu ;
- nouvelle pension ;
- disparition du salaire régulier.

## 6.2 Comportement dans l'application

Exemples :

- pages visitées ;
- recherches ;
- simulateurs utilisés ;
- fonctionnalités ouvertes plusieurs fois ;
- page hypothécaire consultée ;
- page investissement consultée ;
- page assurance consultée ;
- recommandation rejetée ;
- parcours abandonné.

## 6.3 Situation connue du client

Exemples :

- tranche de vie ;
- situation de logement ;
- présence d'un crédit ;
- situation familiale ;
- produits KBC déjà détenus ;
- niveau d'épargne ;
- historique de revenus.

## 6.4 Produits et protections déjà existants

C'est très important.

Avant de proposer quelque chose, le moteur doit vérifier si le client possède déjà une solution pertinente.

Exemple :

```text
Travel detected
        ↓
Already has relevant travel coverage?
        ↓
YES
→ do not recommend another insurance
```

---

# 7. Le Context Engine

Le Context Engine fusionne les informations durables et les événements récents.

Exemple :

```text
CUSTOMER
   │
   ├── Persistent context
   │     ├── young professional
   │     ├── tenant
   │     ├── first recurring salary
   │     └── low savings buffer
   │
   └── Active signals
         ├── salary received
         ├── savings page visited
         └── budgeting page visited
```

Le système peut alors construire un état client :

```json
{
  "profile": {
    "life_stage": "young_professional",
    "housing": "tenant",
    "income_stage": "first_salary"
  },
  "moments": [
    {
      "type": "FIRST_SALARY",
      "confidence": 0.96
    }
  ]
}
```

---

# 8. L'Intent Engine

L'Intent Engine estime ce que le client essaie probablement de faire ou ce dont il pourrait avoir besoin.

Exemple :

```text
FINANCIAL SAFETY       93%
START SAVING           82%
INVESTING              31%
HOME BUYING             4%
```

Les intentions ne sont pas forcément exclusives.

Un client peut simultanément :

- vouloir préparer un voyage ;
- être intéressé par l'investissement ;
- avoir une tension de trésorerie.

Le système doit donc également les **prioriser**.

---

# 9. Le Decision Engine

C'est probablement la partie conceptuellement la plus importante.

Le système ne doit pas faire :

```text
TRAVEL detected
→ SELL TRAVEL INSURANCE
```

Le Decision Engine combine :

```text
Intent
+
Confidence
+
Timing
+
Current financial situation
+
Existing KBC products
+
Urgency
+
Potential usefulness
```

Puis choisit une action :

```text
PRODUCT
SERVICE
GUIDANCE
WARNING
JOURNEY
WAIT
NOTHING
```

## Règle fondamentale

> **The best recommendation is sometimes no recommendation.**

Cela différencie notre solution d'un moteur de cross-selling classique.

---

# 10. Exemple complet : voyage

Signaux :

```text
Flight purchase
+
Booking.com transaction
+
travel-related activity
```

Le système :

```text
TRAVEL INTENT
94%
```

Avant de proposer une assurance :

```text
Does this customer already have relevant coverage?
```

### Cas A — déjà couvert

```text
NO PRODUCT RECOMMENDATION

You're already covered for your trip.
```

### Cas B — pas couvert

```text
TRAVEL JOURNEY

→ Check travel coverage
→ Review card settings abroad
→ Create travel budget
→ Review payment options
```

### Cas C — faible confiance

```text
TRAVEL 48%

→ Do nothing
```

---

# 11. Exemple complet : voiture

Version trop simple :

```text
Car transaction
→ car insurance
```

Version KBC Context :

```text
Automotive transaction
+
Customer context
+
Existing products
+
Current cashflow
+
App behavior
        ↓
CAR-RELATED INTENT
        ↓
Decision Engine
```

Résultats possibles :

### Client non assuré

```text
→ relevant insurance journey
```

### Client déjà assuré

```text
→ no insurance offer
```

### Client en tension financière

```text
→ prioritize cashflow / budgeting guidance
```

### Intention peu certaine

```text
→ wait
```

Même transaction, expérience différente.

---

# 12. Exemple complet : achat immobilier

Persistent Context :

```text
32 years old
Tenant
Stable salary
Savings €48k
```

Behavior :

```text
Mortgage simulator opened ×4
Mortgage FAQ visited
Savings increasing
```

Résultat :

```text
HOME BUYING INTENT
93%
```

Le système peut construire un **Home Journey** :

```text
Understand borrowing capacity
        ↓
Prepare down payment
        ↓
Understand monthly impact
        ↓
Explore financing options
        ↓
Review relevant protection / insurance
        ↓
Potential appointment / support
```

Le point important est :

> nous ne recommandons pas simplement un crédit.

Nous orchestrons un **parcours autour de l'objectif du client**.

---

# 13. Produit → Journey

C'est un des changements importants de notre concept.

Nous ne voulons pas penser :

```text
moment → product
```

mais :

```text
moment → journey
```

Exemples :

## Travel Journey

```text
Card abroad
Travel coverage
Travel budget
Foreign payments
Guidance
```

## Car Journey

```text
Insurance
Financing information
Budget impact
Recurring vehicle costs
Savings impact
```

## Home Journey

```text
Borrowing capacity
Savings
Mortgage
Insurance
Budget impact
Appointments
```

## First Salary Journey

```text
Emergency buffer
Savings habit
Monthly budget
Financial education
Future investment readiness
```

---

# 14. L'expérience KBC doit réellement se transformer

Nous ne voulons pas seulement ajouter une petite carte :

```text
Recommended for you:
Travel insurance
```

La page principale doit se **réorganiser autour du contexte du client**.

Exemple avant :

```text
Accounts
Payments
Savings
Investments
Insurance
```

Exemple pendant un voyage :

```text
✈ YOUR UPCOMING TRIP

Card abroad             ✓
Travel coverage         ?
Travel budget           €900

[Prepare my trip]

--------------------------

Accounts
Payments
Savings
```

L'idée est :

> **the bank adapts around the moment.**

---

# 15. Explainability

Notre moteur analyse potentiellement des données sensibles et des comportements.

Il faut donc éviter l'effet :

> "KBC me surveille et essaie immédiatement de me vendre quelque chose."

Chaque recommandation devrait avoir :

```text
Why am I seeing this?
```

Exemple :

```text
We detected:

✓ recent flight purchase
✓ hotel booking
✓ travel-related activity

This is why we think travel preparation may be relevant.
```

Puis :

```text
[This is useful]
[Not relevant]
```

Si le client répond :

```text
Not relevant
```

le moteur peut réduire le confidence score :

```text
TRAVEL
94% → 20%
```

La recommandation disparaît.

Le système devient :

```text
personalized
+
explainable
+
correctable
```

---

# 16. Le timing

Le challenge KBC insiste sur le fait d'agir **au bon moment**.

Notre Decision Engine doit donc répondre à :

```text
WHAT?
```

mais aussi :

```text
WHEN?
```

Exemple :

```text
HOME BUYING INTENT   88%
TIMING RELEVANCE     35%

→ WAIT
```

Puis quelques jours plus tard :

```text
HOME BUYING INTENT   94%
TIMING RELEVANCE     91%

→ ACT
```

La personnalisation ne doit pas uniquement être correcte.

Elle doit être **pertinente maintenant**.

---

# 17. Architecture fonctionnelle

```text
                   CUSTOMER
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼

 PERSISTENT CONTEXT        REAL-TIME SIGNALS

 Life stage                Transactions
 Employment                App behavior
 Housing                   Searches
 Family                    Simulations
 Financial context         Recent events
 Existing products

          │                       │
          └───────────┬───────────┘
                      ▼

                CONTEXT ENGINE
                      │
                      ▼
                 INTENT ENGINE
                      │
                      ▼
                DECISION ENGINE
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       PRODUCT      SERVICE     GUIDANCE
          │           │           │
          └───────────┼───────────┘
                      ▼
                CUSTOMER JOURNEY
                      │
                      ▼
             ADAPTIVE KBC EXPERIENCE
```

---

# 18. Pourquoi notre solution est scalable

Le challenge demande de réfléchir à une solution utilisable pour plus de 2,3 millions de clients.

Nous ne créons pas :

```text
one manually designed interface per customer
```

Nous créons :

```text
one generic engine
+
reusable customer attributes
+
reusable moments
+
reusable journeys
+
dynamic decisions
```

Donc :

```text
2.3M customers
      ↓
Universal event schema
      ↓
KBC Context Engine
      ↓
2.3M different customer states
      ↓
Personalized experiences
```

Les quatre personas de la démo ne sont **pas quatre catégories finales**.

Ils ne sont que quatre exemples visuels qui permettent de démontrer le moteur.

---

# 19. Le site de démonstration

Le prototype est un site web pensé spécifiquement pour la présentation.

Nous devons pouvoir faire comprendre le concept en quelques secondes.

Le site contient trois grandes étapes :

```text
1. Choose a person
2. Overview
3. My KBC
```

---

# 20. Page 1 — Choose a person

Titre possible :

# **Meet your KBC**

Sous-titre :

> **Same bank. Different lives. Different needs.**

Autre phrase possible :

> **Four lives. One KBC.**

La page présente quatre humains.

---

# 21. Persona 1 — Thomas : First Salary

## Persistent Context

```text
23 years old
Young professional
Tenant
No children
No mortgage
First recurring salary
Low savings buffer
```

## Event

```text
ACME BELGIUM
SALARY
+ €2,450
```

## Detected Moment

```text
FIRST SALARY
Confidence: 96%
```

## Intent

```text
Financial safety       93%
Start saving           82%
Investing              31%
```

## My KBC

```text
🎉 Your first salary just arrived

Build your financial foundation

Monthly income             €2,450
Expected monthly expenses  €1,550
Potential monthly savings    €300

[Build my savings plan]
```

Le but n'est pas de vendre immédiatement un produit.

Le but est de reconnaître une **nouvelle étape de vie financière**.

---

# 22. Persona 2 — Sarah : New Parent

## Persistent Context

```text
31 years old
Stable salary
Homeowner
Mortgage
Partner
```

## Signals

```text
Child account created
+
new recurring child-related expenses
```

## Detected Moment

```text
NEW PARENT
Confidence: 94%
```

## My KBC

```text
👶 A new chapter starts

Your family

✓ Household finances
✓ Child account

Next steps

→ Start saving for your child
→ Review family protection
→ Adapt household budget
```

Cette démo doit montrer la transformation :

```text
Sarah before child
      ↓
New signals
      ↓
New context
      ↓
KBC adapts
```

---

# 23. Persona 3 — Marc : Retirement

## Persistent Context

```text
67 years old
Homeowner
No mortgage
Long financial history
Savings
```

## Signals

```text
Salary disappears
+
pension payment appears
```

## Detected Moment

```text
RETIREMENT TRANSITION
Confidence: 97%
```

## My KBC

```text
Your finances are entering a new phase

Monthly pension       €2,200
Recurring expenses    €1,450
Available buffer        €750
```

Journey possible :

```text
Manage monthly income
Savings organisation
Long-term financial planning
Relevant services
```

---

# 24. Persona 4 — Sophie : No Action Needed

Ce persona est très important.

## Persistent Context

```text
41 years old
Stable income
Homeowner
Mortgage under control
Emergency savings
Existing relevant coverage
Healthy cashflow
```

## Active Moments

```text
Travel                 12%
Car purchase            7%
Cashflow pressure       4%
Home purchase           2%
```

## Decision

# **NO ACTION NEEDED**

## My KBC

```text
Everything looks on track.

No action needed right now.
```

Pourquoi ce persona est important :

Il prouve que notre système n'est **pas un moteur qui cherche à vendre quelque chose à chaque client**.

Logique :

```text
customer
↓
understand context
↓
is something actually relevant?
↓
NO
↓
don't interrupt
```

C'est un excellent contraste avec les trois autres personas.

---

# 25. Design de la page d'accueil

Proposition :

```text
MEET YOUR KBC

4 people.
4 financial realities.
1 bank that adapts.


┌────────────────┐
│ THOMAS         │
│ 23             │
│                │
│ First Salary   │
│                │
│ [Be Thomas]    │
└────────────────┘

┌────────────────┐
│ SARAH          │
│ 31             │
│                │
│ New Parent     │
│                │
│ [Be Sarah]     │
└────────────────┘

┌────────────────┐
│ MARC           │
│ 67             │
│                │
│ Retirement     │
│                │
│ [Be Marc]      │
└────────────────┘

┌────────────────┐
│ SOPHIE         │
│ 41             │
│                │
│ Stable         │
│                │
│ [Be Sophie]    │
└────────────────┘
```

Éviter le terme interne :

> "femme parfaite où on doit rien lui dire"

Dans la présentation, appeler ce persona :

- Stable & Optimized
- No Active Need
- Financially Stable

---

# 26. Page 2 — Overview

Après avoir choisi un persona, on voit d'abord sa situation actuelle.

Exemple Thomas :

```text
THOMAS

Current account       €3,280
Savings                 €420

Recent transactions

ACME BELGIUM          +€2,450
Rent                    -€750
Spotify                  -€11
Supermarket               -€63
```

À droite :

```text
CUSTOMER CONTEXT

Young professional
Tenant
First salary detected
```

Puis gros bouton :

# **See My KBC →**

L'idée est de montrer :

```text
raw customer information
↓
understanding
↓
personalized experience
```

---

# 27. Transition vers My KBC

C'est un moment important de la démo.

On peut afficher successivement :

```text
Understanding Thomas...
```

Puis :

```text
Analyzing context
████████████
```

Puis :

```text
First salary detected
```

Puis :

```text
Understanding needs

Financial foundation  93%
Saving                 82%
Investing              31%
```

Puis :

```text
Building Thomas's KBC...
```

Puis révélation de l'interface personnalisée.

La transition doit être rapide.

Le jury doit sentir qu'un moteur vient de transformer les données en compréhension.

---

# 28. Page 3 — My KBC

Avant :

```text
Accounts
Payments
Savings
Insurance
Investments
```

Après personnalisation pour Thomas :

```text
Good evening Thomas

🎉 Your first salary just arrived

Build your financial foundation

€420 ━━━━━━━━━━━ €3,000

Save €250 / month

[Start my plan]

------------------------------

Accounts
Payments
More
```

Pour Sarah, Marc et Sophie, cette page doit être différente.

---

# 29. "Why am I seeing this?"

Sur My KBC :

```text
Why am I seeing this?
```

Pour Thomas :

```text
We detected:

✓ Your first recurring salary
✓ Limited existing savings
✓ Stable monthly income

We therefore believe building
financial security could be relevant.
```

Puis :

```text
[This is useful]
[Not relevant]
```

---

# 30. "Under the hood"

Il faut un bouton technique discret :

```text
</> See how KBC understood Thomas
```

Cette vue montre le moteur.

Exemple :

```text
CUSTOMER CONTEXT

life_stage
young_professional

housing
tenant

income_stage
first_salary


ACTIVE MOMENTS

FIRST_SALARY        96%
TRAVEL               7%
HOME_BUYING           4%


INTENT

FINANCIAL_SAFETY     93%
SAVING               82%
INVESTING            31%


DECISION

Journey:
FINANCIAL_FOUNDATION

Timing:
NOW

Confidence:
HIGH
```

Cette page est très importante pour montrer que le projet n'est pas juste une UI.

---

# 31. Démontrer un changement en temps réel

Si possible, ajouter un bouton ou event simulator :

```text
SIMULATE EVENT

[ First salary ]

[ Flight purchase ]

[ Mortgage interest ]

[ Unexpected expense ]
```

Exemple :

```text
Flight purchase
↓
TRAVEL 62%
```

Puis :

```text
Booking.com transaction
↓
TRAVEL 94%
```

Et l'interface se transforme.

Cela permet de démontrer le moteur en live.

---

# 32. Démontrer que KBC peut changer d'avis

Très bon moment de démo :

1. le système détecte un voyage ;
2. il affiche un Travel Journey ;
3. on ajoute une grosse dépense inattendue ;
4. le contexte change ;
5. le système priorise la trésorerie.

Exemple :

```text
Unexpected expense
- €1,500
```

Puis :

```text
CASHFLOW PRESSURE
92%
```

Le système peut supprimer une recommandation non urgente et afficher :

```text
Your next two weeks may be tighter than usual.

Upcoming expenses
€1,400

Projected remaining buffer
€120
```

Cela montre que la personnalisation est **dynamique**, pas statique.

---

# 33. Architecture technique possible

Le prototype peut rester raisonnablement simple.

## Frontend

```text
Next.js / React
```

Responsabilités :

- page personas ;
- overview ;
- My KBC ;
- animations ;
- visualisation des scores ;
- event simulator.

## Backend

```text
FastAPI
or
Node.js
```

Responsabilités :

- données des personas ;
- événements ;
- calcul du contexte ;
- score des moments ;
- score des intentions ;
- décision ;
- réponse JSON.

## Stockage

Pour le hackathon :

- données statiques JSON ;
- SQLite ;
- Firestore ;
- ou autre stockage simple.

Il ne faut pas perdre du temps à construire une infrastructure réaliste de banque.

## IA

Approche conseillée :

```text
Deterministic logic
+
scoring
+
optional LLM reasoning / wording
```

Ne pas tout déléguer à un LLM.

---

# 34. Exemple de JSON interne

## Customer

```json
{
  "customer_id": "thomas",
  "profile": {
    "life_stage": "young_professional",
    "employment": "salaried",
    "housing": "tenant",
    "family": "single",
    "income_stage": "first_salary"
  },
  "accounts": {
    "current": 3280,
    "savings": 420
  }
}
```

## Event

```json
{
  "type": "TRANSACTION",
  "category": "salary",
  "merchant": "ACME BELGIUM",
  "amount": 2450
}
```

## Engine result

```json
{
  "moments": [
    {
      "name": "FIRST_SALARY",
      "confidence": 0.96
    }
  ],
  "intents": {
    "financial_safety": 0.93,
    "saving": 0.82,
    "investing": 0.31
  },
  "decision": {
    "action": "SHOW_JOURNEY",
    "journey": "FINANCIAL_FOUNDATION",
    "timing": "NOW"
  }
}
```

---

# 35. Logique de scoring simple

Pour le hackathon, il n'est pas nécessaire de créer un modèle ML très complexe.

Exemple :

```text
FIRST_SALARY score

+50 if salary transaction exists
+30 if no previous salary exists
+10 if age/life stage is compatible
+10 if savings are low

Total: 100
```

Ou :

```text
TRAVEL score

+40 flight transaction
+25 hotel transaction
+20 travel-related app behavior
+15 foreign payment activity
```

Ce qui compte pendant le hackathon :

- le système doit fonctionner ;
- la logique doit être claire ;
- la démo doit être convaincante ;
- l'architecture doit montrer comment cela pourrait évoluer.

---

# 36. LLM : où l'utiliser intelligemment

Bon usage :

- reformuler une recommandation ;
- générer une explication adaptée ;
- interpréter certains signaux textuels ;
- générer un résumé du contexte ;
- conversation avec le client.

Mauvais usage :

```text
send all customer data
→ ask LLM what to do
```

Nous voulons pouvoir expliquer les décisions du moteur.

---

# 37. Sécurité

Le guide impose un audit Aikido et la sécurité compte dans l'évaluation.

L'audit cherche notamment :

- business logic flaws ;
- IDOR ;
- authentication issues ;
- authorization issues.

Notre prototype doit donc au minimum éviter :

```text
GET /customer?id=123
```

si l'identité peut être modifiée arbitrairement côté client.

Même avec des personas fictifs, il faut montrer de bonnes pratiques :

```text
authenticated user
      ↓
server-side customer identity
      ↓
customer-scoped data
```

Également :

- aucune API key dans le repo ;
- aucun secret dans le frontend ;
- aucun mot de passe commit ;
- repo nettoyé avant audit ;
- screenshots Aikido avant / après corrections.

---

# 38. Critères du jury

Le guide annonce quatre critères :

1. **Creativity**
2. **Technical ability**
3. **Fit**
4. **Security**

Notre stratégie doit rendre les quatre visibles.

## Creativity

Montrer :

- context engine ;
- adaptive banking ;
- journeys ;
- "do nothing" decision ;
- dynamic transformation.

## Technical Ability

Montrer :

```text
events
→ context engine
→ intent scores
→ decision engine
→ JSON
→ dynamic UI
```

Pas seulement quatre maquettes codées séparément.

## Fit

Utiliser le vocabulaire du challenge :

- signals ;
- situation ;
- behavior ;
- intent ;
- personalized experiences ;
- products ;
- services ;
- channels ;
- scale.

## Security

- Aikido ;
- access control ;
- no secrets ;
- customer isolation.

---

# 39. Ce qu'il ne faut PAS faire

## Ne pas pitcher :

> "We analyze spending to sell relevant KBC products."

Trop marketing et trop classique.

## Ne pas construire :

```text
if flight:
    show_travel_insurance()
```

et prétendre que c'est tout le moteur.

## Ne pas présenter les personas comme les catégories finales

Ils ne sont que des exemples.

## Ne pas faire une simple page "recommended for you"

L'interface doit réellement s'adapter.

## Ne pas tout faire avec un LLM

Il faut une architecture compréhensible.

## Ne pas vouloir faire 30 moments

Mieux vaut 4 scénarios parfaitement démontrés.

---

# 40. Les quatre scénarios à implémenter en priorité

Ordre conseillé :

## 1. First Salary

Pourquoi :

- simple à comprendre ;
- très visuel ;
- très bon pour ouvrir la démo.

## 2. New Parent

Pourquoi :

- démontre une transition de vie ;
- montre plusieurs besoins / services.

## 3. Retirement

Pourquoi :

- démontre que le moteur fonctionne pour une autre génération ;
- montre une adaptation profonde du contexte.

## 4. No Action Needed

Pourquoi :

- différencie notre moteur d'un système publicitaire ;
- rend le projet plus crédible.

Option bonus :

## 5. Travel / unexpected expense

À utiliser surtout dans l'event simulator pour montrer le changement en temps réel.

---

# 41. Structure de la démo

## Étape 1 — Home

Afficher :

```text
Four lives.
One KBC.
```

Puis les quatre personnes.

## Étape 2 — Choisir Thomas

Dire :

> "Thomas just received his first salary."

## Étape 3 — Overview

Montrer :

- comptes ;
- transactions ;
- contexte brut.

## Étape 4 — See My KBC

Lancer la transformation.

## Étape 5 — Montrer l'interface personnalisée

Phrase :

> "The customer doesn't have to understand the bank anymore. The bank understands the customer."

## Étape 6 — Under the hood

Montrer :

- persistent context ;
- active moments ;
- intent scores ;
- decision ;
- timing.

## Étape 7 — Passer rapidement sur Sarah, Marc, Sophie

Faire comprendre :

```text
Same engine.
Different context.
Different KBC.
```

## Étape 8 — Option live event

Ajouter un événement et montrer que le moteur change d'avis.

---

# 42. Script possible — version courte

> "KBC has millions of customers, but those customers are living completely different financial moments."

Afficher les quatre personas.

> "Thomas just received his first salary. Sarah just became a parent. Marc just retired. Sophie doesn't need anything right now."

> "They shouldn't necessarily see the same bank."

Choisir Thomas.

> "Our Context Engine combines persistent customer context with real-time financial and behavioral signals."

Montrer Overview.

> "It estimates what is happening, what Thomas may need, whether now is the right moment, and how KBC should adapt."

Cliquer **See My KBC**.

Transformation.

> "This is not four interfaces we designed manually. It is one personalization engine producing different experiences from different contexts."

Afficher Under the Hood.

> "And sometimes, the best recommendation is no recommendation."

Afficher Sophie.

> "We don't want KBC to sell more at every moment. We want KBC to understand which moments matter."

Fin :

> **We turn customer signals into customer understanding.**

---

# 43. Structure possible de la vidéo de moins de 3 minutes

Le guide demande une courte vidéo de démo de moins de 3 minutes.

Proposition :

## 00:00 – 00:20 — problème

```text
Same bank.
Millions of different lives.
```

Présenter le problème.

## 00:20 – 00:40 — concept

```text
Persistent Context
+
Active Moments
→ Intent
→ Decision
→ Adaptive KBC
```

## 00:40 – 01:20 — Thomas

- overview ;
- first salary detected ;
- transformation ;
- My KBC.

## 01:20 – 01:50 — autres personas

- Sarah ;
- Marc ;
- Sophie.

Très rapide.

## 01:50 – 02:20 — Under the hood

Montrer :

- context ;
- active moments ;
- intent scores ;
- decision engine.

## 02:20 – 02:40 — Event change

Ajouter une dépense ou un voyage.

Montrer l'interface qui s'adapte.

## 02:40 – 03:00 — scale + conclusion

```text
One engine.
Millions of contexts.
Millions of relevant experiences.
```

Fin :

> **KBC Context — a bank that understands the moment.**

---

# 44. Répartition possible du travail

Exemple pour une équipe de 4.

## Personne 1 — Frontend

- home ;
- personas ;
- overview ;
- My KBC ;
- animations ;
- responsive.

## Personne 2 — Engine

- customer model ;
- signals ;
- scoring ;
- context ;
- intents ;
- decisions.

## Personne 3 — Backend / Integration

- API ;
- event simulator ;
- frontend/backend ;
- stockage ;
- deployment.

## Personne 4 — UX / Content / Security / Pitch

- journeys ;
- texts ;
- explainability ;
- Aikido ;
- README ;
- demo video ;
- pitch.

Évidemment, chacun peut aider ailleurs.

---

# 45. MVP

Le MVP doit fonctionner même si on manque de temps.

## Obligatoire

- 4 personas ;
- page de sélection ;
- overview ;
- page My KBC différente pour chacun ;
- moteur de données commun ;
- persistent context ;
- active moments ;
- intent score ;
- decision ;
- under-the-hood view ;
- repo public et propre ;
- Aikido audit.

## Très souhaitable

- animation de transformation ;
- Why am I seeing this? ;
- feedback "Not relevant" ;
- event simulator ;
- changement dynamique d'un score.

## Bonus

- assistant ;
- voice ;
- intégration ElevenLabs ;
- visualisation avancée ;
- données simulées plus riches ;
- streaming temps réel.

Ne pas sacrifier le MVP pour les bonus.

---

# 46. Priorité absolue

Si nous avons peu de temps, la priorité est :

```text
1. Working engine
2. Beautiful transformation
3. Clear story
4. Four convincing examples
5. Security
6. Bonus features
```

La meilleure démo n'est pas celle avec le plus de fonctionnalités.

C'est celle où le jury comprend le concept en 20 secondes et voit immédiatement qu'il existe une architecture scalable derrière.

---

# 47. Formulations à réutiliser

## Taglines

> **We turn customer signals into customer understanding.**

> **KBC adapts to the customer, not the other way around.**

> **Same bank. Different lives. Different needs.**

> **Four lives. One KBC.**

> **The right experience at the right moment.**

> **The best recommendation is sometimes no recommendation.**

> **We don't recommend products. We orchestrate customer journeys.**

> **Don't predict what the customer will buy. Understand what the customer will need.**

---

# 48. Notre différence par rapport à un moteur de recommandation classique

## Recommandation classique

```text
transaction
↓
segment
↓
product
```

## KBC Context

```text
persistent context
+
real-time signals
+
behavior
+
existing products
+
financial situation
        ↓
context
        ↓
intent
        ↓
timing
        ↓
decision
        ↓
journey / guidance / product / nothing
        ↓
adaptive experience
```

C'est cette différence qu'il faut marteler pendant le pitch.

---

# 49. Vision finale

À terme, l'idée est que KBC ne soit plus une application composée principalement de menus que chaque client doit apprendre à naviguer.

Le client ouvre KBC et voit ce qui est pertinent pour **son contexte actuel**.

Deux clients peuvent donc ouvrir l'application au même moment et voir deux expériences complètement différentes.

Exemple :

```text
THOMAS
→ financial foundation

SARAH
→ family journey

MARC
→ retirement transition

SOPHIE
→ nothing urgent
```

Ce ne sont pas quatre produits.

Ce sont quatre manifestations d'un même système.

---

# 50. Conclusion

Notre idée de base est la suivante :

> **Créer une couche d'intelligence client qui maintient en permanence une compréhension du contexte durable et des moments récents de chaque utilisateur, estime ses intentions et décide comment KBC devrait s'adapter à cet instant.**

Les "catégories longues" deviennent :

> **Persistent Customer Context**

Les "catégories courtes" deviennent :

> **Active Moments**

Puis :

```text
Persistent Context
+
Active Moments
        ↓
Context Engine
        ↓
Intent Engine
        ↓
Decision Engine
        ↓
Customer Journey
        ↓
Adaptive KBC
```

Le produit ne cherche pas uniquement à répondre :

> "Quel produit pouvons-nous proposer ?"

Il cherche à répondre :

> **"Qu'est-ce qui se passe pour ce client, de quoi pourrait-il avoir besoin, est-ce le bon moment pour agir, et comment KBC devrait-il s'adapter ?"**

C'est cela que notre site et notre présentation doivent rendre immédiatement visible.

---

# 51. Références au Participants Guide

Points du *Tectonic Hackathon - Participants Guide* utilisés comme base :

- **KBC Challenge — pages 3–4**
  - comprendre ce dont les clients ont besoin ;
  - agir au bon moment ;
  - réfléchir sans contraintes à l'expérience idéale ;
  - rendre la solution scalable à plus de 2,3 millions de clients ;
  - utiliser les signaux ;
  - reconnaître situation, comportement et intention ;
  - adapter automatiquement les expériences ;
  - fonctionner à travers produits, services et canaux ;
  - ne pas créer simplement une nouvelle feature.

- **Aikido — pages 6–7**
  - audit de sécurité obligatoire ;
  - business logic flaws ;
  - IDOR ;
  - authentication ;
  - authorization ;
  - screenshots avant / après.

- **Submission & Judging — page 11**
  - courte description ;
  - vidéo de démo de moins de 3 minutes ;
  - repo GitHub ;
  - screenshots Aikido ;
  - critères : Creativity, Technical Ability, Fit, Security.

- **Rules & Fair Play — page 12**
  - projet construit pendant le hackathon ;
  - repo public pendant le judging ;
  - README ;
  - liens accessibles ;
  - aucun mot de passe / API key / donnée confidentielle dans le repo.

---

# 52. Dernière phrase à garder en tête

> **Nous ne construisons pas quatre expériences pour quatre personas. Nous construisons un moteur unique capable de générer une expérience différente pour chaque contexte.**
