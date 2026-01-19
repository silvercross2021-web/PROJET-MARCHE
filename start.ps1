# Script de démarrage pour e-Marché
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  e-Marché - Démarrage du serveur" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application: http://127.0.0.1:8000/" -ForegroundColor Green
Write-Host "Admin: http://127.0.0.1:8000/admin/" -ForegroundColor Green
Write-Host "Identifiant: admin" -ForegroundColor Cyan
Write-Host "Mot de passe: admin123" -ForegroundColor Cyan
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter le serveur" -ForegroundColor Yellow
Write-Host ""

cd C:\Users\silve\Desktop\etalMarrche
.\venv\Scripts\python.exe manage.py runserver

