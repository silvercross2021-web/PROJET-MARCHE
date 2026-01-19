# Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet avec le contenu suivant :

```env
# Configuration e-Marché

# Sécurité
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données
# Pour SQLite (développement)
DATABASE_URL=sqlite:///db.sqlite3

# Pour PostgreSQL (production)
# DATABASE_URL=postgres://user:password@localhost:5432/emarche

# Pour MySQL (production)
# DATABASE_URL=mysql://user:password@localhost:3306/emarche

# Cache Redis (optionnel, pour production)
# REDIS_URL=redis://localhost:6379/0

# Email (pour notifications d'erreurs)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@emarche.treichville.ci

# Sécurité HTTPS (production uniquement)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
```

## Notes importantes

- Le fichier `.env` est déjà dans `.gitignore` et ne sera pas versionné
- En production, définissez `DEBUG=False` et `SECURE_SSL_REDIRECT=True`
- Générez une nouvelle `SECRET_KEY` pour la production avec : `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

