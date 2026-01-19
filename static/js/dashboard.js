// Dashboard JavaScript - Interactions et Animations

// ============================================
// MODALES
// ============================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        // Animation d'entrée
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }, 300);
    }
}

// Fermer les modales en cliquant en dehors
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
        setTimeout(() => {
            event.target.style.display = 'none';
            document.body.style.overflow = 'auto';
        }, 300);
    }
}

// ============================================
// ACTUALISATION
// ============================================

function refreshDashboard() {
    const btn = document.querySelector('.btn-refresh');
    if (btn) {
        btn.classList.add('spinning');
        // Simuler le rechargement (en production, faire un fetch AJAX)
        setTimeout(() => {
            location.reload();
        }, 500);
    }
}

// ============================================
// EXPORT
// ============================================

function exportDashboard() {
    // Option 1: Export PDF (nécessite une bibliothèque)
    // Option 2: Export Excel (nécessite une bibliothèque)
    // Option 3: Impression
    window.print();
}

function exportDayDetails() {
    // Exporter les détails du jour
    alert('Fonctionnalité d\'export à implémenter');
}

function exportMonthlyEvolution() {
    // Exporter l'évolution mensuelle
    alert('Fonctionnalité d\'export à implémenter');
}

// ============================================
// DÉTAILS JOUR/MOIS
// ============================================

function showDayDetails(date, montant) {
    // Afficher les détails d'un jour spécifique
    console.log('Détails du jour:', date, montant);
    // Pourrait ouvrir une sous-modal avec plus de détails
}

function showMonthDetails(month, montant) {
    // Afficher les détails d'un mois spécifique
    console.log('Détails du mois:', month, montant);
    // Pourrait ouvrir une sous-modal avec plus de détails
}

// ============================================
// ANIMATIONS AU CHARGEMENT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Animation des KPI cards
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.5s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        }, index * 100);
    });
    
    // Animation des barres du graphique
    const chartBars = document.querySelectorAll('.chart-bar');
    chartBars.forEach((bar, index) => {
        const height = bar.style.height;
        bar.style.height = '0%';
        bar.style.transition = 'height 0.8s ease';
        
        setTimeout(() => {
            bar.style.height = height;
        }, index * 100);
    });
    
    // Animation de la ligne du graphique
    const linePath = document.querySelector('.line-path');
    if (linePath) {
        const length = linePath.getTotalLength();
        linePath.style.strokeDasharray = length;
        linePath.style.strokeDashoffset = length;
        linePath.style.transition = 'stroke-dashoffset 2s ease';
        
        setTimeout(() => {
            linePath.style.strokeDashoffset = 0;
        }, 500);
    }
    
    // Animation des points de la ligne
    const linePoints = document.querySelectorAll('.line-point');
    linePoints.forEach((point, index) => {
        point.style.opacity = '0';
        point.style.transition = 'opacity 0.3s ease';
        
        setTimeout(() => {
            point.style.opacity = '1';
        }, 2000 + (index * 100));
    });
    
    // Animation des progress bars
    const progressBars = document.querySelectorAll('.progress-fill');
    progressBars.forEach((bar, index) => {
        const width = bar.style.width;
        bar.style.width = '0%';
        bar.style.transition = 'width 1s ease';
        
        setTimeout(() => {
            bar.style.width = width;
        }, 1000 + (index * 200));
    });
    
    // Animation des activités
    const activites = document.querySelectorAll('.activite-item');
    activites.forEach((item, index) => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(-20px)';
        item.style.transition = 'all 0.3s ease';
        
        setTimeout(() => {
            item.style.opacity = '1';
            item.style.transform = 'translateX(0)';
        }, 2000 + (index * 50));
    });
    
    // Forcer le positionnement correct du badge ALERTE
    // Supprimer les styles inline qui pourraient être ajoutés par des outils de développement
    function fixAlertBadgePosition() {
        const alertBadges = document.querySelectorAll('.stat-alert-badge');
        alertBadges.forEach(badge => {
            // Supprimer les styles inline de positionnement qui interfèrent
            if (badge.style.left || badge.style.top) {
                badge.style.removeProperty('left');
                badge.style.removeProperty('top');
            }
        });
    }
    
    // Exécuter immédiatement et après un court délai
    fixAlertBadgePosition();
    setTimeout(fixAlertBadgePosition, 100);
    setTimeout(fixAlertBadgePosition, 500);
    
    // Observer les changements de style pour maintenir la position correcte
    const alertBadges = document.querySelectorAll('.stat-alert-badge');
    alertBadges.forEach(badge => {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                    // Si left ou top sont ajoutés, les supprimer
                    if (badge.style.left || badge.style.top) {
                        badge.style.removeProperty('left');
                        badge.style.removeProperty('top');
                    }
                }
            });
        });
        observer.observe(badge, { attributes: true, attributeFilter: ['style'] });
    });
});

// ============================================
// TOOLTIPS POUR LES BARRES
// ============================================

document.querySelectorAll('.chart-bar').forEach(bar => {
    bar.addEventListener('mouseenter', function(e) {
        const tooltip = this.querySelector('.chart-bar-tooltip');
        if (tooltip) {
            tooltip.style.display = 'block';
        }
    });
    
    bar.addEventListener('mouseleave', function(e) {
        const tooltip = this.querySelector('.chart-bar-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    });
});

// ============================================
// TOOLTIPS POUR LES POINTS DE LA LIGNE
// ============================================

document.querySelectorAll('.line-point').forEach(point => {
    point.addEventListener('mouseenter', function(e) {
        // Créer un tooltip dynamique
        const tooltip = document.createElement('div');
        tooltip.className = 'line-tooltip';
        tooltip.innerHTML = `
            <div class="tooltip-title">${this.dataset.month}</div>
            <div class="tooltip-value">${this.dataset.value} FCFA</div>
        `;
        document.body.appendChild(tooltip);
        
        const rect = this.getBoundingClientRect();
        tooltip.style.left = rect.left + 'px';
        tooltip.style.top = (rect.top - 40) + 'px';
    });
    
    point.addEventListener('mouseleave', function(e) {
        const tooltip = document.querySelector('.line-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    });
});

// ============================================
// AUTO-REFRESH (Optionnel)
// ============================================

let autoRefreshInterval = null;

function toggleAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    } else {
        autoRefreshInterval = setInterval(() => {
            refreshDashboard();
        }, 300000); // 5 minutes
    }
}

// ============================================
// RESPONSIVE HANDLING
// ============================================

function handleResize() {
    // Ajuster les graphiques si nécessaire
    const charts = document.querySelectorAll('.chart-container');
    charts.forEach(chart => {
        // Logique de redimensionnement si nécessaire
    });
}

window.addEventListener('resize', handleResize);

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

document.addEventListener('keydown', function(e) {
    // R pour refresh
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
        refreshDashboard();
    }
    
    // Echap pour fermer les modales
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.show').forEach(modal => {
            closeModal(modal.id);
        });
    }
});

