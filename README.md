# 🛡️ Aegis Monitor

> **Tableau de bord de monitoring intelligent et résilient**  


[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 À propos du projet

**Aegis Monitor** est une solution d'observabilité web complète qui vérifie la disponibilité des sites, enregistre les temps de réponse et déclenche des alertes intelligentes. Conçu pour répondre aux exigences du projet P08 de l'ESTI, ce projet dépasse le niveau L2 en intégrant des pratiques **SRE (Site Reliability Engineering)**, **DevSecOps** et une brique d'**IA locale (AIOps)** pour le diagnostic automatique des causes racines (RCA).

###  Fonctionnalités Clés 
- 🕵️ **Sondes Actives Multi-Protocoles** : Vérification HTTP/TCP/DNS avec métriques Prometheus natives.
- 📊 **Observabilité as Code** : Dashboards Grafana provisionnés automatiquement.
- 🧠 **Diagnostic IA Local** : Intégration d'Ollama (Phi-3/Mistral) pour analyser les pannes et proposer des causes racines sans fuite de données.
- 🌐 **Page de Statut Publique (PWA)** : Interface légère et installable pour les utilisateurs finaux.
- 🔒 **DevSecOps** : Pipeline CI/CD avec analyse de sécurité (Trivy), gestion des secrets et conteneurisation stricte.

---

## 🏗️ Architecture

Le système repose sur une architecture micro-services orchestrée par Docker Compose :

```mermaid
graph TD
    User[Utilisateur / Jury] -->|Consulte| StatusPage[Page de Statut Publique PWA]
    User -->|Administre| Grafana[Grafana Dashboards]
    User -->|Interroge| API[FastAPI Backend]
    
    API -->|1. Lance les sondes| Probes[Moteur de Sondes Python]
    Probes -->|2. HTTP/TCP/DNS| Targets[(Sites Web Cibles)]
    
    Probes -->|3. Expose métriques| Prometheus[(Prometheus)]
    Prometheus -->|4. Alerte si DOWN| Alertmanager[Alertmanager]
    Alertmanager -->|5. Webhook| API
    
    API -->|6. Demande diagnostic| Ollama[(Ollama LLM Local)]
    Ollama -.->|7. RCA en langage naturel| API
    
    Prometheus -.->|8. Visualisation| Grafana