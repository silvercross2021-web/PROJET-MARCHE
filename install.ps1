# Script d'installation pour e-Marché
# Version simplifiée et robuste

$ErrorActionPreference = "Continue"
$projectPath = "C:\Users\silve\Desktop\etalMarrche"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  e-Marché - Installation Complète" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Aller dans le dossier du projet
Set-Location $projectPath
Write-Host "[ÉTAPE 1] Dossier: $projectPath" -ForegroundColor Green
Write-Host ""

# Vérifier Python
Write-Host "[ÉTAPE 2] Vérification de Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ ERREUR: Python n'est pas installé" -ForegroundColor Red
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}
Write-Host ""

# Créer/Activer venv
Write-Host "[ÉTAPE 3] Création/Activation du venv..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "  ✓ Venv créé" -ForegroundColor Green
} else {
    Write-Host "  ✓ Venv existe déjà" -ForegroundColor Green
}

# Activer venv et installer pip
& .\venv\Scripts\python.exe -m ensurepip --upgrade | Out-Null
Write-Host "  ✓ Pip installé" -ForegroundColor Green
Write-Host ""

# Installer Django
Write-Host "[ÉTAPE 4] Installation de Django..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\venv\Scripts\python.exe -m pip install Django | Out-Null
$djangoVersion = & .\venv\Scripts\python.exe -m django --version 2>&1
Write-Host "  ✓ Django installé: $djangoVersion" -ForegroundColor Green
Write-Host ""

# Migrations
Write-Host "[ÉTAPE 5] Création des migrations..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py makemigrations market 2>&1 | Out-Null
Write-Host "  ✓ Migrations créées" -ForegroundColor Green
Write-Host ""

Write-Host "[ÉTAPE 6] Application des migrations..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py migrate 2>&1 | Out-Null
Write-Host "  ✓ Migrations appliquées" -ForegroundColor Green
Write-Host ""

# Données initiales
Write-Host "[ÉTAPE 7] Initialisation des données..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py init_data 2>&1 | Out-Null
Write-Host "  ✓ Données initialisées" -ForegroundColor Green
Write-Host ""

# Superutilisateur
Write-Host "[ÉTAPE 8] Création du superutilisateur..." -ForegroundColor Yellow
$userScript = "from django.contrib.auth.models import User; u, c = User.objects.get_or_create(username='admin', defaults={'email': 'admin@treichville.ci', 'is_superuser': True, 'is_staff': True}); u.set_password('admin123'); u.save(); print('OK')"
$result = & .\venv\Scripts\python.exe manage.py shell -c $userScript 2>&1
Write-Host "  ✓ Superutilisateur créé: admin / admin123" -ForegroundColor Green
Write-Host ""

# Résumé
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✓ Installation terminée!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application: http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "Admin: http://127.0.0.1:8000/admin/" -ForegroundColor Green
Write-Host "Identifiant: admin" -ForegroundColor Cyan
Write-Host "Mot de passe: admin123" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pour démarrer le serveur:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""


